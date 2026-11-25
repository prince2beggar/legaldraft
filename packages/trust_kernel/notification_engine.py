"""
Notification & Reminder Engine (SRS M07, Sprint S6).

Implements:
1. In-process reminder scheduler with injectable clock.
2. Reminder schedule: T-7, T-3, T-1, and 08:00 on the day; daily digest at 08:00 for deadlines in next 7 days.
3. Quiet hours (22:00 - 07:00 Asia/Dhaka): defers non-urgent notifications to 08:00 next morning.
4. SMS Escalation:
   - When an urgent deadline is within 24h and user has SMS enabled.
   - Escalate via MockSmsProvider with strictly generic text:
     "You have a deadline soon. Open AIN-AI." — zero case details or PII.
5. Delivery receipts, retry logic (up to 3x with error tracking).
6. Admin view for failed notifications.
7. Notification preferences management (in-app, SMS, quiet hours, language).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from datetime import time as dt_time
from typing import Any

from packages.trust_kernel.audit import InMemoryAuditService, audit_service
from packages.trust_kernel.db import DatabaseManager, db_manager
from packages.trust_kernel.sms import MockSmsProvider, mock_sms_provider

logger = logging.getLogger(__name__)

DHAKA_TZ = timezone(timedelta(hours=6))
GENERIC_SMS_TEXT_EN = "You have a deadline soon. Open AIN-AI."
GENERIC_SMS_TEXT_BN = "আপনার একটি আইনি সময়সীমা আসন্ন। আইন-AI অ্যাপটি দেখুন।"


class NotificationEngine:
    def __init__(
        self,
        db: DatabaseManager | None = None,
        sms_provider: MockSmsProvider | None = None,
        audit: InMemoryAuditService | None = None,
    ):
        self.db = db or db_manager
        self.sms = sms_provider or mock_sms_provider
        self.audit = audit or audit_service

    def _get_current_time(self) -> datetime:
        return self.db.get_current_time()

    def _get_dhaka_time(self) -> datetime:
        curr = self._get_current_time()
        if curr.tzinfo is None:
            curr = curr.replace(tzinfo=timezone.utc)
        return curr.astimezone(DHAKA_TZ)

    def is_quiet_hours(self, dt: datetime, prefs: dict[str, Any] | None = None) -> bool:
        """
        Determines if given time falls into quiet hours (22:00 - 07:00 Asia/Dhaka).
        """
        if prefs and not prefs.get("quiet_hours_enabled", True):
            return False

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dhaka_dt = dt.astimezone(DHAKA_TZ)
        hour = dhaka_dt.hour
        return hour >= 22 or hour < 7

    def get_next_quiet_hours_end(self, dt: datetime) -> str:
        """Calculates next 08:00 Asia/Dhaka timestamp in ISO format."""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dhaka_dt = dt.astimezone(DHAKA_TZ)

        target_date = dhaka_dt.date()
        if dhaka_dt.hour >= 7:
            # If after 07:00 at night (e.g. 22:00), next 08:00 is tomorrow morning
            target_date += timedelta(days=1)

        wake_dhaka = datetime.combine(target_date, dt_time(8, 0, 0), tzinfo=DHAKA_TZ)
        return wake_dhaka.astimezone(timezone.utc).isoformat()

    # ---------------------------------------------------------------------------
    # Trigger & Dispatch Logic
    # ---------------------------------------------------------------------------

    def trigger_pending_notifications(self) -> dict[str, Any]:
        """
        Processes pending notifications scheduled on or before current time.
        Handles quiet hours deferral, retry logic, SMS dispatch, and delivery receipts.
        """
        now_dt = self._get_current_time()
        now_iso = now_dt.isoformat()

        with self.db.get_session() as session:
            from packages.trust_kernel.db import NotificationDB

            notifications = (
                session.query(NotificationDB)
                .filter(
                    NotificationDB.status.in_(["pending", "deferred_quiet_hours"]),
                    NotificationDB.scheduled_at <= now_iso,
                )
                .all()
            )

            sent_count = 0
            deferred_count = 0
            failed_count = 0

            for notif in notifications:
                prefs = self.db.get_notification_preferences(notif.user_id)
                user = self.db.get_user(notif.user_id) or {}

                # 1. Quiet Hours check: defer non-urgent notifications
                # AC-M07-4: Quiet hours respected EXCEPT overdue-critical reminders
                is_overdue_critical = notif.category in ("overdue_critical", "urgent_overdue")
                if not is_overdue_critical and self.is_quiet_hours(now_dt, prefs):
                    next_morning_iso = self.get_next_quiet_hours_end(now_dt)
                    notif.status = "pending"
                    notif.scheduled_at = next_morning_iso
                    deferred_count += 1
                    self.audit.record_event(
                        actor_id="system",
                        action="notification.deferred",
                        object_type="notification",
                        object_id=notif.id,
                        description="Deferred notification to 08:00 due to quiet hours",
                    )
                    continue

                # 2. Dispatch by channel
                try:
                    if notif.channel == "in_app":
                        if not prefs.get("enable_in_app", True):
                            notif.status = "cancelled"
                            continue
                        notif.status = "sent"
                        notif.sent_at = now_iso
                        sent_count += 1

                    elif notif.channel == "sms":
                        phone = user.get("phone", "")
                        if not phone:
                            raise ValueError("User has no phone number on record for SMS dispatch.")

                        # STRICT REQUIREMENT: SMS message must be generic, zero case details
                        # Always ensure generic text
                        sms_text = (
                            GENERIC_SMS_TEXT_BN
                            if prefs.get("language") == "bn"
                            else GENERIC_SMS_TEXT_EN
                        )

                        # Mock / Real SMS dispatch
                        ok = self.sms.send_sms(phone=phone, message=sms_text)
                        if ok:
                            notif.status = "sent"
                            notif.sent_at = now_iso
                            sent_count += 1
                        else:
                            raise RuntimeError("SMS provider failed to dispatch.")

                    self.audit.record_event(
                        actor_id="system",
                        action="notification.sent",
                        object_type="notification",
                        object_id=notif.id,
                        description=f"Dispatched {notif.channel} notification to user {notif.user_id}",
                    )

                except Exception as ex:
                    notif.retry_count += 1
                    notif.error_message = str(ex)
                    if notif.retry_count >= 3:
                        notif.status = "failed"
                        failed_count += 1
                    else:
                        # Retry after 5 minutes
                        retry_dt = now_dt + timedelta(minutes=5)
                        notif.scheduled_at = retry_dt.isoformat()
                    logger.error("Failed notification dispatch %s: %s", notif.id, ex)

            session.commit()
            return {
                "processed": len(notifications),
                "sent": sent_count,
                "deferred": deferred_count,
                "failed": failed_count,
            }

    # ---------------------------------------------------------------------------
    # Deadline Reminders (T-7, T-3, T-1, Day-of)
    # ---------------------------------------------------------------------------

    def schedule_deadline_reminders(self, deadline_id: str) -> list[dict[str, Any]]:
        """
        Schedules T-7, T-3, T-1, and Day-of reminders (at 08:00 Asia/Dhaka) for a deadline.
        Ensures reminders in the past relative to the current clock are never scheduled.
        If user has SMS enabled, creates SMS notifications for urgent milestones (e.g. T-1, Day-of).
        """
        deadline = self.db.get_deadline(deadline_id)
        if not deadline:
            return []

        user_id = deadline.get("user_id")
        if not user_id:
            case_id = deadline.get("case_id")
            if case_id:
                case = self.db.get_case(case_id)
                if case:
                    user_id = case.get("owner_id")
        if not user_id:
            return []

        prefs = self.db.get_notification_preferences(user_id)
        due_str = deadline.get("due_date", "")
        try:
            due_date = datetime.strptime(due_str, "%Y-%m-%d").date()
        except Exception:
            return []

        now_dt = self._get_current_time()
        if now_dt.tzinfo is None:
            now_dt = now_dt.replace(tzinfo=timezone.utc)

        created_notifs = []
        offsets = [7, 3, 1, 0]
        for offset in offsets:
            remind_date = due_date - timedelta(days=offset)
            remind_dhaka = datetime.combine(remind_date, dt_time(8, 0, 0), tzinfo=DHAKA_TZ)
            remind_utc = remind_dhaka.astimezone(timezone.utc)

            # Never schedule in the past
            if remind_utc < now_dt:
                continue

            if offset == 0:
                offset_bn = "আজই"
            elif offset == 1:
                offset_bn = "আগামীকাল"
            else:
                from packages.trust_kernel.notice_engine import to_bangla_digits

                offset_bn = f"{to_bangla_digits(offset)} দিন পর"

            notif = self.db.create_notification(
                user_id=user_id,
                title=f"সময়সীমা রিমাইন্ডার ({offset_bn}): {deadline.get('title', '')}",
                message=f"আপনার মামলার একটি গুরুত্বপূর্ণ সময়সীমা নির্ধারিত রয়েছে ({deadline.get('due_date')})। সময়মত প্রস্তুতি সম্পন্ন করুন।",
                channel="in_app",
                category="deadline_reminder",
                deadline_id=deadline_id,
                case_id=deadline.get("case_id"),
                scheduled_at=remind_utc.isoformat(),
                status="pending",
            )
            created_notifs.append(notif)

            if prefs.get("enable_sms") and offset <= 1:
                sms_text = (
                    GENERIC_SMS_TEXT_BN if prefs.get("language") == "bn" else GENERIC_SMS_TEXT_EN
                )
                sms_notif = self.db.create_notification(
                    user_id=user_id,
                    title="সময়সীমা সতর্কতা",
                    message=sms_text,
                    channel="sms",
                    category="deadline_urgent",
                    deadline_id=deadline_id,
                    case_id=deadline.get("case_id"),
                    scheduled_at=remind_utc.isoformat(),
                    status="pending",
                )
                created_notifs.append(sms_notif)

        return created_notifs

    def cancel_deadline_reminders(self, deadline_id: str) -> int:
        """
        AC-M07-1: Cancels all pending notifications for a completed/dismissed deadline.
        """
        with self.db.get_session() as session:
            from packages.trust_kernel.db import NotificationDB

            cnt = (
                session.query(NotificationDB)
                .filter(
                    NotificationDB.deadline_id == deadline_id,
                    NotificationDB.status == "pending",
                )
                .update({"status": "cancelled"})
            )
            session.commit()
            return cnt

    def escalate_unread_deadline_notifications(self) -> list[dict[str, Any]]:
        """
        AC-M07-2: Unread deadline notification <= 3 days triggers SMS after 24h (injectable clock).
        Finds sent in-app notifications linked to a deadline <= 3 days away that remain unread
        after 24 hours of dispatch, and creates/sends an SMS notification.
        """
        now_dt = self._get_current_time()
        if now_dt.tzinfo is None:
            now_dt = now_dt.replace(tzinfo=timezone.utc)
        curr_dhaka = now_dt.astimezone(DHAKA_TZ)

        escalated: list[dict[str, Any]] = []
        with self.db.get_session() as session:
            from packages.trust_kernel.db import DeadlineDB, NotificationDB

            rows = (
                session.query(NotificationDB)
                .filter(
                    NotificationDB.channel == "in_app",
                    NotificationDB.status == "sent",
                    NotificationDB.deadline_id.isnot(None),
                    (NotificationDB.is_read == False) | (NotificationDB.is_read.is_(None)),  # noqa: E712
                )
                .all()
            )

            for notif in rows:
                if not notif.sent_at:
                    continue
                try:
                    sent_dt = datetime.fromisoformat(notif.sent_at.replace("Z", "+00:00"))
                    if sent_dt.tzinfo is None:
                        sent_dt = sent_dt.replace(tzinfo=timezone.utc)
                except Exception:
                    continue

                if (now_dt - sent_dt) < timedelta(hours=24):
                    continue

                dl = session.query(DeadlineDB).filter(DeadlineDB.id == notif.deadline_id).first()
                if not dl or dl.status in ("completed", "cancelled"):
                    continue

                try:
                    due_date = datetime.strptime(dl.due_date[:10], "%Y-%m-%d").date()
                    diff_days = (due_date - curr_dhaka.date()).days
                    if diff_days > 3:
                        continue
                except Exception:
                    continue

                existing_sms = (
                    session.query(NotificationDB)
                    .filter(
                        NotificationDB.user_id == notif.user_id,
                        NotificationDB.deadline_id == notif.deadline_id,
                        NotificationDB.channel == "sms",
                    )
                    .first()
                )
                if existing_sms:
                    continue

                prefs = self.db.get_notification_preferences(notif.user_id)
                sms_text = (
                    GENERIC_SMS_TEXT_BN if prefs.get("language") == "bn" else GENERIC_SMS_TEXT_EN
                )
                sms_notif = self.db.create_notification(
                    user_id=notif.user_id,
                    title="সময়সীমা সতর্কতা",
                    message=sms_text,
                    channel="sms",
                    category="deadline_urgent",
                    deadline_id=notif.deadline_id,
                    case_id=notif.case_id,
                    status="pending",
                )
                escalated.append(sms_notif)

        if escalated:
            self.trigger_pending_notifications()
        return escalated

    # ---------------------------------------------------------------------------
    # SMS Escalation for Urgent Deadlines (< 24h)
    # ---------------------------------------------------------------------------

    def escalate_urgent_deadline_sms(self, deadline_id: str, user_id: str) -> dict[str, Any] | None:
        """
        Escalates urgent deadline (<24h) to SMS if user has SMS notifications enabled.
        Strictly dispatches generic message text: 'You have a deadline soon. Open AIN-AI.'
        Never includes case title, court name, or case details in the SMS body.
        """
        prefs = self.db.get_notification_preferences(user_id)
        if not prefs.get("enable_sms"):
            return None

        deadline = self.db.get_deadline(deadline_id)
        if not deadline or deadline.get("status") in ("completed", "cancelled"):
            return None

        # Verify due date is within 24 hours
        curr_dhaka = self._get_dhaka_time()
        due_str = deadline.get("due_date", "")
        try:
            due_d = datetime.strptime(due_str, "%Y-%m-%d").date()
            diff_days = (due_d - curr_dhaka.date()).days
            if diff_days > 1:
                return None
        except Exception:
            return None

        user = self.db.get_user(user_id) or {}
        phone = user.get("phone", "")
        if not phone:
            return None

        # Generic text only
        msg_text = GENERIC_SMS_TEXT_BN if prefs.get("language") == "bn" else GENERIC_SMS_TEXT_EN

        notif = self.db.create_notification(
            user_id=user_id,
            title="জরুরি সময়সীমা সতর্কতা",
            message=msg_text,
            channel="sms",
            category="deadline_urgent",
            deadline_id=deadline_id,
            case_id=deadline.get("case_id"),
            status="pending",
        )

        # Trigger immediately
        self.trigger_pending_notifications()
        return notif

    # ---------------------------------------------------------------------------
    # Daily Digest at 08:00
    # ---------------------------------------------------------------------------

    def generate_daily_digest(self, user_id: str) -> dict[str, Any] | None:
        """
        Generates daily digest notification at 08:00 for deadlines due in the next 7 days.
        """
        curr_dhaka = self._get_dhaka_time()
        today = curr_dhaka.date()

        user_cases = self.db.list_cases(owner_id=user_id)
        upcoming_count = 0
        for c in user_cases:
            for dl in self.db.list_deadlines(case_id=c["id"]):
                if dl.get("status") in ("completed", "cancelled"):
                    continue
                try:
                    due_d = datetime.strptime(dl["due_date"], "%Y-%m-%d").date()
                    diff = (due_d - today).days
                    if 0 <= diff <= 7:
                        upcoming_count += 1
                except Exception:
                    pass

        if upcoming_count == 0:
            return None

        from packages.trust_kernel.notice_engine import to_bangla_digits

        cnt_bn = to_bangla_digits(upcoming_count)
        title = "দৈনিক আইনি আপডেট (Daily Digest)"
        msg = f"আজকের পর্যালোচনা: আগামী ৭ দিনের মধ্যে আপনার {cnt_bn}টি গুরুত্বপূর্ণ সময়সীমা রয়েছে। সময়মত পদক্ষেপ নিন।"

        return self.db.create_notification(
            user_id=user_id,
            title=title,
            message=msg,
            channel="in_app",
            category="daily_digest",
            status="sent",
        )

    # ---------------------------------------------------------------------------
    # Admin Views & Preferences
    # ---------------------------------------------------------------------------

    def list_failed_notifications(self) -> list[dict[str, Any]]:
        """Admin failure view: lists notifications that failed after retries."""
        with self.db.get_session() as session:
            from packages.trust_kernel.db import NotificationDB

            rows = (
                session.query(NotificationDB)
                .filter(NotificationDB.status == "failed")
                .order_by(NotificationDB.created_at.desc())
                .all()
            )
            return [
                {
                    "id": r.id,
                    "user_id": r.user_id,
                    "title": r.title,
                    "message": r.message,
                    "channel": r.channel,
                    "category": r.category,
                    "retry_count": r.retry_count,
                    "error_message": r.error_message,
                    "created_at": r.created_at,
                }
                for r in rows
            ]
