"""
Notice Interpreter & Deadlines Engine (SRS Module M04, Part of M07, Sprint S5).
Orchestrates:
1. Notice classification & edge case detection (blurry, multi-notice, handwriting, non-notice, English).
2. AI Gateway task notice.explain.v1 execution with schema validation retry and fallback.
3. Citation Verifier enforcement on all claims (document spans & statutory citations).
4. Strict "If you ignore it" consequence grounding (fallback if unverified).
5. Deterministic Rules Engine integration for relative deadlines (relative_period.calendar_days.v1).
6. Deadline confirmation and automated reminder scheduling (AC-M07-1).
7. Save to case (minimal case, task checklist, confirmed deadline).
8. Simpler Bangla explanation rewrite (notice.explain_simpler.v1).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from packages.trust_kernel.ai_gateway import AIGateway, SchemaValidationError
from packages.trust_kernel.citation_verifier import CitationVerifier, citation_verifier
from packages.trust_kernel.db import DatabaseManager, db_manager
from packages.trust_kernel.rules_engine import RulesEngine

logger = logging.getLogger(__name__)

BN_DIGITS = "০১২৩৪৫৬৭৮৯"
_EN_TO_BN = str.maketrans("0123456789", BN_DIGITS)
_BN_TO_EN = str.maketrans(BN_DIGITS, "0123456789")


def to_bangla_digits(val: Any) -> str:
    return str(val).translate(_EN_TO_BN)


def to_ascii_digits(val: Any) -> str:
    return str(val).translate(_BN_TO_EN)


def format_bangla_date(date_str: str) -> str:
    """Converts YYYY-MM-DD to Bangla representation (e.g. ১৫ অক্টোবর ২০২৬)."""
    months_bn = {
        "01": "জানুয়ারি",
        "02": "ফেব্রুয়ারি",
        "03": "মার্চ",
        "04": "এপ্রিল",
        "05": "মে",
        "06": "জুন",
        "07": "জুলাই",
        "08": "আগস্ট",
        "09": "সেপ্টেম্বর",
        "10": "অক্টোবর",
        "11": "নভেম্বর",
        "12": "ডিসেম্বর",
    }
    try:
        parts = date_str[:10].split("-")
        if len(parts) == 3:
            year, month, day = parts
            day_bn = to_bangla_digits(int(day))
            month_bn = months_bn.get(month, month)
            year_bn = to_bangla_digits(year)
            return f"{day_bn} {month_bn} {year_bn}"
    except Exception:
        pass
    return to_bangla_digits(date_str)


class NoticeEngine:
    def __init__(
        self,
        db: DatabaseManager | None = None,
        gateway: AIGateway | None = None,
        verifier: CitationVerifier | None = None,
        rules_engine: RulesEngine | None = None,
    ):
        self.db = db or db_manager
        self.gateway = gateway or AIGateway(self.db)
        self.verifier = verifier or citation_verifier
        self.rules_engine = rules_engine or RulesEngine(self.db)

    def interpret_notice(
        self,
        document_id: str,
        user_id: str,
        as_of_date: str | None = None,
    ) -> dict[str, Any]:
        """
        Interprets a legal notice document according to SRS M04.
        Fixed order of 8 required sections:
        1. Label bar (amber banner, AI disclaimer, as-of date, plain certainty word)
        2. In one line (summary with source chips)
        3. Who sent it · Why received · What it says
        4. What you must do (actionable checklist)
        5. Important date / DeadlineCard
        6. Documents you need to gather
        7. If you ignore it (strictly grounded or fallback)
        8. Questions to ask your lawyer
        """
        # 1. Ownership & Access Verification
        doc = self.db.get_document(document_id)
        if not doc:
            raise ValueError(f"Document '{document_id}' not found.")

        # Check access permission
        if doc.get("owner_id") and doc["owner_id"] != user_id:
            # Check if user is admin or has valid consent
            user = self.db.get_user(user_id)
            user_role = user.get("role", "citizen") if user else "citizen"
            if user_role not in ("admin", "reviewer"):
                # Check consent
                has_consent = self.db.has_active_consent(
                    grantor_id=doc["owner_id"],
                    grantee_id=user_id,
                    scope="documents.read",
                )
                if not has_consent:
                    raise PermissionError(f"User '{user_id}' does not have permission to view document '{document_id}'.")

        # 2. Extract Document Pages and Combined OCR Text
        pages = self.db.get_document_pages(document_id)
        if not pages:
            # Check document record itself
            combined_text = doc.get("full_text") or ""
            avg_confidence = 0.95 if combined_text else 0.0
        else:
            combined_text = " ".join([p.get("ocr_text", "") for p in pages if p.get("ocr_text")]).strip()
            confidences = [p.get("ocr_confidence", 0.9) for p in pages if p.get("ocr_confidence") is not None]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.9

        eff_as_of_date = as_of_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # 3. Detect Edge Cases
        is_blurry = avg_confidence < 0.50 or len(combined_text.strip()) < 25 or "[অস্পষ্ট স্ক্যান]" in combined_text
        has_handwriting = "হাতের লেখা" in combined_text or "[হাতে লেখা]" in combined_text or "handwritten" in combined_text.lower()
        multiple_notices = (
            "একাধিক নোটিশ" in combined_text
            or "দুটি নোটিশ" in combined_text
            or "২টি নোটিশ" in combined_text
            or "প্রথম নোটিশ" in combined_text
            or "multiple notices" in combined_text.lower()
            or "two notices" in combined_text.lower()
        )
        is_non_notice = (
            "নন-নোটিশ" in combined_text
            or "চালান" in combined_text
            or ("বিক্রয় কবলা দলিল" in combined_text and "নোটিশ" not in combined_text)
            or ("ভাউচার" in combined_text and "নোটিশ" not in combined_text)
        )

        # Fallback state if scan is too blurry / unreadable (SRS M04 Edge Case)
        if is_blurry:
            fallback_res = self._build_unreadable_fallback(document_id, eff_as_of_date)
            self.db.save_notice_analysis(document_id, user_id, fallback_res, "not_sure", eff_as_of_date)
            self._log_audit(user_id, "notice.interpreted.fallback_unreadable", document_id)
            return fallback_res

        # 4. AI Gateway Execution (Task notice.explain.v1) with Retry
        analysis_data = None
        for attempt in (1, 2):
            try:
                gw_res = self.gateway.execute_prompt(
                    prompt_id="notice.explain.v1",
                    variables={
                        "document_text": combined_text,
                        "as_of_date": eff_as_of_date,
                    },
                    user_id=user_id,
                )
                analysis_data = gw_res["data"]
                provider_type = gw_res.get("provider", "fake")
                break
            except SchemaValidationError as e:
                logger.warning("Attempt %s for notice.explain.v1 schema validation failed: %s", attempt, e)
                if attempt == 2:
                    fallback_res = self._build_unreadable_fallback(document_id, eff_as_of_date, error_msg="নথিটির কাঠামো স্পষ্টভাবে পড়া সম্ভব হয়নি।")
                    self.db.save_notice_analysis(document_id, user_id, fallback_res, "not_sure", eff_as_of_date)
                    return fallback_res

        if not analysis_data:
            return self._build_unreadable_fallback(document_id, eff_as_of_date)

        analysis_data["provider"] = provider_type

        # Override edge case flags detected from text
        if is_non_notice:
            analysis_data["is_notice"] = False
            analysis_data["certainty"] = "check"
        if has_handwriting:
            analysis_data["has_handwriting"] = True
            analysis_data["certainty"] = "check"
        if multiple_notices:
            analysis_data["multiple_notices_detected"] = True
            analysis_data["certainty"] = "check"

        # 5. Citation Verifier Post-Processing on Claims
        claims_to_store = []
        for section_key in ["what_is_this", "sender", "why_received"]:
            item = analysis_data.get(section_key, {})
            text = item.get("text", "")
            claims = item.get("claims", [])
            for c in claims:
                report = self.verifier.verify_span(c.get("text", text), combined_text, c.get("span_ref"))
                c["verification_status"] = report.status
                c["match_score"] = report.match_score
                claims_to_store.append(c)

        for array_key in ["what_it_says", "action_required", "documents_needed"]:
            items = analysis_data.get(array_key, [])
            for item in items:
                text = item.get("text", "")
                claims = item.get("claims", [])
                for c in claims:
                    report = self.verifier.verify_span(c.get("text", text), combined_text, c.get("span_ref"))
                    c["verification_status"] = report.status
                    c["match_score"] = report.match_score
                    claims_to_store.append(c)

        # 6. Strict "If you ignore it" Rule (AC-M04-4, SRS Section M04)
        # ONLY show if stated in the notice or supported by an approved statutory passage;
        # otherwise show: "নথিতে এমন কিছু উল্লেখ নেই। একজন আইনজীবীর পরামর্শ নিন।"
        if_ignored = analysis_data.get("if_ignored", {})
        consequence_text = if_ignored.get("text", "")
        stated_in_notice = if_ignored.get("stated_in_notice", False)

        has_verified_support = False
        if stated_in_notice and consequence_text:
            # Check if there is support in notice text
            report = self.verifier.verify_span(consequence_text, combined_text)
            if report.status == "VERIFIED":
                has_verified_support = True
            else:
                # Also check keywords like 'মামলা', 'উচ্ছেদ', 'ফৌজদারি'
                for kw in ["মামলা", "আদালত", "উচ্ছেদ", "দণ্ড", "জরিমানা"]:
                    if kw in combined_text and kw in consequence_text:
                        has_verified_support = True
                        break

        if not has_verified_support:
            analysis_data["if_ignored"] = {
                "text": "নথিতে এমন কিছু উল্লেখ নেই। একজন আইনজীবীর পরামর্শ নিন।",
                "claims": [],
                "stated_in_notice": False,
                "not_stated": True,
            }

        # 7. Dates and DeadlineCard Preparation
        # Stated dates labeled "নোটিশে লেখা তারিখ, অনুগ্রহ করে নিশ্চিত করুন"
        # Relative periods prompt for trigger date, compute via Rules Engine
        important_dates = analysis_data.get("important_dates", [])
        processed_dates = []
        for d in important_dates:
            stated_date = d.get("stated_date")
            relative = d.get("relative")
            stated_text = d.get("stated_text", "")

            # Security Guard (Decision D6): Never keep free-text LLM dates without provenance
            if stated_date and not (stated_date in combined_text or format_bangla_date(stated_date) in combined_text or to_bangla_digits(stated_date) in combined_text):
                # Stated date does not match source text verbatim
                stated_date = None

            d_entry = {
                "label": d.get("label", "গুরুত্বপূর্ণ তারিখ"),
                "stated_text": stated_text,
                "stated_date": stated_date,
                "stated_date_formatted_bn": format_bangla_date(stated_date) if stated_date else None,
                "date_label_note": "নোটিশে লেখা তারিখ, অনুগ্রহ করে নিশ্চিত করুন" if stated_date else None,
                "relative": relative,
                "requires_trigger_date": bool(relative),
                "is_confirmed": False,
            }
            processed_dates.append(d_entry)

        analysis_data["important_dates"] = processed_dates

        # 8. Compute Days Left if stated date is present
        primary_deadline_card = self._build_primary_deadline_card(processed_dates, eff_as_of_date)
        analysis_data["primary_deadline_card"] = primary_deadline_card

        # 9. Format UI Labels and Banner Metadata
        certainty_map = {
            "clear": {"word_bn": "স্পষ্ট", "style": "success"},
            "check": {"word_bn": "যাচাই করুন", "style": "warning"},
            "not_sure": {"word_bn": "নিশ্চিত নই", "style": "danger"},
        }
        certainty_key = analysis_data.get("certainty", "clear")
        certainty_meta = certainty_map.get(certainty_key, certainty_map["check"])

        analysis_data["label_bar"] = {
            "disclaimer_text": "AI ব্যাখ্যা — আইনজীবীর দ্বারা যাচাইকৃত নয়",
            "as_of_date": eff_as_of_date,
            "as_of_date_formatted_bn": format_bangla_date(eff_as_of_date),
            "certainty_label": certainty_meta["word_bn"],
            "certainty_key": certainty_key,
            "background_class": "bg-amber-100 border-amber-400 text-amber-900",
        }

        # 10. Persist Analysis and Audit Log
        self.db.save_notice_analysis(
            document_id=document_id,
            user_id=user_id,
            analysis=analysis_data,
            certainty=certainty_key,
            as_of_date=eff_as_of_date,
        )
        self._log_audit(user_id, "notice.interpreted", document_id)

        return analysis_data

    def _build_primary_deadline_card(self, dates: list[dict[str, Any]], as_of_date: str) -> dict[str, Any]:
        """Builds interactive DeadlineCard view model with Bangla digits and calculation state."""
        as_of_dt = datetime.strptime(as_of_date[:10], "%Y-%m-%d").date()

        for d in dates:
            if d.get("stated_date"):
                try:
                    due_dt = datetime.strptime(d["stated_date"][:10], "%Y-%m-%d").date()
                    days_left = (due_dt - as_of_dt).days
                    days_left_bn = to_bangla_digits(max(0, days_left))
                    return {
                        "has_deadline": True,
                        "type": "stated",
                        "due_date": d["stated_date"],
                        "due_date_bn": format_bangla_date(d["stated_date"]),
                        "days_left": days_left,
                        "days_left_text": f"{days_left_bn} দিন বাকি",
                        "note": "নোটিশে লেখা তারিখ, অনুগ্রহ করে নিশ্চিত করুন",
                        "calculation_steps": [
                            f"নোটিশে উল্লেখিত তারিখ: {format_bangla_date(d['stated_date'])}",
                            f"হিসাবের ভিত্তি তারিখ: {format_bangla_date(as_of_date)}",
                            f"অবশিষ্ট সময়: {days_left_bn} দিন",
                        ],
                        "can_confirm": True,
                        "is_confirmed": False,
                    }
                except Exception:
                    pass

            if d.get("relative"):
                rel = d["relative"]
                val = rel.get("period_value", 15)
                val_bn = to_bangla_digits(val)
                return {
                    "has_deadline": True,
                    "type": "relative",
                    "requires_trigger_input": True,
                    "prompt_question": "নোটিশটি আপনি কবে হাতে পেয়েছেন বা গ্রহণ করেছেন?",
                    "period_days": val,
                    "period_days_bn": val_bn,
                    "note": f"নোটিশ প্রাপ্তির {val_bn} দিনের মধ্যে পদক্ষেপ গ্রহণ করতে হবে।",
                    "rule_id": "relative_period.calendar_days.v1",
                    "can_confirm": False,
                    "is_confirmed": False,
                }

        return {
            "has_deadline": False,
            "note": "নোটিশে নির্দিষ্ট কোনো সময়সীমা উল্লেখ পাওয়া যায়নি।",
        }

    def _build_unreadable_fallback(self, document_id: str, as_of_date: str, error_msg: str | None = None) -> dict[str, Any]:
        """Returns standard fallback payload when document scan cannot be read clearly (SRS M04)."""
        msg = error_msg or "স্ক্যানটি অস্পষ্ট বা অসম্পূর্ণ হওয়ায় স্পষ্টভাবে পড়া যায়নি।"
        return {
            "language": "bn",
            "certainty": "not_sure",
            "is_notice": True,
            "summary_one_line": "আমরা এটি স্পষ্টভাবে পড়তে পারছি না। অনুগ্রহ করে স্পষ্ট কপি আপলোড করুন।",
            "summary_chips": [],
            "what_is_this": {"text": "অস্পষ্ট বা অপাঠ্য নথি।", "claims": []},
            "sender": {"text": "প্রেরকের তথ্য স্পষ্টভাবে পাঠোদ্ধার করা যায়নি।", "claims": []},
            "why_received": {"text": msg, "claims": []},
            "what_it_says": [{"text": "নথিটি স্পষ্ট না হওয়ায় বক্তব্য বিশ্লেষণ সম্ভব নয়।", "claims": []}],
            "action_required": [
                {"text": "নথিটির একটি স্পষ্ট, উজ্জ্বল ছবি বা স্ক্যান কপি পুনরায় আপলোড করুন।", "claims": []},
                {"text": "প্রয়োজনে নথিটি নিয়ে সরাসরি একজন আইনজীবীর পরামর্শ নিন।", "claims": []},
            ],
            "important_dates": [],
            "documents_needed": [{"text": "মূল নথির সুস্পষ্ট কপি", "claims": []}],
            "if_ignored": {
                "text": "নথিতে এমন কিছু উল্লেখ নেই। একজন আইনজীবীর পরামর্শ নিন।",
                "claims": [],
                "stated_in_notice": False,
                "not_stated": True,
            },
            "questions_for_lawyer": ["এই অস্পষ্ট নোটিশটির বিষয়ে আমি কিভাবে তথ্য সংগ্রহ করতে পারি?"],
            "primary_deadline_card": {"has_deadline": False, "note": "অস্পষ্ট নথির কারণে কোনো সময়সীমা নির্ধারণ করা যায়নি।"},
            "label_bar": {
                "disclaimer_text": "AI ব্যাখ্যা — আইনজীবীর দ্বারা যাচাইকৃত নয়",
                "as_of_date": as_of_date,
                "as_of_date_formatted_bn": format_bangla_date(as_of_date),
                "certainty_label": "নিশ্চিত নই",
                "certainty_key": "not_sure",
                "background_class": "bg-red-100 border-red-400 text-red-900",
            },
            "provider": "fake",
        }

    def calculate_relative_deadline(
        self,
        document_id: str,
        trigger_date: str,
        days: int,
        include_trigger_day: bool = False,
        label: str = "নোটিশের জবাব দাখিল",
    ) -> dict[str, Any]:
        """
        Executes Rules Engine relative_period.calendar_days.v1 with 'How we counted this' breakdown.
        """
        calc_res = self.rules_engine.compute(
            rule_id="relative_period.calendar_days.v1",
            inputs={
                "start_date": trigger_date,
                "days": days,
                "include_trigger_day": include_trigger_day,
            },
        )
        result_date = calc_res["result_date"]
        due_date_bn = format_bangla_date(result_date)
        start_date_bn = format_bangla_date(trigger_date)
        days_bn = to_bangla_digits(days)

        steps = [
            f"নোটিশ প্রাপ্তির শুরুর তারিখ: {start_date_bn}",
            f"{'প্রাপ্তির দিনটি প্রথম দিন ধরে ' if include_trigger_day else 'প্রাপ্তির দিন ব্যতিরেকে '} মোট {days_bn} ক্যালেন্ডার দিন গণনা করা হয়েছে।",
            "অনুমান ও সীমাবদ্ধতা: ক্যালেন্ডার দিন অনুযায়ী হিসাবকৃত; আদালত বা সরকারি ছুটির দিন সমন্বয় করা হয়নি — আইনজীবীর সাথে নিশ্চিত হন।",
            f"নির্ধারিত শেষ তারিখ: {due_date_bn}",
        ]

        now_dt = datetime.now(timezone.utc).date()
        due_dt = datetime.strptime(result_date[:10], "%Y-%m-%d").date()
        days_left = (due_dt - now_dt).days
        days_left_bn = to_bangla_digits(max(0, days_left))

        return {
            "has_deadline": True,
            "type": "relative_calculated",
            "title": label,
            "trigger_date": trigger_date,
            "trigger_date_bn": start_date_bn,
            "days": days,
            "days_bn": days_bn,
            "include_trigger_day": include_trigger_day,
            "due_date": result_date,
            "due_date_bn": due_date_bn,
            "days_left": days_left,
            "days_left_text": f"{days_left_bn} দিন বাকি",
            "rule_key": "relative_period.calendar_days.v1",
            "rule_version": "1.0.0",
            "calculation_steps": steps,
            "explanation": calc_res["explanation"],
            "can_confirm": True,
            "is_confirmed": False,
        }

    def explain_simpler(self, document_id: str, user_id: str) -> dict[str, Any]:
        """
        Executes AI Gateway task notice.explain_simpler.v1 and stores in DB.
        """
        existing = self.db.get_notice_analysis(document_id)
        if not existing or not existing.get("analysis"):
            raise ValueError(f"Notice analysis for document '{document_id}' not found. Please interpret first.")

        analysis = existing["analysis"]
        gw_res = self.gateway.execute_prompt(
            prompt_id="notice.explain_simpler.v1",
            variables={"analysis_json": json.dumps(analysis, ensure_ascii=False)},
            user_id=user_id,
        )
        simpler_data = gw_res["data"]
        self.db.update_notice_simpler(document_id, simpler_data)
        self._log_audit(user_id, "notice.simpler_explained", document_id)
        return simpler_data

    def confirm_deadline(self, deadline_id: str, user_id: str) -> dict[str, Any]:
        """
        Confirms a deadline, scheduling automated reminders (AC-M04-2, AC-M07-1).
        """
        res = self.db.confirm_deadline(deadline_id, user_id)
        if not res:
            raise ValueError(f"Deadline '{deadline_id}' not found.")
        self._log_audit(user_id, "deadline.confirmed", deadline_id)
        return res

    def dismiss_or_meet_deadline(self, deadline_id: str, status: str = "completed") -> dict[str, Any]:
        """
        Dismisses or meets a deadline, cancelling pending reminders (AC-M07-1).
        """
        res = self.db.dismiss_or_meet_deadline(deadline_id, status)
        if not res:
            raise ValueError(f"Deadline '{deadline_id}' not found.")
        return res

    def save_to_case(
        self,
        document_id: str,
        user_id: str,
        case_id: str | None = None,
        new_case_title: str | None = None,
        selected_task_indices: list[int] | None = None,
        confirmed_deadline_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Saves notice interpretation to case (SRS M04 Step 3):
        - Creates case (if none provided)
        - Links document to case
        - Creates tasks from selected checklist items
        - Creates confirmed deadline and schedules reminders (AC-M07-1)
        """
        doc = self.db.get_document(document_id)
        if not doc:
            raise ValueError(f"Document '{document_id}' not found.")

        case_data: dict[str, Any]
        if not case_id:
            title = new_case_title or f"আইনি নোটিশ বিষয়: {doc.get('filename', 'নতুন মামলা')}"
            case_data = self.db.create_case(
                owner_id=user_id,
                title=title,
                case_type="legal_notice",
                description=f"নোটিশ নথি {document_id} থেকে প্রস্তুতকৃত মামলা।",
            )
            case_id = case_data["id"]
        else:
            existing_case = self.db.get_case(case_id)
            if not existing_case:
                raise ValueError(f"Case '{case_id}' not found.")
            case_data = existing_case

        # Link document to case
        # We can update document case_id directly via SQL
        from sqlalchemy import text
        with self.db.engine.connect() as conn:
            conn.execute(
                text("UPDATE documents SET case_id = :case_id WHERE id = :doc_id"),
                {"case_id": case_id, "doc_id": document_id},
            )
            conn.commit()

        # 2. Create tasks from checklist items
        analysis_record = self.db.get_notice_analysis(document_id)
        created_tasks = []
        if analysis_record and analysis_record.get("analysis"):
            action_items = analysis_record["analysis"].get("action_required", [])
            indices_to_add = selected_task_indices if selected_task_indices is not None else list(range(len(action_items)))
            for idx in indices_to_add:
                if 0 <= idx < len(action_items):
                    item = action_items[idx]
                    task_title = item.get("task_suggestion", {}).get("title") or item.get("text")
                    t = self.db.create_task(
                        case_id=case_id,
                        title=task_title,
                        description=item.get("text"),
                        owner_id=user_id,
                        document_id=document_id,
                        status="not_started",
                    )
                    created_tasks.append(t)

        # 3. Create confirmed deadline (if provided)
        created_deadline = None
        if confirmed_deadline_data and confirmed_deadline_data.get("due_date"):
            dl_title = confirmed_deadline_data.get("title", "আইনি নোটিশের জবাব দাখিল")
            due_date = confirmed_deadline_data["due_date"]
            rule_key = confirmed_deadline_data.get("rule_key")
            calc_steps = confirmed_deadline_data.get("calculation_steps", [])
            is_user_set = confirmed_deadline_data.get("is_user_set", False)

            created_deadline = self.db.create_deadline(
                case_id=case_id,
                title=dl_title,
                due_date=due_date,
                user_id=user_id,
                document_id=document_id,
                rule_key=rule_key,
                calc_steps=calc_steps,
                calculation_basis=confirmed_deadline_data.get("note"),
                is_user_set=is_user_set,
                confirmed_by_user=True,  # Explicitly confirmed by user action
            )

        self._log_audit(user_id, "notice.saved_to_case", case_id, {"document_id": document_id})

        return {
            "status": "success",
            "case_id": case_id,
            "document_id": document_id,
            "tasks_created": len(created_tasks),
            "tasks": created_tasks,
            "deadline": created_deadline,
        }

    def _log_audit(self, user_id: str, action: str, object_id: str, details: dict[str, Any] | None = None):
        """Records an immutable audit event in Trust Kernel audit log."""
        self.db.record_audit_event(
            actor_id=user_id,
            actor_type="user",
            action=action,
            object_type="document_notice",
            object_id=object_id,
            details=details or {},
        )


notice_engine = NoticeEngine()
