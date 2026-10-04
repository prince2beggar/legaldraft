"""
Acceptance Criteria Tests for Notifications & Reminder Scheduler Module (SRS Section 5.5 M07; Sprint S6).

Exact SRS AC Mapping:
- AC-M07-1: confirming deadline creates reminders; dismissing/completing cancels.
- AC-M07-2: unread deadline notification <= 3 days triggers SMS after 24h (injectable clock).
- AC-M07-3: SMS text contains no case or personal detail.
- AC-M07-4: quiet hours respected EXCEPT overdue-critical reminders (test for exception).

Supporting & Non-AC Tests:
- test_scheduler_injectable_clock_and_no_past_reminders
- test_delivery_receipts_and_admin_failure_view
- test_notification_preferences_crud
- test_daily_digest_at_0800
- test_notifications_ownership_isolation
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import pytest

from packages.trust_kernel.case_engine import CaseEngine
from packages.trust_kernel.notification_engine import (
    DHAKA_TZ,
    GENERIC_SMS_TEXT_BN,
    GENERIC_SMS_TEXT_EN,
    NotificationEngine,
)
from packages.trust_kernel.sms import MockSmsProvider


@pytest.fixture
def sms_provider():
    provider = MockSmsProvider()
    provider.clear()
    return provider


@pytest.fixture
def notif_eng(isolated_db_manager, sms_provider):
    return NotificationEngine(db=isolated_db_manager, sms_provider=sms_provider)


@pytest.fixture
def case_eng(isolated_db_manager):
    return CaseEngine(db=isolated_db_manager)


@pytest.fixture
def user_a(isolated_db_manager):
    user_data = {
        "id": f"citizen-user-notif-a-{time.time_ns()}",
        "phone": "+8801711778899",
        "name": "তৌফিক এলাহী",
        "role": "citizen",
        "roles": ["citizen"],
        "preferred_lang": "bn",
        "status": "active",
        "is_onboarded": True,
    }
    isolated_db_manager.save_user(user_data)
    return user_data


@pytest.fixture
def user_b(isolated_db_manager):
    user_data = {
        "id": f"citizen-user-notif-b-{time.time_ns()}",
        "phone": "+8801911443322",
        "name": "শফিকুল ইসলাম",
        "role": "citizen",
        "roles": ["citizen"],
        "preferred_lang": "bn",
        "status": "active",
        "is_onboarded": True,
    }
    isolated_db_manager.save_user(user_data)
    return user_data


# ---------------------------------------------------------------------------
# Exact SRS AC Mapping (M07)
# ---------------------------------------------------------------------------

def test_ac_m07_1_confirming_deadline_creates_reminders_dismissing_cancels(notif_eng, case_eng, user_a):
    """
    AC-M07-1: confirming deadline creates reminders; dismissing/completing cancels.
    """
    case = case_eng.create_case(user_id=user_a["id"], title="সময়সীমা নিশ্চিতকরণ ও বাতিল পরীক্ষা")

    # Set clock to: 2026-10-10 08:00:00 Dhaka time (+06:00) -> 02:00:00 UTC
    clock_now = datetime(2026, 10, 10, 2, 0, 0, tzinfo=timezone.utc)
    notif_eng.db.set_clock(clock_now)

    # 1. Create deadline unconfirmed
    dl = case_eng.db.create_deadline(
        case_id=case["id"],
        title="লিখিত আপত্তি দাখিল",
        due_date="2026-10-25",
        user_id=user_a["id"],
        confirmed_by_user=False,
    )
    # Unconfirmed: no reminders yet in schedules
    initial_rems = case_eng.db.get_reminders_for_deadline(dl["id"])
    assert len(initial_rems) == 0

    # 2. Confirm deadline -> automatically creates reminder schedules
    confirmed = case_eng.db.confirm_deadline(dl["id"], user_id=user_a["id"])
    assert confirmed["confirmed_by_user"] is True

    # Also schedule in NotificationEngine
    notifs = notif_eng.schedule_deadline_reminders(dl["id"])
    assert len(notifs) >= 1

    rems_after_confirm = case_eng.db.get_reminders_for_deadline(dl["id"])
    assert len(rems_after_confirm) > 0
    assert any(r["status"] == "pending" for r in rems_after_confirm)

    # 3. Dismissing/completing deadline cancels all pending reminders
    dismiss_res = case_eng.db.dismiss_or_meet_deadline(dl["id"], status="completed")
    assert dismiss_res["reminders_cancelled"] is True

    rems_after_dismiss = case_eng.db.get_reminders_for_deadline(dl["id"])
    assert all(r["status"] == "cancelled" for r in rems_after_dismiss)

    # Also check notification table pending reminders are cancelled
    active_notifs = notif_eng.db.list_notifications(user_a["id"], status="pending")
    dl_notifs = [n for n in active_notifs if n.get("deadline_id") == dl["id"]]
    assert len(dl_notifs) == 0

    notif_eng.db.reset_clock()


def test_ac_m07_2_unread_deadline_notification_le_3d_triggers_sms_after_24h(notif_eng, case_eng, user_a, sms_provider):
    """
    AC-M07-2: unread deadline notification <= 3 days triggers SMS after 24h (injectable clock).
    """
    case = case_eng.create_case(user_id=user_a["id"], title="জরুরি নোটিফিকেশন এসকেলেশন কেস")

    # Set clock to: Day 1, 10:00 AM Dhaka (+06:00) -> 04:00 UTC
    day1 = datetime(2026, 10, 10, 4, 0, 0, tzinfo=timezone.utc)
    notif_eng.db.set_clock(day1)

    # Create deadline due in 2 days (within <= 3 days)
    dl = case_eng.db.create_deadline(
        case_id=case["id"],
        title="চূড়ান্ত জবাব দাখিল",
        due_date="2026-10-12",
        user_id=user_a["id"],
        confirmed_by_user=True,
    )

    # Create an in-app notification and mark it sent at Day 1
    notif = notif_eng.db.create_notification(
        user_id=user_a["id"],
        title="সময়সীমা আসন্ন",
        message="আপনার মামলার সময়সীমা আর ২ দিন বাকি।",
        channel="in_app",
        category="deadline_reminder",
        deadline_id=dl["id"],
        case_id=case["id"],
        status="sent",
    )
    notif_eng.db.update_notification(notif["id"], sent_at=day1.isoformat())

    # Advance clock by only 10 hours: SMS must NOT trigger yet (< 24h)
    notif_eng.db.set_clock(day1 + timedelta(hours=10))
    esc_early = notif_eng.escalate_unread_deadline_notifications()
    assert len(esc_early) == 0

    # Advance clock to 25 hours later (now > 24 hours unread):
    day2 = day1 + timedelta(hours=25)
    notif_eng.db.set_clock(day2)

    # Trigger escalation
    esc_after_24h = notif_eng.escalate_unread_deadline_notifications()
    assert len(esc_after_24h) == 1

    # Verify SMS was dispatched via provider
    sent_sms = sms_provider._sent_messages
    assert len(sent_sms) >= 1
    latest_sms = sent_sms[-1]
    assert latest_sms["phone"] == user_a["phone"]
    assert latest_sms["message"] in (GENERIC_SMS_TEXT_BN, GENERIC_SMS_TEXT_EN)

    notif_eng.db.reset_clock()


def test_ac_m07_3_sms_text_contains_no_case_or_personal_detail(notif_eng, case_eng, user_a, sms_provider):
    """
    AC-M07-3: SMS text contains no case or personal detail.
    Strictly generic text: 'You have a deadline soon. Open AIN-AI.' or Bangla equivalent.
    """
    notif_eng.db.save_notification_preferences(user_a["id"], {
        "enable_sms": True,
        "language": "en",
    })

    case = case_eng.create_case(
        user_id=user_a["id"],
        title="গোপনীয় জমি খারিজ মামলা নং ১২৩/২০২৬",
        description="আদালত: ১ম যুগ্ম জেলা জজ আদালত ঢাকা",
    )
    dl = case_eng.db.create_deadline(
        case_id=case["id"],
        title="আদালতে লিখিত জবাব দাখিল",
        due_date="2026-10-12",
        user_id=user_a["id"],
        confirmed_by_user=True,
    )

    sched_clock = datetime(2026, 10, 11, 1, 0, 0, tzinfo=timezone.utc)  # 07:00 AM Dhaka
    notif_eng.db.set_clock(sched_clock)
    notif_eng.schedule_deadline_reminders(dl["id"])

    daytime_clock = datetime(2026, 10, 11, 3, 0, 0, tzinfo=timezone.utc)  # 09:00 AM Dhaka
    notif_eng.db.set_clock(daytime_clock)
    notif_eng.trigger_pending_notifications()

    sent_sms = [m for m in sms_provider._sent_messages if m.get("type") == "transactional"]
    assert len(sent_sms) >= 1

    for msg in sent_sms:
        text = msg["message"]
        assert text in (GENERIC_SMS_TEXT_EN, GENERIC_SMS_TEXT_BN)
        # Strict privacy guarantees
        assert "১২৩" not in text
        assert "জমি খারিজ" not in text
        assert "জেলা জজ" not in text
        assert "আদালত" not in text
        assert user_a["name"] not in text

    notif_eng.db.reset_clock()


def test_ac_m07_4_quiet_hours_respected_except_overdue_critical_reminders(notif_eng, user_a):
    """
    AC-M07-4: quiet hours respected EXCEPT overdue-critical reminders (test for exception).
    - Regular notification during quiet hours (22:00 - 07:00 Dhaka) is deferred to 08:00 next morning.
    - Overdue-critical reminder (category='overdue_critical') bypasses quiet hours and sends immediately.
    """
    notif_eng.db.save_notification_preferences(user_a["id"], {
        "quiet_hours_enabled": True,
        "quiet_hours_start": "22:00",
        "quiet_hours_end": "07:00",
    })

    # Set clock to: 23:30 Asia/Dhaka (+06:00) -> 17:30 UTC (Quiet hours!)
    quiet_clock = datetime(2026, 10, 11, 17, 30, 0, tzinfo=timezone.utc)
    notif_eng.db.set_clock(quiet_clock)

    # 1. Regular non-critical notification
    reg_notif = notif_eng.db.create_notification(
        user_id=user_a["id"],
        title="নিয়মিত আপডেট",
        message="আপনার মামলার অগ্রগতি দেখুন।",
        channel="in_app",
        category="general",
        scheduled_at=quiet_clock.isoformat(),
    )

    # 2. Overdue-critical reminder (THE EXCEPTION)
    crit_notif = notif_eng.db.create_notification(
        user_id=user_a["id"],
        title="জরুরি মেয়াদোত্তীর্ণ সতর্কতা!",
        message="আইনি সময়সীমা পার হয়ে গেছে। অবিলম্বে পদক্ষেপ নিন।",
        channel="in_app",
        category="overdue_critical",
        scheduled_at=quiet_clock.isoformat(),
    )

    # Trigger scheduler during quiet hours
    _ = notif_eng.trigger_pending_notifications()

    # 3. Verify regular notification was DEFERRED
    updated_reg = notif_eng.db.get_notification(reg_notif["id"])
    assert updated_reg["status"] == "pending"
    deferred_hour = datetime.fromisoformat(updated_reg["scheduled_at"]).astimezone(DHAKA_TZ).hour
    assert deferred_hour == 8, f"Expected regular notification deferred to 08:00, got {deferred_hour}"

    # 4. Verify overdue-critical reminder BYPASSED quiet hours and was SENT immediately!
    updated_crit = notif_eng.db.get_notification(crit_notif["id"])
    assert updated_crit["status"] == "sent", "Overdue-critical reminder MUST bypass quiet hours!"
    assert updated_crit["sent_at"] is not None

    notif_eng.db.reset_clock()


# ---------------------------------------------------------------------------
# Supporting / Non-AC Tests
# ---------------------------------------------------------------------------

def test_scheduler_injectable_clock_and_no_past_reminders(notif_eng, case_eng, user_a):
    """Scheduler with injectable clock never schedules reminders in the past."""
    case = case_eng.create_case(user_id=user_a["id"], title="ইনজেক্টেবল ক্লক টেস্ট")
    clock_now = datetime(2026, 10, 10, 2, 0, 0, tzinfo=timezone.utc)
    notif_eng.db.set_clock(clock_now)

    dl = case_eng.db.create_deadline(
        case_id=case["id"],
        title="জবাব দাখিল",
        due_date="2026-10-15",
        user_id=user_a["id"],
        confirmed_by_user=True,
    )

    created_notifs = notif_eng.schedule_deadline_reminders(deadline_id=dl["id"])
    assert len(created_notifs) == 3
    for n in created_notifs:
        sched_dt = datetime.fromisoformat(n["scheduled_at"])
        assert sched_dt > clock_now
        assert sched_dt.astimezone(DHAKA_TZ).hour == 8

    notif_eng.db.reset_clock()


def test_delivery_receipts_and_admin_failure_view(notif_eng, user_a):
    """Delivery receipts and admin failure tracking after 3 failed retries."""
    class FailingSmsProvider(MockSmsProvider):
        def send_sms(self, phone: str, message: str) -> bool:
            raise RuntimeError("Aggregator 503 Service Unavailable")

    fail_eng = NotificationEngine(db=notif_eng.db, sms_provider=FailingSmsProvider())
    daytime_clock = datetime(2026, 10, 10, 4, 0, 0, tzinfo=timezone.utc)
    fail_eng.db.set_clock(daytime_clock)

    try:
        now_utc = fail_eng.db.get_current_time()
        notif = fail_eng.db.create_notification(
            user_id=user_a["id"],
            title="ব্যর্থতা ট্র্যাকিং",
            message="Test message",
            channel="sms",
            category="deadline_reminder",
            scheduled_at=(now_utc - timedelta(minutes=5)).isoformat(),
        )

        # Attempt 1
        fail_eng.trigger_pending_notifications()
        n1 = fail_eng.db.get_notification(notif["id"])
        assert n1["retry_count"] == 1
        assert n1["status"] == "pending"

        # Attempt 2
        fail_eng.db.update_notification(notif["id"], scheduled_at=(now_utc - timedelta(minutes=1)).isoformat())
        fail_eng.trigger_pending_notifications()
        n2 = fail_eng.db.get_notification(notif["id"])
        assert n2["retry_count"] == 2

        # Attempt 3 -> fails permanently
        fail_eng.db.update_notification(notif["id"], scheduled_at=(now_utc - timedelta(minutes=1)).isoformat())
        fail_eng.trigger_pending_notifications()
        n3 = fail_eng.db.get_notification(notif["id"])
        assert n3["retry_count"] == 3
        assert n3["status"] == "failed"

        # Admin view
        failed_list = fail_eng.list_failed_notifications()
        assert any(fn["id"] == notif["id"] for fn in failed_list)
    finally:
        fail_eng.db.reset_clock()


def test_notification_preferences_crud(notif_eng, user_a):
    """CRUD for citizen notification preferences."""
    prefs = notif_eng.db.get_notification_preferences(user_a["id"])
    assert prefs["enable_in_app"] is True
    assert prefs["enable_sms"] is False

    saved = notif_eng.db.save_notification_preferences(user_a["id"], {
        "enable_sms": True,
        "language": "en",
    })
    assert saved["enable_sms"] is True
    assert saved["language"] == "en"


def test_daily_digest_at_0800(notif_eng, case_eng, user_a):
    """Daily digest summarizes upcoming deadlines."""
    case = case_eng.create_case(user_id=user_a["id"], title="দৈনিক সারাংশ কেস")
    clock_now = datetime(2026, 10, 10, 2, 0, 0, tzinfo=timezone.utc)  # 08:00 Dhaka
    notif_eng.db.set_clock(clock_now)

    case_eng.db.create_deadline(
        case_id=case["id"],
        title="পদ্ধতিগত কাজ",
        due_date="2026-10-14",
        user_id=user_a["id"],
        confirmed_by_user=True,
    )

    digest = notif_eng.generate_daily_digest(user_a["id"])
    assert digest is not None
    assert "দৈনিক আইনি আপডেট" in digest["title"]

    notif_eng.db.reset_clock()


def test_notifications_ownership_isolation(notif_eng, user_a, user_b):
    """User B cannot see User A's notifications."""
    notif_a = notif_eng.db.create_notification(
        user_id=user_a["id"],
        title="গোপন সতর্কতা",
        message="ব্যক্তিগত তথ্য",
        channel="in_app",
    )
    b_notifs = notif_eng.db.list_notifications(user_b["id"])
    assert not any(n["id"] == notif_a["id"] for n in b_notifs)
