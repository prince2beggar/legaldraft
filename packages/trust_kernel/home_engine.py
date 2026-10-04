"""
Home & Deterministic Next Action Engine (SRS M02, Sprint S6).

Implements:
1. Home data view (Greeting, ProblemInput, NextActionCard, QuickActions, My Cases, Upcoming, Footer).
2. Deterministic 10-priority Next Action algorithm from SRS Section 4 (p. 21).
   - Pure code, zero AI.
   - Stores reason_refs and explanation_bn for 'Why am I seeing this?'.
   - Strictly ignores proposed items until accepted.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from packages.trust_kernel.db import DatabaseManager, db_manager
from packages.trust_kernel.notice_engine import to_bangla_digits

logger = logging.getLogger(__name__)

DHAKA_TZ = timezone(timedelta(hours=6))

CASE_TYPE_REQUIRED_DOCUMENTS: dict[str, list[dict[str, str]]] = {
    "land_dispute": [
        {"doc_type": "khatian", "title": "খতিয়ান বা পরচা (Khatian)", "status": "APPROVED"},
        {"doc_type": "deed", "title": "মালিকানা দলিল (Title Deed)", "status": "APPROVED"},
    ],
    "cheque_dishonor": [
        {"doc_type": "cheque_copy", "title": "ডিসঅনারকৃত চেক (Cheque Copy)", "status": "APPROVED"},
        {"doc_type": "bank_memo", "title": "ব্যাংক রিটার্ন মেমো (Bank Memo)", "status": "APPROVED"},
    ],
    "eviction": [
        {"doc_type": "tenancy_agreement", "title": "ভাড়া চুক্তিপত্র (Tenancy Agreement)", "status": "APPROVED"},
        {"doc_type": "eviction_notice", "title": "উচ্ছেদ নোটিশ (Eviction Notice)", "status": "APPROVED"},
    ],
    "money_claim": [
        {"doc_type": "money_receipt", "title": "টাকা লেনদেনের প্রমাণ (Money Receipt)", "status": "APPROVED"},
    ],
    "notice_response": [
        {"doc_type": "received_notice", "title": "প্রাপ্ত আইনি নোটিশ", "status": "APPROVED"},
    ],
}


class HomeEngine:
    def __init__(self, db: DatabaseManager | None = None):
        self.db = db or db_manager

    def _get_current_time(self) -> datetime:
        return self.db.get_current_time()

    def _get_dhaka_time(self) -> datetime:
        curr = self._get_current_time()
        if curr.tzinfo is None:
            curr = curr.replace(tzinfo=timezone.utc)
        return curr.astimezone(DHAKA_TZ)

    def _get_time_aware_greeting(self, hour: int | None = None) -> str:
        if hour is None:
            dhaka_dt = self._get_dhaka_time()
            hour = dhaka_dt.hour
        if 5 <= hour < 12:
            return "শুভ সকাল"
        elif 12 <= hour < 17:
            return "শুভ অপরাহ্ন"
        else:
            return "শুভ সন্ধ্যা"

    def generate_greeting(self, user_id: str, hour: int | None = None) -> str:
        """Generates time-aware greeting for user adhering to AC-M02-1."""
        time_greeting = self._get_time_aware_greeting(hour=hour)
        user = self.db.get_user(user_id) if user_id else None
        name = (user.get("name") if user else None) or "নাগরিক"
        return f"{time_greeting}, {name}!"

    def get_problem_input_metadata(self) -> dict[str, Any]:
        """Returns ProblemInput metadata adhering to AC-M02-2."""
        return {
            "placeholder": "আপনার আইনি সমস্যা বা প্রশ্ন এখানে সংক্ষেপে লিখুন...",
            "action_route": "/intake",
            "mic_disabled": True,
            "mic_tooltip": "ভয়েস ইনপুট শীঘ্রই আসছে",
        }

    def clean_problem_input(self, text: str) -> str:
        """Trims whitespace and sanitizes problem input string."""
        return (text or "").strip()

    def calculate_next_action(self, user_id: str) -> dict[str, Any]:
        """
        Calculates the single most urgent Next Action using the deterministic
        10-priority table from SRS p. 21. Pure code, zero AI.
        Priorities:
        1. Urgent triage no help step (reads nullable case.is_urgent_triage / triage_urgency == "urgent_no_help")
        2. Overdue deadline (days_left < 0 / is_overdue) -> sets case status to action_required (AC-M06-3)
        3. Unconfirmed deadline <= 3 days (days_left <= 3 & unconfirmed)
        4. Deadline <= 7 days with open tasks (0 <= days_left <= 7 & open tasks)
        5. Lawyer/instruction task due (origin in ('lawyer', 'instruction'))
        6. Required document missing (has_missing_documents / 0 docs)
        7. Extracted fields awaiting review (status == 'extracted')
        8. AI-proposed facts/events awaiting confirmation (is_proposed == True)
        9. Draft in progress (draft.status == 'in_progress')
        10. next.none ("all caught up" / explore default)
        """
        curr_dhaka = self._get_dhaka_time()
        today_date = curr_dhaka.date()

        user_cases = self.db.list_cases(owner_id=user_id)
        active_cases = [c for c in user_cases if c.get("status") != "archived"]

        # -----------------------------------------------------------------------
        # Priority 1: Urgent triage no help step
        # -----------------------------------------------------------------------
        for c in active_cases:
            if c.get("is_urgent_triage") or c.get("triage_urgency") in ("urgent_no_help", "urgent_triage"):
                return {
                    "priority_tier": 1,
                    "title": f"জরুরি ট্রায়াজ: {c['title']}",
                    "description": "মামলাটিতে জরুরি সহায়তা এবং তাৎক্ষণিক আইনি পদক্ষেপ গ্রহণ প্রয়োজন।",
                    "action_type": "urgent_triage",
                    "target_url": f"/cases/{c['id']}?tab=overview",
                    "case_id": c["id"],
                    "reason_refs": [{"object_type": "case", "id": c["id"], "rule": "urgent_triage_no_help"}],
                    "explanation_bn": "মামলাটি প্রাথমিক ট্রায়াজে অত্যন্ত জরুরি হিসেবে চিহ্নিত হয়েছে এবং অবিলম্বে ব্যবস্থা গ্রহণ আবশ্যক।",
                }

        # Collect all deadlines and tasks across user's cases
        all_deadlines: list[dict[str, Any]] = []
        all_tasks: list[dict[str, Any]] = []
        for c in active_cases:
            dls = self.db.list_deadlines(case_id=c["id"])
            for dl in dls:
                dl["case_title"] = c["title"]
                all_deadlines.append(dl)
            tsks = self.db.list_tasks(case_id=c["id"])
            for t in tsks:
                t["case_title"] = c["title"]
                all_tasks.append(t)

        # Also collect deadlines from unattached user notice documents
        unconf_notices = self._find_unconfirmed_notices(user_id)
        for n in unconf_notices:
            doc_dls = self.db.list_deadlines(document_id=n["id"])
            for dl in doc_dls:
                if not any(d["id"] == dl["id"] for d in all_deadlines):
                    dl["case_title"] = n.get("filename", "আইনি নোটিশ")
                    all_deadlines.append(dl)

        # -----------------------------------------------------------------------
        # Priority 2: Overdue deadline (days_left < 0)
        # AC-M06-3: overdue deadline => case status action_required and Next Action priority 2
        # -----------------------------------------------------------------------
        overdue_dls = []
        for dl in all_deadlines:
            if dl.get("status") in ("completed", "cancelled"):
                continue
            due_str = dl.get("due_date", "")
            try:
                due_d = datetime.strptime(due_str[:10], "%Y-%m-%d").date()
                diff_days = (due_d - today_date).days
                if diff_days < 0:
                    overdue_dls.append((diff_days, dl))
            except Exception:
                pass

        if overdue_dls:
            overdue_dls.sort(key=lambda x: x[0])  # most overdue first
            diff_days, dl = overdue_dls[0]
            if dl.get("case_id"):
                try:
                    self.db.update_case(dl["case_id"], status="action_required")
                except Exception:
                    pass
            days_overdue = abs(diff_days)
            bn_days = to_bangla_digits(days_overdue)
            return {
                "priority_tier": 2,
                "title": f"মেয়াদ উত্তীর্ণ সময়সীমা! ({bn_days} দিন অতিবাহিত)",
                "description": f"মামলা '{dl.get('case_title', '')}': {dl['title']} — সময়সীমা পার হয়ে গেছে। অবিলম্বে পদক্ষেপ নিন।",
                "action_type": "overdue_deadline",
                "target_url": f"/cases/{dl['case_id']}?tab=deadlines" if dl.get("case_id") else f"/documents/{dl.get('document_id')}/notice",
                "case_id": dl.get("case_id"),
                "deadline_id": dl["id"],
                "reason_refs": [{"object_type": "deadline", "id": dl["id"], "rule": "overdue_deadline", "days_overdue": days_overdue}],
                "explanation_bn": "আইনি সময়সীমা উত্তীর্ণ হওয়ায় আদালতের আদেশ বা নোটিশের প্রতিকূল প্রভাব থেকে বাঁচতে অবিলম্বে পদক্ষেপ নিন।",
            }

        # -----------------------------------------------------------------------
        # Priority 3: Unconfirmed deadline <= 3 days (0 <= days_left <= 3 & unconfirmed)
        # AC-M02-1: unconfirmed deadline in 2 days + missing document => priority 3 before 6
        # -----------------------------------------------------------------------
        unconfirmed_dls = []
        for dl in all_deadlines:
            if dl.get("status") in ("completed", "cancelled"):
                continue
            if dl.get("confirmed_by_user"):
                continue
            due_str = dl.get("due_date", "")
            try:
                due_d = datetime.strptime(due_str[:10], "%Y-%m-%d").date()
                diff_days = (due_d - today_date).days
                if 0 <= diff_days <= 3:
                    unconfirmed_dls.append((diff_days, dl))
            except Exception:
                pass

        if unconfirmed_dls:
            unconfirmed_dls.sort(key=lambda x: x[0])
            diff_days, dl = unconfirmed_dls[0]
            bn_days = to_bangla_digits(diff_days)
            days_txt = "আজকের মধ্যে" if diff_days == 0 else f"আর {bn_days} দিন বাকি"
            return {
                "priority_tier": 3,
                "title": f"সময়সীমা নিশ্চিত করুন ({days_txt})",
                "description": f"গণনাকৃত সময়সীমা '{dl['title']}' যাচাই ও নিশ্চিত করুন যাতে স্বয়ংক্রিয় রিমাইন্ডার সক্রিয় থাকে।",
                "action_type": "confirm_deadline",
                "target_url": f"/cases/{dl['case_id']}?tab=deadlines" if dl.get("case_id") else f"/documents/{dl.get('document_id')}/notice",
                "case_id": dl.get("case_id"),
                "deadline_id": dl["id"],
                "reason_refs": [{"object_type": "deadline", "id": dl["id"], "rule": "unconfirmed_deadline_le_3d", "days_left": diff_days}],
                "explanation_bn": "সময়সীমা ৩ দিন বা তার কম সময়ের মধ্যে শেষ হচ্ছে কিন্তু এখনও নিশ্চিত করা হয়নি। নিশ্চিত না করলে পরবর্তী নোটিফিকেশন বন্ধ থাকবে।",
            }

        # -----------------------------------------------------------------------
        # Priority 4: Deadline <= 7 days with open tasks (0 <= days_left <= 7)
        # -----------------------------------------------------------------------
        tier4_candidates = []
        for dl in all_deadlines:
            if dl.get("status") in ("completed", "cancelled"):
                continue
            due_str = dl.get("due_date", "")
            try:
                due_d = datetime.strptime(due_str[:10], "%Y-%m-%d").date()
                diff_days = (due_d - today_date).days
                if 0 <= diff_days <= 7:
                    cid = dl.get("case_id")
                    open_tasks = [t for t in all_tasks if t.get("case_id") == cid and t.get("status") in ("not_started", "in_progress", "pending")]
                    if open_tasks:
                        tier4_candidates.append((diff_days, dl, open_tasks[0]))
            except Exception:
                pass

        if tier4_candidates:
            tier4_candidates.sort(key=lambda x: x[0])
            diff_days, dl, tsk = tier4_candidates[0]
            bn_days = to_bangla_digits(diff_days)
            return {
                "priority_tier": 4,
                "title": f"আসন্ন সময়সীমার টাস্ক সম্পন্ন করুন: {tsk['title']}",
                "description": f"সময়সীমা '{dl['title']}' আর {bn_days} দিন বাকি। নির্ধারিত টাস্ক সম্পন্ন করুন।",
                "action_type": "complete_task",
                "target_url": f"/cases/{dl['case_id']}?tab=tasks",
                "case_id": dl["case_id"],
                "task_id": tsk["id"],
                "reason_refs": [
                    {"object_type": "deadline", "id": dl["id"], "rule": "deadline_le_7d_with_open_tasks"},
                    {"object_type": "task", "id": tsk["id"], "rule": "open_task_for_deadline"},
                ],
                "explanation_bn": "সময়সীমা ৭ দিনের মধ্যে শেষ হতে যাচ্ছে এবং এর অধীনে অনিষ্পন্ন টাস্ক রয়েছে।",
            }

        # -----------------------------------------------------------------------
        # Priority 5: Lawyer/instruction task due (origin in ('lawyer', 'instruction'))
        # -----------------------------------------------------------------------
        lawyer_tasks = [
            t for t in all_tasks
            if t.get("origin") in ("lawyer", "instruction") and t.get("status") in ("not_started", "in_progress", "pending")
        ]
        if lawyer_tasks:
            tsk = lawyer_tasks[0]
            return {
                "priority_tier": 5,
                "title": f"আইনজীবীর নির্দেশিত টাস্ক: {tsk['title']}",
                "description": "আইনজীবীর অনুরোধ অনুযায়ী প্রয়োজনীয় তথ্য বা পদক্ষেপ প্রদান করুন।",
                "action_type": "complete_task",
                "target_url": f"/cases/{tsk['case_id']}?tab=tasks",
                "case_id": tsk["case_id"],
                "task_id": tsk["id"],
                "reason_refs": [{"object_type": "task", "id": tsk["id"], "rule": "lawyer_instruction_task"}],
                "explanation_bn": "আপনার আইনজীবী এই কাজটি সম্পন্ন করার নির্দেশনা দিয়েছেন। মামলার সফলতার জন্য এটি দ্রুত সম্পন্ন করুন।",
            }

        # -----------------------------------------------------------------------
        # Priority 6: Required document missing (rule / checklist driven, not "0 documents")
        # -----------------------------------------------------------------------
        for c in active_cases:
            attached_docs = self.db.list_case_documents(c["id"])
            attached_types = {d.get("doc_type") for d in attached_docs if d.get("doc_type")}
            attached_names = {d.get("filename") for d in attached_docs if d.get("filename")}

            ctype = c.get("case_type", "")
            required_checklist = list(CASE_TYPE_REQUIRED_DOCUMENTS.get(ctype, []))

            meta_json = {}
            if c.get("metadata_json"):
                try:
                    meta_json = json.loads(c["metadata_json"])
                except Exception:
                    meta_json = {}

            if meta_json.get("required_documents"):
                custom_reqs = meta_json["required_documents"]
                required_checklist = [
                    {"doc_type": r, "title": r, "status": "APPROVED"} if isinstance(r, str) else r
                    for r in custom_reqs
                ]

            missing_reqs = []
            for req in required_checklist:
                rtype = req.get("doc_type")
                rtitle = req.get("title")
                if rtype not in attached_types and rtitle not in attached_names:
                    missing_reqs.append(req)

            has_explicit_missing = bool(meta_json.get("has_missing_documents") or meta_json.get("missing_documents"))

            if missing_reqs or has_explicit_missing:
                first_missing = missing_reqs[0] if missing_reqs else {"title": "প্রয়োজনীয় প্রমাণপত্র", "status": "APPROVED"}
                is_draft = first_missing.get("status") == "DRAFT_NOT_REVIEWED"
                placeholder = " [DRAFT_NOT_REVIEWED / খসড়া চেকলিস্ট]" if is_draft else ""
                doc_name = first_missing.get("title", "দলিল")

                return {
                    "priority_tier": 6,
                    "title": f"{c['title']}: {doc_name} আপলোড করুন{placeholder}",
                    "description": f"মামলাটির আইনি ভিত্তি নিশ্চিত করতে প্রয়োজনীয় নথি '{doc_name}' আপলোড করা আবশ্যক।",
                    "action_type": "upload_document",
                    "target_url": f"/cases/{c['id']}?tab=documents",
                    "case_id": c["id"],
                    "reason_refs": [{"object_type": "case", "id": c["id"], "rule": "missing_required_document", "missing_doc": doc_name}],
                    "explanation_bn": "মামলার ধরণ অনুযায়ী এই নথিটি অপরিহার্য। এটি দাখিল না করা পর্যন্ত পরবর্তী আইনি পদক্ষেপ ব্যাহত হতে পারে।",
                }

        # -----------------------------------------------------------------------
        # Priority 7: Extracted fields awaiting review (status == 'extracted')
        # -----------------------------------------------------------------------
        with self.db.get_session() as session:
            from packages.trust_kernel.db import DocumentDB, DocumentFieldDB
            pending_fields = (
                session.query(DocumentFieldDB)
                .join(DocumentDB, DocumentDB.id == DocumentFieldDB.document_id)
                .filter(DocumentDB.owner_id == user_id, DocumentFieldDB.state == "extracted")
                .first()
            )
            if pending_fields:
                doc = self.db.get_document(pending_fields.document_id)
                fld_doc_name: str = str(doc.get("filename")) if (doc and doc.get("filename")) else "দলিল"
                return {
                    "priority_tier": 7,
                    "title": f"তথ্য যাচাই সম্পন্ন করুন: {fld_doc_name}",
                    "description": "নথি থেকে স্বয়ংক্রিয়ভাবে সংগৃহীত তথ্য ও সময়সীমা পর্যালোচনা করে অনুমোদন দিন।",
                    "action_type": "review_extracted_fields",
                    "target_url": f"/documents/{pending_fields.document_id}/review",
                    "case_id": doc.get("case_id") if doc else None,
                    "document_id": pending_fields.document_id,
                    "reason_refs": [{"object_type": "document", "id": pending_fields.document_id, "rule": "extracted_fields_awaiting_review"}],
                    "explanation_bn": "স্বয়ংক্রিয়ভাবে চিহ্নিত তথ্যগুলো আইনগতভাবে ব্যবহার করার আগে আপনার যাচাই ও অনুমোদন প্রয়োজন।",
                }

        # -----------------------------------------------------------------------
        # Priority 8: AI-proposed facts/events awaiting confirmation (is_proposed == True)
        # -----------------------------------------------------------------------
        for c in active_cases:
            facts = self.db.list_case_facts(c["id"], include_proposed=True)
            proposed_facts = [f for f in facts if f.get("is_proposed") and f.get("status") == "proposed"]
            if proposed_facts:
                f = proposed_facts[0]
                return {
                    "priority_tier": 8,
                    "title": f"{c['title']}: AI-প্রস্তাবিত তথ্য নিশ্চিত করুন",
                    "description": f"প্রস্তাবিত তথ্য: {f['fact_text'][:60]}... নিশ্চিত বা বাতিল করুন।",
                    "action_type": "confirm_proposed_fact",
                    "target_url": f"/cases/{c['id']}?tab=review",
                    "case_id": c["id"],
                    "fact_id": f["id"],
                    "reason_refs": [{"object_type": "case_fact", "id": f["id"], "rule": "proposed_fact_confirmation"}],
                    "explanation_bn": "AI কেস রিভিউ থেকে প্রাপ্ত তথ্যটি আপনার অনুমোদন ছাড়া মামলায় সক্রিয় করা হবে না।",
                }

        # -----------------------------------------------------------------------
        # Priority 9: Draft in progress (draft.status == 'in_progress' or metadata)
        # -----------------------------------------------------------------------
        for c in active_cases:
            is_draft = False
            if c.get("metadata_json"):
                try:
                    m_json = json.loads(c["metadata_json"])
                    if m_json.get("draft_in_progress") or m_json.get("draft_status") == "in_progress":
                        is_draft = True
                except Exception:
                    pass
            if c.get("status") == "draft_in_progress" or is_draft:
                return {
                    "priority_tier": 9,
                    "title": f"{c['title']}: খসড়া জবাব বা দলিলের কাজ চালিয়ে যান",
                    "description": "অসম্পূর্ণ খসড়াটি পর্যালোচনা করে প্রস্তুত সম্পন্ন করুন।",
                    "action_type": "continue_draft",
                    "target_url": f"/cases/{c['id']}?tab=overview",
                    "case_id": c["id"],
                    "reason_refs": [{"object_type": "case", "id": c["id"], "rule": "draft_in_progress"}],
                    "explanation_bn": "আপনার একটি খসড়া প্রস্তুত প্রক্রিয়াধীন রয়েছে। এটি চূড়ান্ত করতে কাজ চালিয়ে যান।",
                }

        # -----------------------------------------------------------------------
        # Priority 10: next.none ("all caught up" / explore default)
        # AC-M02-2: every Next Action has non-empty reason_refs that resolve to existing objects
        # -----------------------------------------------------------------------
        if active_cases:
            first_c = active_cases[0]
            return {
                "priority_tier": 10,
                "title": "সব কাজ সম্পন্ন! কোনো জরুরি পদক্ষেপ নেই",
                "description": "আপনার সকল মামলার জরুরি পদক্ষেপ সম্পন্ন হয়েছে। মামলার সার্বিক অগ্রগতি পর্যবেক্ষণ করতে পারেন।",
                "action_type": "next.none",
                "target_url": f"/cases/{first_c['id']}?tab=overview",
                "case_id": first_c["id"],
                "reason_refs": [{"object_type": "case", "id": first_c["id"], "rule": "all_caught_up"}],
                "explanation_bn": "বর্তমানে কোনো জরুরি সময়সীমা বা কাজ নেই। আপনি নিশ্চিন্ত থাকতে পারেন।",
            }
        else:
            return {
                "priority_tier": 10,
                "title": "কোনো সক্রিয় মামলা বা পদক্ষেপ নেই",
                "description": "নতুন কোনো আইনি প্রশ্ন বা নোটিশ থাকলে তা যুক্ত করে সেবা গ্রহণ শুরু করুন।",
                "action_type": "next.none",
                "target_url": "/intake",
                "case_id": None,
                "reason_refs": [{"object_type": "user", "id": user_id, "rule": "empty_state_no_cases"}],
                "explanation_bn": "আপনার কোনো চলমান মামলা নেই। নতুন সমস্যা লিখে বা নোটিশ আপলোড করে শুরু করুন।",
            }

    def _find_unconfirmed_notices(self, user_id: str) -> list[dict[str, Any]]:
        """Finds notice documents where deadlines are not yet confirmed."""
        with self.db.get_session() as session:
            from packages.trust_kernel.db import DocumentDB, NoticeAnalysisDB
            rows = (
                session.query(DocumentDB)
                .join(NoticeAnalysisDB, NoticeAnalysisDB.document_id == DocumentDB.id)
                .filter(DocumentDB.owner_id == user_id, DocumentDB.deleted_at.is_(None))
                .order_by(DocumentDB.uploaded_at.desc())
                .all()
            )
            unconfirmed = []
            for r in rows:
                dls = self.db.list_deadlines(document_id=r.id)
                if not dls or any(not dl.get("confirmed_by_user") for dl in dls):
                    unconfirmed.append({"id": r.id, "filename": r.filename, "case_id": r.case_id})
            return unconfirmed

    def get_home_data(self, user_id: str) -> dict[str, Any]:
        """Aggregates all components for the citizen Home screen (SRS M02)."""
        user = self.db.get_user(user_id) or {}
        user_name = user.get("name") or "নাগরিক"
        greeting = f"{self._get_time_aware_greeting()}, {user_name}!"

        # Next Action
        next_action = self.calculate_next_action(user_id)

        # My Cases (up to 3 most recent active)
        all_cases = self.db.list_cases(owner_id=user_id)
        active_cases = [c for c in all_cases if c.get("status") != "archived"][:3]

        # Upcoming (next 5 deadlines/events across all cases)
        today_date = self._get_dhaka_time().date()
        upcoming_items = []
        for c in active_cases:
            dls = self.db.list_deadlines(case_id=c["id"])
            for dl in dls:
                if dl.get("status") in ("completed", "cancelled"):
                    continue
                try:
                    due_d = datetime.strptime(dl["due_date"], "%Y-%m-%d").date()
                    diff = (due_d - today_date).days
                    upcoming_items.append({
                        "id": dl["id"],
                        "case_id": c["id"],
                        "case_title": c["title"],
                        "title": dl["title"],
                        "due_date": dl["due_date"],
                        "days_left": diff,
                        "days_left_bn": to_bangla_digits(max(0, diff)) + " দিন বাকি" if diff >= 0 else "মেয়াদ উত্তীর্ণ",
                    })
                except Exception:
                    pass

        upcoming_items.sort(key=lambda x: x["days_left"])
        upcoming_items = upcoming_items[:5]

        return {
            "greeting": greeting,
            "user_name": user_name,
            "problem_input": {
                "placeholder": "আপনার সমস্যা বাংলায় লিখুন",
                "action_route": "/intake",
                "target_url": "/intake",
                "mic_disabled": True,
                "mic_tooltip": "ভয়েস ইনপুট শীঘ্রই আসছে",
            },
            "next_action": next_action,
            "quick_actions": [
                {"title": "নোটিশ বা দলিল আপলোড", "url": "/documents/upload", "icon": "upload"},
                {"title": "আইনি প্রশ্ন জিজ্ঞাসা", "url": "/intake", "icon": "help"},
                {"title": "আইনি সহায়তা ও লাইব্রেরি", "url": "/library", "icon": "book"},
            ],
            "my_cases": active_cases,
            "upcoming": upcoming_items,
            "footer_disclaimer": "AIN-AI আইনজীবীর বিকল্প নয়",
        }
