"""
Guided Drafting Engine (SRS Module M05 / Sprint S8).
Manages template schemas, question workflows, conditional dependencies, prefill validation,
consistency checks, execution checklists, live previews, and encrypted exports (PDF/DOCX/TXT).
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from docx import Document
from docx.shared import Pt, RGBColor

from packages.trust_kernel.ai_gateway import AIGateway, to_bangla_digits
from packages.trust_kernel.audit import audit_service
from packages.trust_kernel.db import (
    DatabaseManager,
    DocumentFieldDB,
    db_manager,
)
from packages.trust_kernel.num_to_words import (
    verify_numeral_word_consistency,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = REPO_ROOT / "backend" / "app" / "static"
FONTS_DIR = STATIC_DIR / "fonts"

# Encryption key for draft exports (reported as STUBBED key management, rotation not implemented)
DEV_DRAFT_STORAGE_KEY_DEFAULT = "ain-ai-draft-export-encryption-secret-2026"


def _get_draft_storage_key() -> str:
    """Returns draft encryption storage key. Fails closed in production (DEV_MODE=false) if missing, default, or < 32 bytes."""
    is_dev = os.getenv("DEV_MODE", "false").lower() in ("true", "1", "yes")
    key = os.getenv("DRAFT_STORAGE_KEY")
    if not is_dev:
        if not key or key == DEV_DRAFT_STORAGE_KEY_DEFAULT:
            raise RuntimeError(
                "CRITICAL SECURITY CONFIGURATION: 'DRAFT_STORAGE_KEY' must be set to a secure non-default secret in production (DEV_MODE=false)."
            )
        if len(key.encode("utf-8")) < 32:
            raise RuntimeError(
                "CRITICAL SECURITY CONFIGURATION: 'DRAFT_STORAGE_KEY' must be at least 32 bytes (256 bits) in production (DEV_MODE=false)."
            )
        return key
    return key or DEV_DRAFT_STORAGE_KEY_DEFAULT


DRAFT_STORAGE_KEY = os.environ.get("DRAFT_STORAGE_KEY", DEV_DRAFT_STORAGE_KEY_DEFAULT)

_REGULAR_FONT_BASE64: str | None = None
_BOLD_FONT_BASE64: str | None = None


def _get_font_base64() -> tuple[str, str]:
    global _REGULAR_FONT_BASE64, _BOLD_FONT_BASE64
    if _REGULAR_FONT_BASE64 is None:
        reg_path = FONTS_DIR / "NotoSansBengali-Regular.ttf"
        if reg_path.exists():
            _REGULAR_FONT_BASE64 = base64.b64encode(reg_path.read_bytes()).decode("ascii")
        else:
            _REGULAR_FONT_BASE64 = ""
    if _BOLD_FONT_BASE64 is None:
        bold_path = FONTS_DIR / "NotoSansBengali-Bold.ttf"
        if bold_path.exists():
            _BOLD_FONT_BASE64 = base64.b64encode(bold_path.read_bytes()).decode("ascii")
        else:
            _BOLD_FONT_BASE64 = ""
    return _REGULAR_FONT_BASE64, _BOLD_FONT_BASE64


def _get_derived_key(key_str: str | None = None) -> bytes:
    raw = key_str or _get_draft_storage_key()
    return hashlib.sha256(raw.encode("utf-8")).digest()


def _encrypt_bytes(data: bytes, key_str: str | None = None) -> bytes:
    """AES-256-GCM authenticated encryption for draft files at rest."""
    key = _get_derived_key(key_str)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, data, None)
    return nonce + ciphertext


def _decrypt_bytes(data: bytes, key_str: str | None = None) -> bytes:
    """AES-256-GCM authenticated decryption for draft files at rest."""
    key = _get_derived_key(key_str)
    if len(data) < 28:
        raise ValueError("Invalid encrypted payload size")
    nonce = data[:12]
    ciphertext = data[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)


class DraftEngine:
    def __init__(self, db: DatabaseManager | None = None, gateway: AIGateway | None = None):
        self.db = db or db_manager
        self.gateway = gateway or AIGateway(db=self.db)

    def is_staging_allowed(self) -> bool:
        return os.environ.get("STAGING_ALLOW_DRAFT_TEMPLATES", "false").lower() in (
            "true",
            "1",
            "yes",
        )

    def get_available_templates(self, user_role: str = "citizen") -> list[dict[str, Any]]:
        """
        Returns list of templates available to the user.
        Citizens can only access 'approved' templates in prod (AC-M05-1).
        In staging with STAGING_ALLOW_DRAFT_TEMPLATES=true, citizens see unapproved templates with a warning banner.
        Admins and reviewers can see all templates.
        """
        all_templates = self.db.list_templates()
        is_staging = self.is_staging_allowed()

        res: list[dict[str, Any]] = []
        for t in all_templates:
            if user_role in ("admin", "reviewer"):
                res.append(t)
            elif t["status"] == "approved":
                res.append(t)
            elif is_staging:
                # Add staging warning banner
                t_copy = dict(t)
                t_copy["staging_warning"] = "পরীক্ষামূলক টেমপ্লেট — আইনজীবী কর্তৃক অনুমোদিত নয়"
                res.append(t_copy)

        return res

    def get_prefill_candidates(
        self, user_id: str, case_id: str | None = None
    ) -> dict[str, dict[str, Any]]:
        """
        Gathers prefill candidates for drafting questions (AC-M05-2).
        STRICT RULE: ONLY fields with status 'reviewed' or 'verified' are returned.
        Fields with status 'extracted' are NEVER offered.
        """
        candidates: dict[str, dict[str, Any]] = {}
        with self.db.get_session() as session:
            # 1. Query reviewed/verified document fields
            fields = (
                session.query(DocumentFieldDB)
                .filter(DocumentFieldDB.state.in_(["reviewed", "verified"]))
                .all()
            )

            for f in fields:
                norm_key = f.key.lower().strip()
                candidates[norm_key] = {
                    "value": f.value,
                    "source_label": f"নথি থেকে ({f.key}) — {f.state}",
                    "status": f.state,
                    "field_key": f.key,
                }

            # 2. Case parties & events if case_id provided
            if case_id:
                case_obj = self.db.get_case(case_id)
                if case_obj and case_obj.get("owner_id") == user_id:
                    parties = self.db.list_case_parties(case_id)
                    for p in parties:
                        role = p.get("role", "")
                        name = p.get("name", "")
                        if role in ("client", "landlord", "applicant", "first_party"):
                            candidates["first_party_name"] = {
                                "value": name,
                                "source_label": f"মামলার তথ্য ({role})",
                                "status": "verified",
                            }
                        elif role in ("opponent", "tenant", "second_party"):
                            candidates["second_party_name"] = {
                                "value": name,
                                "source_label": f"মামলার তথ্য ({role})",
                                "status": "verified",
                            }

        return candidates

    def start_draft(
        self,
        user_id: str,
        template_id: str,
        case_id: str | None = None,
        title: str | None = None,
    ) -> dict[str, Any]:
        """
        Initializes a draft from a template (AC-M05-1).
        Enforces 403 Forbidden in prod if template is not approved.
        Prefills reviewed/verified data with explicit origin chips.
        """
        tmpl = self.db.get_template(template_id)
        if not tmpl:
            raise ValueError(f"Template '{template_id}' not found")

        if tmpl["status"] == "retired":
            raise PermissionError(
                f"Template '{tmpl['code']}' has been retired and cannot be used for new drafts."
            )

        is_staging = self.is_staging_allowed()
        if tmpl["status"] != "approved" and not is_staging:
            raise PermissionError(
                f"Template '{tmpl['code']}' is not approved for citizen drafting (status: {tmpl['status']})"
            )

        # Collect prefill values
        prefills = self.get_prefill_candidates(user_id, case_id=case_id)
        initial_answers: dict[str, Any] = {}
        prefill_origins: dict[str, str] = {}

        for q in tmpl.get("questions_schema", []):
            qid = q["id"]
            prefill_keys = q.get("prefill_from", [])
            for pk in prefill_keys:
                if pk.lower() in prefills:
                    cand = prefills[pk.lower()]
                    initial_answers[qid] = cand["value"]
                    prefill_origins[qid] = cand["source_label"]
                    break

        if prefill_origins:
            initial_answers["_prefill_origins"] = prefill_origins

        draft = self.db.create_draft(
            user_id=user_id,
            template_id=tmpl["id"],
            case_id=case_id,
            title=title or f"{tmpl['title_bn']} (খসড়া)",
            answers=initial_answers,
        )

        audit_service.log(
            actor_id=user_id,
            actor_role="citizen",
            action="START_DRAFT",
            object_type="draft",
            object_id=draft["id"],
            meta={"template_code": tmpl["code"], "version": tmpl["version"]},
        )
        return draft

    def save_answers(
        self,
        draft_id: str,
        user_id: str,
        answers: dict[str, Any],
        selected_clause_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Saves or updates answers in a draft."""
        draft = self.db.get_draft(draft_id)
        if not draft:
            raise ValueError(f"Draft '{draft_id}' not found")
        if draft["user_id"] != user_id:
            audit_service.log(
                actor_id=user_id,
                actor_role="citizen",
                action="DRAFT_ACCESS_DENIED",
                object_type="draft",
                object_id=draft_id,
                meta={"attempted_action": "save_answers"},
            )
            raise PermissionError("Access denied to draft")

        existing_answers = draft.get("answers", {})
        existing_answers.update(answers)

        update_kwargs: dict[str, Any] = {"answers": existing_answers}
        if selected_clause_ids is not None:
            update_kwargs["selected_clause_ids"] = selected_clause_ids

        updated = self.db.update_draft(draft_id, **update_kwargs)

        audit_service.log(
            actor_id=user_id,
            actor_role="citizen",
            action="DRAFT_ANSWER",
            object_type="draft",
            object_id=draft_id,
            meta={"keys": list(answers.keys())},
        )
        return updated or draft

    def run_consistency_checks(self, draft_id: str, user_id: str) -> dict[str, Any]:
        """
        Runs validation and consistency rules before finalization (AC-M05-5).
        Validates:
        1. Required questions completed (respecting depends_on conditions).
        2. Question type number min_value and max_value bounds.
        3. Date chronological validity (start_date <= end_date, etc.).
        4. Inconsistent opposing party names (e.g. landlord == tenant).
        5. Numeral-vs-words consistency (Bangla & English).
        6. Execution checklist acknowledgment.
        """
        draft = self.db.get_draft(draft_id)
        if not draft:
            raise ValueError(f"Draft '{draft_id}' not found")
        if draft["user_id"] != user_id:
            audit_service.log(
                actor_id=user_id,
                actor_role="citizen",
                action="DRAFT_ACCESS_DENIED",
                object_type="draft",
                object_id=draft_id,
                meta={"attempted_action": "run_consistency_checks"},
            )
            raise PermissionError("Access denied to draft")

        tmpl = self.db.get_template(draft["template_id"])
        if not tmpl:
            raise ValueError("Associated template not found")

        answers = draft.get("answers", {})
        errors: list[str] = []
        warnings: list[str] = []

        # 1. Required questions check
        for q in tmpl.get("questions_schema", []):
            qid = q["id"]
            depends_on = q.get("depends_on")
            if depends_on:
                parent_id = depends_on.get("id")
                parent_expected = depends_on.get("value")
                if answers.get(parent_id) != parent_expected:
                    continue  # Skip conditional question if condition not met

            if q.get("required", False):
                val = answers.get(qid)
                if val is None or (isinstance(val, str) and not val.strip()):
                    errors.append(f"আবশ্যক প্রশ্ন পূরণ করা হয়নি: '{q.get('label_bn', qid)}'")

        # 2. Number type min_value / max_value validation
        for q in tmpl.get("questions_schema", []):
            if q.get("type") == "number":
                val = answers.get(q["id"])
                if val is not None and str(val).strip():
                    try:
                        num_val = float(str(val).replace(",", "").strip())
                        min_v = q.get("min_value")
                        max_v = q.get("max_value")
                        if min_v is not None and num_val < min_v:
                            errors.append(
                                f"'{q.get('label_bn', q['id'])}' এর মান সর্বনিম্ন {to_bangla_digits(str(min_v))} হতে হবে।"
                            )
                        if max_v is not None and num_val > max_v:
                            errors.append(
                                f"'{q.get('label_bn', q['id'])}' এর মান সর্বোচ্চ {to_bangla_digits(str(max_v))} হতে পারে।"
                            )
                    except ValueError:
                        errors.append(f"'{q.get('label_bn', q['id'])}' একটি বৈধ সংখ্যা হতে হবে।")

        # 3. Date chronological consistency
        start_date_str = answers.get("start_date")
        end_date_str = answers.get("end_date")
        if start_date_str and end_date_str:
            try:
                s_date = datetime.fromisoformat(str(start_date_str).replace("/", "-"))
                e_date = datetime.fromisoformat(str(end_date_str).replace("/", "-"))
                if s_date > e_date:
                    errors.append("চুক্তি শুরুর তারিখ অবশ্যই সমাপ্তির তারিখের পূর্বে হতে হবে।")
            except Exception:
                warnings.append("তারিখের বিন্যাস মানসম্মত নয়।")

        rent_due_day = answers.get("rent_due_day")
        if rent_due_day is not None and "rent_due_day" in answers:
            try:
                day_num = int(rent_due_day)
                if day_num < 1 or day_num > 31:
                    errors.append("ভাড়া প্রদেয় দিন ১ থেকে ৩১ এর মধ্যে হতে হবে।")
            except Exception:
                errors.append("ভাড়া প্রদেয় দিন একটি বৈধ সংখ্যা হতে হবে।")

        # 4. Inconsistent opposing party names check (AC-M05-5)
        opposing_pairs = [
            (("landlord_name", "বাড়িওয়ালা"), ("tenant_name", "ভাড়াটিয়া")),
            (("client_name", "সেবা গ্রহণকারী"), ("provider_name", "সেবা প্রদানকারী")),
            (("sender_name", "জবাব প্রদানকারী"), ("notice_lawyer_name", "নোটিশ প্রেরণকারী আইনজীবী")),
        ]
        for (k1, l1), (k2, l2) in opposing_pairs:
            n1 = answers.get(k1)
            n2 = answers.get(k2)
            if n1 and n2 and str(n1).strip().lower() == str(n2).strip().lower():
                errors.append(
                    f"পক্ষসমূহের নাম অসামঞ্জস্যপূর্ণ: '{l1}' এবং '{l2}' উভয় ক্ষেত্রে একই ব্যক্তি ('{n1}') হতে পারে না।"
                )

        # 5. Numerals vs Words consistency check (AC-M05-5)
        numeral_pairs = [
            ("monthly_rent", "monthly_rent_words"),
            ("security_deposit", "security_deposit_words"),
            ("contract_amount", "contract_amount_words"),
        ]
        for num_k, words_k in numeral_pairs:
            num_val = answers.get(num_k)
            words_val = answers.get(words_k)
            if num_val is not None and words_val:
                is_match, mismatch_msg = verify_numeral_word_consistency(num_val, str(words_val))
                if not is_match:
                    errors.append(mismatch_msg)

        # 6. Checklist items status
        checklist_states = draft.get("checklist_states", {})
        for chk in tmpl.get("checklist_schema", []):
            cid = chk["id"]
            if chk.get("is_required", True) and not checklist_states.get(cid, False):
                warnings.append(f"সম্পাদন চেকলিস্ট আইটেম এখনো নিশ্চিত করা হয়নি: '{chk.get('title_bn')}'")

        # Save validation results
        self.db.update_draft(draft_id, validation_errors=errors)

        audit_service.log(
            actor_id=user_id,
            actor_role="citizen",
            action="DRAFT_CHECK",
            object_type="draft",
            object_id=draft_id,
            meta={"is_valid": len(errors) == 0, "error_count": len(errors)},
        )

        return {
            "draft_id": draft_id,
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    def toggle_checklist_item(
        self,
        draft_id: str,
        user_id: str,
        item_id: str,
        confirmed: bool,
    ) -> dict[str, Any]:
        """Toggles or confirms an execution checklist item (AC-M05-3)."""
        draft = self.db.get_draft(draft_id)
        if not draft:
            raise ValueError(f"Draft '{draft_id}' not found")
        if draft["user_id"] != user_id:
            audit_service.log(
                actor_id=user_id,
                actor_role="citizen",
                action="DRAFT_ACCESS_DENIED",
                object_type="draft",
                object_id=draft_id,
                meta={"attempted_action": "toggle_checklist"},
            )
            raise PermissionError("Access denied to draft")

        states = draft.get("checklist_states", {})
        states[item_id] = confirmed
        updated = self.db.update_draft(draft_id, checklist_states=states)

        audit_service.log(
            actor_id=user_id,
            actor_role="citizen",
            action="DRAFT_CHECKLIST",
            object_type="draft",
            object_id=draft_id,
            meta={"item_id": item_id, "confirmed": confirmed},
        )
        return updated or draft

    def render_document_preview(self, draft_id: str, user_id: str) -> dict[str, Any]:
        """
        Renders live preview with populated clauses and watermark (AC-M05-3).
        Watermark 'খসড়া — AI-সহায়তায় তৈরি, আইনি পরামর্শ নয়' is present on EVERY view until finalized.
        """
        draft = self.db.get_draft(draft_id)
        if not draft:
            raise ValueError(f"Draft '{draft_id}' not found")
        if draft["user_id"] != user_id:
            audit_service.log(
                actor_id=user_id,
                actor_role="citizen",
                action="DRAFT_ACCESS_DENIED",
                object_type="draft",
                object_id=draft_id,
                meta={"attempted_action": "render_preview"},
            )
            raise PermissionError("Access denied to draft")

        tmpl = self.db.get_template(draft["template_id"])
        if not tmpl:
            raise ValueError("Template not found")

        answers = draft.get("answers", {})
        selected_clause_ids = set(draft.get("selected_clause_ids", []))

        # Format answers for display (convert digits if numeric)
        display_answers: dict[str, str] = {}
        for k, v in answers.items():
            if isinstance(v, (int, float)):
                display_answers[k] = to_bangla_digits(f"{v:,}")
            elif isinstance(v, str):
                display_answers[k] = v
            else:
                display_answers[k] = str(v)

        rendered_clauses: list[dict[str, Any]] = []
        full_text_parts: list[str] = [f"দলিলের নাম: {tmpl['title_bn']}\n"]

        for clause in tmpl.get("clauses", []):
            cid = clause["id"]
            if clause.get("is_optional", False) and cid not in selected_clause_ids:
                continue

            template_text = clause.get("text_template_bn", "")

            # Replace placeholder variables {var}
            def _replace_var(match: re.Match) -> str:
                var_name = match.group(1)
                if var_name in display_answers and display_answers[var_name].strip():
                    return display_answers[var_name]
                return "[____]"

            rendered_clause_text = re.sub(r"\{([a-zA-Z0-9_]+)\}", _replace_var, template_text)
            rendered_clauses.append(
                {
                    "id": cid,
                    "title_bn": clause.get("title_bn"),
                    "text": rendered_clause_text,
                    "is_optional": clause.get("is_optional", False),
                }
            )
            full_text_parts.append(f"{clause.get('title_bn')}\n{rendered_clause_text}\n")

        # Watermark & Footer logic
        is_finalized = bool(draft.get("is_finalized", False))
        watermark = (
            None
            if is_finalized
            else draft.get("watermark_text", "খসড়া — AI-সহায়তায় তৈরি, আইনি পরামর্শ নয়")
        )

        footer = {
            "template_name": tmpl["title_bn"],
            "template_code": tmpl["code"],
            "version": f"v{tmpl['version']}",
            "effective_date": tmpl.get("effective_from") or "২০২৬-১০-০১",
            "generation_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "system_attribution": "AIN-AI দ্বারা প্রস্তুতকৃত",
        }

        audit_service.log(
            actor_id=user_id,
            actor_role="citizen",
            action="DRAFT_PREVIEW",
            object_type="draft",
            object_id=draft_id,
        )

        return {
            "draft_id": draft_id,
            "title": draft["title"],
            "template_code": tmpl["code"],
            "clauses": rendered_clauses,
            "full_text": "\n".join(full_text_parts),
            "watermark": watermark,
            "footer": footer,
            "is_finalized": is_finalized,
            "checklist_states": draft.get("checklist_states", {}),
            "checklist_schema": tmpl.get("checklist_schema", []),
        }

    def finalize_draft(self, draft_id: str, user_id: str) -> dict[str, Any]:
        """
        Finalizes draft (AC-M05-3).
        REJECTS finalization unless:
        1. All required questions are answered.
        2. Consistency checks pass with 0 errors.
        3. EVERY execution checklist item is confirmed.
        """
        draft = self.db.get_draft(draft_id)
        if not draft:
            raise ValueError(f"Draft '{draft_id}' not found")
        if draft["user_id"] != user_id:
            audit_service.log(
                actor_id=user_id,
                actor_role="citizen",
                action="DRAFT_ACCESS_DENIED",
                object_type="draft",
                object_id=draft_id,
                meta={"attempted_action": "finalize"},
            )
            raise PermissionError("Access denied to draft")

        tmpl = self.db.get_template(draft["template_id"])
        if not tmpl:
            raise ValueError("Template not found")

        # 1. Run consistency check
        check_res = self.run_consistency_checks(draft_id, user_id)
        if not check_res["is_valid"]:
            raise ValueError(
                f"Cannot finalize draft with consistency errors: {', '.join(check_res['errors'])}"
            )

        # 2. Check every execution checklist item is confirmed (AC-M05-3)
        states = draft.get("checklist_states", {})
        checklist_schema = tmpl.get("checklist_schema", [])
        unconfirmed = []
        for chk in checklist_schema:
            cid = chk["id"]
            if not states.get(cid, False):
                unconfirmed.append(chk.get("title_bn", cid))

        if unconfirmed:
            raise ValueError(
                f"চূড়ান্ত করার পূর্বে সকল সম্পাদন চেকলিস্ট আইটেম নিশ্চিত করা আবশ্যক। অপরিপূর্ণ: {', '.join(unconfirmed)}"
            )

        now = datetime.now(timezone.utc).isoformat()
        clean_title = draft.get("title", "").replace(" (খসড়া)", "").replace(" (খসড়া)", "").strip()
        updated = self.db.update_draft(
            draft_id,
            title=clean_title or draft.get("title", ""),
            is_finalized=True,
            status="finalized",
            finalized_at=now,
            watermark_text="",  # Watermark removed ONLY upon finalization
        )

        audit_service.log(
            actor_id=user_id,
            actor_role="citizen",
            action="FINALIZE_DRAFT",
            object_type="draft",
            object_id=draft_id,
            meta={"template_code": tmpl["code"]},
        )
        audit_service.log(
            actor_id=user_id,
            actor_role="citizen",
            action="DRAFT_FINALIZE",
            object_type="draft",
            object_id=draft_id,
            meta={"template_code": tmpl["code"]},
        )

        return updated or draft

    def get_signing_checklist(self, draft_id: str, user_id: str) -> dict[str, Any]:
        """Returns actionable document-specific next steps (AC-M05-6)."""
        preview = self.render_document_preview(draft_id, user_id)
        tmpl_code = preview["template_code"]

        steps = []
        if tmpl_code == "DT-01":
            steps = [
                {
                    "step_id": "s1",
                    "title_bn": "নন-জুডিশিয়াল স্ট্যাম্পে প্রিন্ট",
                    "description_bn": "৩০০ টাকার স্ট্যাম্পে প্রিন্ট করুন (The Stamp Act, 1899 অনুযায়ী)।",
                },
                {
                    "step_id": "s2",
                    "title_bn": "স্বাক্ষর ও আদ্যক্ষর",
                    "description_bn": "চুক্তির প্রতিটি পৃষ্ঠায় প্রথম ও দ্বিতীয় পক্ষের আদ্যক্ষর এবং শেষ পৃষ্ঠায় পূর্ণ স্বাক্ষর।",
                },
                {
                    "step_id": "s3",
                    "title_bn": "২ জন নিরপেক্ষ সাক্ষীর স্বাক্ষর",
                    "description_bn": "উভয় পক্ষের উপস্থিতিতে ২ জন প্রাপ্তবয়স্ক সাক্ষীর নাম, ঠিকানা ও স্বাক্ষর।",
                },
                {
                    "step_id": "s4",
                    "title_bn": "রেজিস্ট্রেশন পরীক্ষা",
                    "description_bn": "চুক্তির মেয়াদ ১ বছরের বেশি হলে সাব-রেজিস্ট্রি অফিসে বাধ্যতামূলক নিবন্ধন (The Registration Act, 1908)।",
                },
            ]
        elif tmpl_code == "DT-02":
            steps = [
                {
                    "step_id": "s1",
                    "title_bn": "২০০ টাকার স্ট্যাম্পে মুদ্রণ",
                    "description_bn": "হলফনামাটি ২০০ টাকার নন-জুডিশিয়াল স্ট্যাম্পে টাইপ/প্রিন্ট করুন।",
                },
                {
                    "step_id": "s2",
                    "title_bn": "নোটারি বা ওথ কমিশনারের সম্মুখে শপথ",
                    "description_bn": "সশরীরে উপস্থিত হয়ে বিজ্ঞ নোটারি পাবলিকের সম্মুখে শপথ গ্রহণ ও সিল-স্বাক্ষর গ্রহণ।",
                },
                {
                    "step_id": "s3",
                    "title_bn": "আইনজীবীর মাধ্যমে শনাক্তকরণ",
                    "description_bn": "শনাক্তকারী আইনজীবীর পূর্ণ স্বাক্ষর ও সনদ নম্বর নিশ্চিতকরণ।",
                },
            ]
        elif tmpl_code == "DT-03":
            steps = [
                {
                    "step_id": "s1",
                    "title_bn": "আইনজীবীর অনুমোদন ও স্বাক্ষর",
                    "description_bn": "আইনি নোটিশের জবাব বিজ্ঞ আইনজীবীর স্বাক্ষরযুক্ত বা নির্দেশিত ফরম্যাটে তৈরি।",
                },
                {
                    "step_id": "s2",
                    "title_bn": "রেজিস্ট্রি ডাকযোগে এডি সহ প্রেরণ",
                    "description_bn": "পোস্ট অফিসের মাধ্যমে এডি সহ রেজিস্ট্রি ডাকে প্রেরণ এবং ডাক রসিদ সংরক্ষণ।",
                },
            ]
        elif tmpl_code == "DT-04":
            steps = [
                {
                    "step_id": "s1",
                    "title_bn": "২ কপি প্রিন্ট ও স্বাক্ষর",
                    "description_bn": "আবেদনপত্রের ২ কপি প্রিন্ট করে আবেদনকারী নিজে স্বাক্ষর করবেন।",
                },
                {
                    "step_id": "s2",
                    "title_bn": "থানায় ডিউটি অফিসারের নিকট পেশ",
                    "description_bn": "সংশ্লিষ্ট থানার ডিউটি অফিসারের নিকট পেশ করে ১ কপি সিল ও জিডি নম্বরসহ রিসিভিং সংগ্রহ।",
                },
            ]
        else:
            steps = [
                {
                    "step_id": "s1",
                    "title_bn": "উপযুক্ত স্ট্যাম্পে স্বাক্ষর",
                    "description_bn": "চুক্তিমূল্য অনুযায়ী স্ট্যাম্পে উভয় পক্ষের স্বাক্ষর।",
                },
                {
                    "step_id": "s2",
                    "title_bn": "২ জন সাক্ষীর স্বাক্ষর",
                    "description_bn": "সাক্ষীদের নাম ও ঠিকানা সহ স্বাক্ষর গ্রহণ।",
                },
            ]

        return {
            "draft_id": draft_id,
            "template_code": tmpl_code,
            "is_finalized": preview["is_finalized"],
            "actionable_steps": steps,
        }

    def export_draft(
        self,
        draft_id: str,
        user_id: str,
        export_format: str = "pdf",
    ) -> dict[str, Any]:
        """
        Exports draft to PDF or DOCX (AC-M05-4).
        PDF export uses Playwright Chromium with bundled Noto Sans Bengali font (embedded via base64 data URI)
        to guarantee 100% correct shaping of complex Bengali conjuncts (ক্ষ, জ্ঞ, ন্দ, স্ত্র, ক্ত, ঙ্গ, শ্র).
        Draft files are stored encrypted at rest with AES-256-GCM.
        """
        fmt = export_format.lower()
        if fmt not in ("pdf", "docx"):
            raise ValueError(
                f"Unsupported export format '{export_format}'. Supported formats: pdf, docx."
            )

        draft = self.db.get_draft(draft_id)
        if not draft:
            raise ValueError(f"Draft '{draft_id}' not found")
        if draft["user_id"] != user_id:
            audit_service.log(
                actor_id=user_id,
                actor_role="citizen",
                action="DRAFT_ACCESS_DENIED",
                object_type="draft",
                object_id=draft_id,
                meta={"attempted_action": "export"},
            )
            raise PermissionError("Access denied to draft")

        preview = self.render_document_preview(draft_id, user_id)
        storage_dir = Path(os.environ.get("STORAGE_DIR", str(REPO_ROOT / "storage" / "drafts")))
        storage_dir.mkdir(parents=True, exist_ok=True)

        is_finalized = preview["is_finalized"]
        watermark = preview["watermark"]
        footer = preview["footer"]

        file_id = f"draft_{draft_id}_{uuid.uuid4().hex[:6]}"

        if fmt == "docx":
            out_file = storage_dir / f"{file_id}.docx"
            doc = Document()

            # Set title
            p_title = doc.add_paragraph()
            run_title = p_title.add_run(preview["title"])
            run_title.font.size = Pt(18)
            run_title.font.bold = True
            run_title.font.name = "Noto Sans Bengali"

            if watermark:
                p_wm = doc.add_paragraph()
                r_wm = p_wm.add_run(f"[{watermark}]")
                r_wm.font.size = Pt(12)
                r_wm.font.color.rgb = RGBColor(220, 38, 38)
                r_wm.font.bold = True

            doc.add_paragraph()

            # Add clauses
            for cl in preview["clauses"]:
                p_c = doc.add_paragraph()
                r_ct = p_c.add_run(cl["title_bn"] + "\n")
                r_ct.font.bold = True
                r_ct.font.size = Pt(13)
                r_ct.font.name = "Noto Sans Bengali"

                r_body = p_c.add_run(cl["text"] + "\n")
                r_body.font.size = Pt(11)
                r_body.font.name = "Noto Sans Bengali"

            # Footer
            doc.add_paragraph()
            p_foot = doc.add_paragraph()
            r_foot = p_foot.add_run(
                f"{footer['template_name']} ({footer['version']}) | "
                f"কার্যকর: {footer['effective_date']} | প্রস্তুত: {footer['generation_date']} | "
                f"{footer['system_attribution']}"
            )
            r_foot.font.size = Pt(9)
            r_foot.font.color.rgb = RGBColor(100, 116, 139)

            doc.save(str(out_file))
            raw_bytes = out_file.read_bytes()
            out_file.unlink(missing_ok=True)
        else:
            # PDF via Playwright Chromium with Noto Sans Bengali font
            out_file = storage_dir / f"{file_id}.pdf"
            html_content = self._build_pdf_html(preview)

            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_content(html_content, wait_until="networkidle")
                page.pdf(
                    path=str(out_file),
                    format="A4",
                    print_background=True,
                    margin={"top": "20mm", "bottom": "25mm", "left": "20mm", "right": "20mm"},
                )
                browser.close()

            raw_bytes = out_file.read_bytes()
            out_file.unlink(missing_ok=True)

        # Compute file hash
        file_hash = hashlib.sha256(raw_bytes).hexdigest()

        # Encrypt at rest with AES-256-GCM
        enc_file = storage_dir / f"{file_id}.enc"
        encrypted_data = _encrypt_bytes(raw_bytes, DRAFT_STORAGE_KEY)
        enc_file.write_bytes(encrypted_data)

        # Record export
        export_rec = self.db.create_draft_export(
            draft_id=draft_id,
            user_id=user_id,
            format=fmt,
            storage_key=str(enc_file),
            file_hash=file_hash,
            watermark_applied=bool(watermark),
        )

        audit_service.log(
            actor_id=user_id,
            actor_role="citizen",
            action="DRAFT_EXPORT",
            object_type="draft",
            object_id=draft_id,
            meta={"format": fmt, "export_id": export_rec["id"]},
        )

        return {
            "export_id": export_rec["id"],
            "format": fmt,
            "file_path": str(enc_file),
            "encrypted_path": str(enc_file),
            "file_hash": file_hash,
            "watermark_applied": bool(watermark),
            "is_finalized": is_finalized,
            "file_size": len(raw_bytes),
        }

    def get_decrypted_export_bytes(
        self,
        export_id: str,
        user_id: str,
    ) -> tuple[bytes, str, str]:
        """
        Retrieves and decrypts draft export file for download (F4: do not password-protect citizen downloads).
        Returns (decrypted_bytes, filename, media_type).
        """
        export_rec = self.db.get_draft_export(export_id)
        if not export_rec:
            raise ValueError(f"Draft export '{export_id}' not found")

        draft = self.db.get_draft(export_rec["draft_id"])
        if not draft or draft["user_id"] != user_id:
            audit_service.log(
                actor_id=user_id,
                actor_role="citizen",
                action="DRAFT_ACCESS_DENIED",
                object_type="draft_export",
                object_id=export_id,
                meta={"attempted_action": "download"},
            )
            raise PermissionError("Access denied to export file")

        enc_path = Path(export_rec["storage_key"])
        if not enc_path.exists():
            raise FileNotFoundError(f"Export file not found at {enc_path}")

        enc_bytes = enc_path.read_bytes()
        decrypted_bytes = _decrypt_bytes(enc_bytes, DRAFT_STORAGE_KEY)

        fmt = export_rec["format"].lower()
        if fmt == "pdf":
            media_type = "application/pdf"
            filename = f"draft_{export_rec['draft_id']}.pdf"
        elif fmt == "docx":
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            filename = f"draft_{export_rec['draft_id']}.docx"
        else:
            media_type = "application/octet-stream"
            filename = f"draft_{export_rec['draft_id']}.{fmt}"

        return decrypted_bytes, filename, media_type

    def delete_draft(self, draft_id: str, user_id: str) -> bool:
        """Deletes a draft with ownership verification and audit logging."""
        draft = self.db.get_draft(draft_id)
        if not draft:
            raise ValueError(f"Draft '{draft_id}' not found")
        if draft["user_id"] != user_id:
            audit_service.log(
                actor_id=user_id,
                actor_role="citizen",
                action="DRAFT_ACCESS_DENIED",
                object_type="draft",
                object_id=draft_id,
                meta={"attempted_action": "delete"},
            )
            raise PermissionError("Access denied to draft")

        success = self.db.delete_draft(draft_id, user_id)
        if success:
            audit_service.log(
                actor_id=user_id,
                actor_role="citizen",
                action="DRAFT_DELETE",
                object_type="draft",
                object_id=draft_id,
            )
        return success

    def _build_pdf_html(self, preview: dict[str, Any]) -> str:
        """Constructs HTML styled with bundled Noto Sans Bengali font (data URI) and watermark."""
        reg_b64, bold_b64 = _get_font_base64()

        watermark_html = ""
        if preview.get("watermark"):
            watermark_html = f"""
            <div class="watermark">{preview["watermark"]}</div>
            """

        clauses_html = ""
        for cl in preview["clauses"]:
            clauses_html += f"""
            <div class="clause-box">
                <div class="clause-title">{cl["title_bn"]}</div>
                <div class="clause-text">{cl["text"]}</div>
            </div>
            """

        footer = preview["footer"]
        footer_html = f"""
        <div class="doc-footer">
            <span>{footer["template_name"]} ({footer["version"]})</span>
            <span>কার্যকর: {footer["effective_date"]} | প্রস্তুত: {footer["generation_date"]}</span>
            <span>{footer["system_attribution"]}</span>
        </div>
        """

        subtitle = (
            "আইন-AI প্রস্তুতকৃত চূড়ান্ত দলিল (মডিউল M05)"
            if preview.get("is_finalized")
            else "আইন-AI নিয়ন্ত্রিত খসড়া দলিল (মডিউল M05)"
        )

        return f"""<!DOCTYPE html>
<html lang="bn">
<head>
<meta charset="utf-8">
<style>
  @font-face {{
    font-family: 'Noto Sans Bengali';
    src: url('data:font/truetype;charset=utf-8;base64,{reg_b64}') format('truetype');
    font-weight: normal;
    font-style: normal;
  }}
  @font-face {{
    font-family: 'Noto Sans Bengali';
    src: url('data:font/truetype;charset=utf-8;base64,{bold_b64}') format('truetype');
    font-weight: bold;
    font-style: normal;
  }}
  @page {{
    size: A4;
    margin: 20mm;
  }}
  body {{
    font-family: 'Noto Sans Bengali', sans-serif;
    color: #1e293b;
    line-height: 1.6;
    margin: 0;
    padding: 0;
    position: relative;
  }}
  .watermark {{
    position: fixed;
    top: 40%;
    left: 5%;
    right: 5%;
    text-align: center;
    font-size: 26px;
    font-weight: bold;
    color: rgba(220, 38, 38, 0.22);
    transform: rotate(-30deg);
    pointer-events: none;
    z-index: 9999;
    border: 3px dashed rgba(220, 38, 38, 0.25);
    padding: 18px 24px;
    border-radius: 12px;
  }}
  .header {{
    text-align: center;
    border-bottom: 2px solid #0f766e;
    padding-bottom: 12px;
    margin-bottom: 20px;
  }}
  .header h1 {{
    font-size: 22px;
    color: #0f766e;
    margin: 0 0 6px 0;
  }}
  .header p {{
    margin: 0;
    font-size: 13px;
    color: #64748b;
  }}
  .clause-box {{
    margin-bottom: 16px;
    page-break-inside: avoid;
  }}
  .clause-title {{
    font-size: 15px;
    font-weight: bold;
    color: #0f172a;
    margin-bottom: 4px;
  }}
  .clause-text {{
    font-size: 13px;
    color: #334155;
    text-align: justify;
    line-height: 1.7;
  }}
  .doc-footer {{
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    border-top: 1px solid #cbd5e1;
    padding-top: 8px;
    display: flex;
    justify-content: space-between;
    font-size: 10px;
    color: #64748b;
  }}
</style>
</head>
<body>
  {watermark_html}
  <div class="header">
    <h1>{preview["title"]}</h1>
    <p>{subtitle}</p>
  </div>
  <div class="content">
    {clauses_html}
  </div>
  {footer_html}
</body>
</html>
"""

    def _filter_outcome_predictions(self, text: str) -> str:
        prohibited_patterns = [
            r"(?:নিশ্চিত|অবশ্যই)\s*(?:জিতবেন|হারবেন|জয়ী\s*হবেন)",
            r"(?:মামলায়|আদালতে)\s*(?:জয়লাভ|পরাজয়)\s*(?:নিশ্চিত)",
            r"(?:you\s*will\s*(?:win|lose))",
            r"(?:guaranteed\s*outcome)",
            r"(?:চুক্তিতে\s*আপনার\s*জয়\s*হবে)",
        ]
        for pattern in prohibited_patterns:
            text = re.sub(pattern, "[ফলাফল পূর্বাভাস আইন-AI নীতিমালায় নিষিদ্ধ]", text, flags=re.IGNORECASE)
        return text

    def get_ai_help(
        self,
        draft_id: str,
        user_id: str,
        question_id: str,
        user_query: str = "",
    ) -> dict[str, Any]:
        """
        Executes draft.helper.v1 AI task.
        Structurally constrained: rephrased question, approved clause IDs, and term explanations only.
        Hostile provider attempts (free clause text, outcome predictions, made-up clause IDs) are blocked.
        """
        draft = self.db.get_draft(draft_id)
        if not draft:
            raise ValueError(f"Draft '{draft_id}' not found")
        if draft["user_id"] != user_id:
            audit_service.log(
                actor_id=user_id,
                actor_role="citizen",
                action="DRAFT_ACCESS_DENIED",
                object_type="draft",
                object_id=draft_id,
                meta={"attempted_action": "ai_help"},
            )
            raise PermissionError("Access denied")

        tmpl = self.db.get_template(draft["template_id"])
        if not tmpl:
            raise ValueError("Template not found")

        # Find target question
        target_q = None
        for q in tmpl.get("questions_schema", []):
            if q["id"] == question_id:
                target_q = q
                break

        q_text = target_q.get("label_bn", question_id) if target_q else question_id
        approved_optional_ids = [
            c["id"] for c in tmpl.get("clauses", []) if c.get("is_optional", False)
        ]

        variables = {
            "template_code": tmpl["code"],
            "question_id": question_id,
            "question_text": q_text,
            "approved_clause_ids": json.dumps(approved_optional_ids),
            "user_query": user_query or q_text,
        }

        output = self.gateway.execute_prompt("draft.helper.v1", variables, user_id=user_id)
        raw_data = output.get("data", {})

        sanitized: dict[str, Any] = {}

        # 1. Filter suggested_clause_ids strictly against approved_optional_ids
        raw_clauses = raw_data.get("suggested_clause_ids", [])
        if isinstance(raw_clauses, list):
            sanitized["suggested_clause_ids"] = [
                cid for cid in raw_clauses if cid in approved_optional_ids
            ]
        else:
            sanitized["suggested_clause_ids"] = []

        # 2. Rephrased question check
        rephrased = raw_data.get("rephrased_question", "")
        if isinstance(rephrased, str):
            sanitized["rephrased_question"] = self._filter_outcome_predictions(rephrased)

        # 3. Term explanation check
        term_exp = raw_data.get("term_explanation")
        if isinstance(term_exp, dict):
            exp_bn = term_exp.get("explanation_bn", "")
            if isinstance(exp_bn, str):
                exp_bn = self._filter_outcome_predictions(exp_bn)
            sanitized["term_explanation"] = {
                "term": term_exp.get("term", ""),
                "explanation_bn": exp_bn,
                "source_chip": term_exp.get("source_chip", "আইনি পরিভাষা কোষ"),
            }

        return sanitized


# Singleton engine instance
draft_engine = DraftEngine()
