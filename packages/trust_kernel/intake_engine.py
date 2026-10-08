"""
Intake & Triage Engine (SRS M11 / Sprint S7).
Implements:
1. Multi-select triage chips and instant UrgentBanner trigger.
2. Lawyer-reviewed keyword classification & stated deadline checks.
3. Strict rule: Classifier can ONLY RAISE urgency, never lower user-selected urgency.
4. One-question-per-screen autosave, abandonment, and resumption.
5. AI profiling (intake.profile.v1) with output schema enforcement and outcome sanitization.
6. Case creation from confirmed profile: only confirmed facts/events carry over into case.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from packages.trust_kernel.ai_gateway import AIGateway, ai_gateway
from packages.trust_kernel.audit import InMemoryAuditService, audit_service
from packages.trust_kernel.case_engine import CaseEngine
from packages.trust_kernel.db import DatabaseManager, db_manager
from packages.trust_kernel.outcome_filter import sanitize_ai_profile
from packages.trust_kernel.triage_config import (
    TRIAGE_CHIPS_CONFIG,
    TRIAGE_KEYWORD_PATTERNS,
)

logger = logging.getLogger(__name__)

URGENT_CHIP_IDS = {c["id"] for c in TRIAGE_CHIPS_CONFIG if c["is_urgent"]}


class IntakeEngine:
    def __init__(
        self,
        db: DatabaseManager | None = None,
        gateway: AIGateway | None = None,
        audit: InMemoryAuditService | None = None,
        case_engine: CaseEngine | None = None,
    ):
        self.db = db or db_manager
        self.gateway = gateway or ai_gateway
        self.audit = audit or audit_service
        self.case_engine = case_engine or CaseEngine(
            db=self.db, gateway=self.gateway, audit=self.audit
        )

    # ---------------------------------------------------------------------------
    # 1. Session Lifecycle (Create, Save Answer, Abandon, Resume)
    # ---------------------------------------------------------------------------

    def create_session(
        self,
        user_id: str,
        triage_chips: list[str] | None = None,
    ) -> dict[str, Any]:
        """Creates a new intake session. If an urgent chip is selected, marks urgent immediately."""
        chips = triage_chips or []
        is_urgent = any(c in URGENT_CHIP_IDS for c in chips)
        urgency = "urgent" if is_urgent else "normal"
        urgency_reason = "urgent_triage_chip_selected" if is_urgent else None

        session = self.db.create_intake_session(
            user_id=user_id,
            triage_chips=chips,
            urgency=urgency,
            urgency_reason=urgency_reason,
        )

        self.audit.log(
            actor_id=user_id,
            actor_role="citizen",
            action="create_intake_session",
            object_type="intake_session",
            object_id=session["id"],
            meta={"urgency": urgency, "triage_chips": chips},
        )
        return session

    def get_session(self, session_id: str, user_id: str | None = None) -> dict[str, Any] | None:
        """Retrieves an intake session with tenant isolation check."""
        session = self.db.get_intake_session(session_id)
        if not session:
            return None
        if user_id and session["user_id"] != user_id:
            raise PermissionError("Access denied: You do not own this intake session.")
        return session

    def save_answer(
        self,
        session_id: str,
        user_id: str,
        question_key: str,
        answer_value: Any,
        step: int | None = None,
    ) -> dict[str, Any]:
        """
        Saves or updates an answer to a question in the intake flow.
        Evaluates triage rules dynamically and updates current step.
        """
        session = self.get_session(session_id, user_id=user_id)
        if not session:
            raise ValueError(f"Intake session '{session_id}' not found.")

        answers = dict(session.get("answers", {}))
        answers[question_key] = answer_value

        updates: dict[str, Any] = {"answers": answers}
        if step is not None:
            updates["current_step"] = step

        # Update session answers first
        updated = self.db.update_intake_session(session_id, **updates)
        if not updated:
            raise RuntimeError("Failed to update intake session.")

        # Re-evaluate triage: classifier may raise urgency, never lower it
        self.evaluate_triage(session_id, user_id)

        self.audit.log(
            actor_id=user_id,
            actor_role="citizen",
            action="save_intake_answer",
            object_type="intake_session",
            object_id=session_id,
            meta={"question_key": question_key, "step": step},
        )
        return self.get_session(session_id, user_id=user_id) or updated

    def abandon_session(self, session_id: str, user_id: str) -> dict[str, Any]:
        """Marks intake session as abandoned while preserving all answers intact."""
        session = self.get_session(session_id, user_id=user_id)
        if not session:
            raise ValueError(f"Intake session '{session_id}' not found.")

        updated = self.db.update_intake_session(session_id, status="abandoned")
        self.audit.log(
            actor_id=user_id,
            actor_role="citizen",
            action="abandon_intake_session",
            object_type="intake_session",
            object_id=session_id,
        )
        return updated or session

    def resume_session(self, session_id: str, user_id: str) -> dict[str, Any]:
        """Resumes an abandoned or in-progress intake session with all preserved data."""
        session = self.get_session(session_id, user_id=user_id)
        if not session:
            raise ValueError(f"Intake session '{session_id}' not found.")

        updated = self.db.update_intake_session(session_id, status="in_progress")
        self.audit.log(
            actor_id=user_id,
            actor_role="citizen",
            action="resume_intake_session",
            object_type="intake_session",
            object_id=session_id,
            meta={"resumed_step": session["current_step"]},
        )
        return updated or session

    # ---------------------------------------------------------------------------
    # 2. Triage Logic (Chips, Keywords, Deadlines, Classifier Only Raises)
    # ---------------------------------------------------------------------------

    def evaluate_triage(self, session_id: str, user_id: str) -> dict[str, Any]:
        """
        Evaluates session data against:
        1. Selected triage chips
        2. Lawyer-reviewed keyword patterns in user answers
        3. Stated deadline <= 3 days

        Rule: The classifier may ONLY RAISE urgency from 'normal' to 'urgent', NEVER lower it.
        """
        session = self.get_session(session_id, user_id=user_id)
        if not session:
            raise ValueError(f"Intake session '{session_id}' not found.")

        current_urgency = session.get("urgency", "normal")
        reasons: list[str] = []

        # 1. Triage chip check
        chips = session.get("triage_chips", [])
        urgent_chips_selected = [c for c in chips if c in URGENT_CHIP_IDS]
        if urgent_chips_selected:
            reasons.append(f"urgent_chips:{','.join(urgent_chips_selected)}")

        # 2. Text keyword check across all text answers
        answers = session.get("answers", {})
        combined_text = " ".join(str(v) for v in answers.values() if isinstance(v, (str, list)))

        matched_categories = set()
        for pattern, category in TRIAGE_KEYWORD_PATTERNS:
            if pattern.search(combined_text):
                matched_categories.add(category)

        if matched_categories:
            reasons.append(f"keywords_detected:{','.join(sorted(matched_categories))}")

        # 3. Deadline check (<= 3 days)
        deadline_val = (
            answers.get("deadline_date") or answers.get("deadline") or answers.get("hearing_date")
        )
        stated_days = answers.get("stated_deadline_days")
        is_imminent_deadline = False

        if stated_days is not None:
            try:
                if int(stated_days) <= 3:
                    is_imminent_deadline = True
                    reasons.append(f"stated_deadline_days:{stated_days}")
            except (ValueError, TypeError):
                pass

        if deadline_val and not is_imminent_deadline:
            # Check if parsed date <= 3 days from now
            try:
                due = datetime.fromisoformat(str(deadline_val).replace("Z", "+00:00")).date()
                today = datetime.now(timezone.utc).date()
                diff = (due - today).days
                if 0 <= diff <= 3:
                    is_imminent_deadline = True
                    reasons.append(f"deadline_within_{diff}_days")
            except Exception:
                pass

        # Determine target urgency
        should_be_urgent = bool(urgent_chips_selected or matched_categories or is_imminent_deadline)

        # STRICT MONOTONIC RULE: Classifier may only RAISE urgency, NEVER lower it
        final_urgency = current_urgency
        raised = False

        if should_be_urgent and current_urgency != "urgent":
            final_urgency = "urgent"
            raised = True
            reason_str = " | ".join(reasons)
            self.db.update_intake_session(session_id, urgency="urgent", urgency_reason=reason_str)

        return {
            "session_id": session_id,
            "urgency": final_urgency,
            "reasons": reasons,
            "raised": raised,
        }

    # ---------------------------------------------------------------------------
    # 3. AI Profile Generation (intake.profile.v1)
    # ---------------------------------------------------------------------------

    def generate_case_profile(self, session_id: str, user_id: str) -> dict[str, Any]:
        """
        Executes AI profiling task `intake.profile.v1` via AIGateway.
        Applies schema validation and outcome prediction filtering.
        """
        session = self.get_session(session_id, user_id=user_id)
        if not session:
            raise ValueError(f"Intake session '{session_id}' not found.")

        answers = session.get("answers", {})

        # Invoke AI Gateway
        ai_response = self.gateway.execute(
            task="intake.profile.v1",
            input_data={
                "answers": answers,
                "triage_chips": session.get("triage_chips", []),
                "urgency": session.get("urgency", "normal"),
            },
        )

        output_data = ai_response.get("output", {})
        if isinstance(output_data, str):
            try:
                output_data = json.loads(output_data)
            except Exception:
                output_data = {}

        # Default fallback structure if AI returns empty or malformed
        if not output_data:
            what_happened = str(
                answers.get("what_happened", answers.get("narrative", "আইনি সহায়তা আবেদন"))
            )
            output_data = {
                "case_type": "land_property" if "জমি" in what_happened else "other",
                "title_suggestion": what_happened[:50] if what_happened else "নতুন মামলা খসড়া",
                "parties": [{"name": user_id, "role": "আবেদনকারী", "org": ""}],
                "dates": [],
                "facts": [{"text": what_happened, "span_in_user_text": [0, len(what_happened)]}],
                "documents_mentioned": [],
                "possible_issues": [{"text": "আইনি পর্যালোচনা প্রয়োজন", "kind": "research_suggestion"}],
                "missing_information": ["নথিপত্র যাচাই"],
                "user_objective": str(answers.get("user_objective", "আইনি সমাধান")),
                "clarifying_questions": ["এই বিষয়ে কোনো পূর্বের মামলা আছে কি?"],
                "urgency_signals": [session.get("urgency_reason")]
                if session.get("urgency_reason")
                else [],
            }

        # Apply Outcome Prediction Filter and Schema Allow-Listing
        sanitized_profile = sanitize_ai_profile(output_data)

        # Ground facts against user's actual text (Sprint S7 E2)
        # Every displayed fact must have span_in_user_text that exists in user's own text; drop others.
        user_text_values = [
            str(v).strip()
            for v in answers.values()
            if isinstance(v, (str, list)) and str(v).strip()
        ]
        combined_user_text = " ".join(user_text_values)

        grounded_facts: list[dict[str, Any]] = []
        for f in sanitized_profile.get("facts", []):
            if not isinstance(f, dict):
                continue
            f_text = f.get("text", "").strip()
            if not f_text:
                continue

            span = f.get("span_in_user_text")
            excerpt = None

            # 1. Direct span validation within combined_user_text
            if (
                isinstance(span, list)
                and len(span) == 2
                and isinstance(span[0], int)
                and isinstance(span[1], int)
                and 0 <= span[0] < span[1] <= len(combined_user_text)
            ):
                candidate = combined_user_text[span[0] : span[1]]
                if candidate.strip():
                    excerpt = candidate.strip()

            # 2. Substring matching inside user text
            if not excerpt and combined_user_text:
                idx = combined_user_text.find(f_text)
                if idx != -1:
                    span = [idx, idx + len(f_text)]
                    excerpt = combined_user_text[idx : idx + len(f_text)]
                elif len(f_text) >= 15:
                    sub = f_text[:30]
                    idx2 = combined_user_text.find(sub)
                    if idx2 != -1:
                        end_pos = min(idx2 + len(f_text), len(combined_user_text))
                        span = [idx2, end_pos]
                        excerpt = combined_user_text[idx2:end_pos]

            # Only retain fact if grounded in user text
            if excerpt:
                f["span_in_user_text"] = span
                f["user_excerpt"] = excerpt
                grounded_facts.append(f)
            # Else: dropped as per E2 rule

        # If all were dropped but user supplied text, construct grounded fact directly from user text
        if not grounded_facts and combined_user_text:
            fact_snippet = combined_user_text[:80].strip()
            grounded_facts.append(
                {
                    "text": fact_snippet,
                    "span_in_user_text": [0, len(fact_snippet)],
                    "user_excerpt": fact_snippet,
                }
            )

        sanitized_profile["facts"] = grounded_facts

        # Enforce SRS enum for case_type
        srs_valid_types = {
            "land_property",
            "contract",
            "rent_tenancy",
            "family",
            "criminal_complaint",
            "labour_employment",
            "consumer",
            "notice_received",
            "court_matter",
            "tax",
            "other",
        }
        ctype = sanitized_profile.get("case_type")
        if ctype == "land_dispute":
            ctype = "land_property"
        elif ctype == "general" or ctype not in srs_valid_types:
            ctype = "other"
        sanitized_profile["case_type"] = ctype

        # Save profile to database session
        self.db.update_intake_session(session_id, profile=sanitized_profile, current_step=11)

        self.audit.log(
            actor_id=user_id,
            actor_role="citizen",
            action="generate_intake_profile",
            object_type="intake_session",
            object_id=session_id,
            meta={"case_type": sanitized_profile.get("case_type")},
        )
        return sanitized_profile

    # ---------------------------------------------------------------------------
    # 4. Confirm & Create Case (AC-M06-1, AC-M11-3)
    # ---------------------------------------------------------------------------

    def confirm_and_create_case(
        self,
        session_id: str,
        user_id: str,
        confirmed_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Creates a new citizen case folder from the intake session.
        Only carries over confirmed facts and confirmed events (AC-M06-1).
        AI-proposed items that were not confirmed are kept as proposed or omitted (AC-M11-3).
        """
        session = self.get_session(session_id, user_id=user_id)
        if not session:
            raise ValueError(f"Intake session '{session_id}' not found.")

        profile = session.get("profile") or {}

        title = str(
            confirmed_data.get("title") or profile.get("title_suggestion") or "ইনটেক থেকে তৈরি মামলা"
        )
        case_type = str(confirmed_data.get("case_type") or profile.get("case_type") or "general")
        objective = str(confirmed_data.get("objective") or profile.get("user_objective") or "")
        urgency = session.get("urgency", "normal")

        # 1. Create the case in CaseEngine (M06)
        case = self.case_engine.create_case(
            user_id=user_id,
            title=title,
            case_type=case_type,
            objective=objective,
            urgency=urgency,
            status="action_required" if urgency == "urgent" else "active",
            metadata={
                "source_intake_session_id": session_id,
                "urgency_reason": session.get("urgency_reason"),
            },
        )

        case_id = case["id"]

        # 2. Add confirmed facts (is_proposed=False)
        confirmed_facts = confirmed_data.get("facts", [])
        for f in confirmed_facts:
            ftext = f.get("text") if isinstance(f, dict) else str(f)
            if ftext:
                self.case_engine.add_fact(
                    case_id=case_id,
                    user_id=user_id,
                    fact_text=ftext,
                    is_proposed=False,
                )

        # 3. Add AI proposed facts awaiting confirmation (is_proposed=True)
        proposed_facts = confirmed_data.get("proposed_facts", [])
        for pf in proposed_facts:
            pftext = pf.get("text") if isinstance(pf, dict) else str(pf)
            if pftext:
                self.case_engine.add_fact(
                    case_id=case_id,
                    user_id=user_id,
                    fact_text=pftext,
                    is_proposed=True,
                )

        # 4. Add confirmed events/dates
        confirmed_events = confirmed_data.get("events", [])
        for ev in confirmed_events:
            if isinstance(ev, dict):
                date_str = ev.get("date") or datetime.now(timezone.utc).date().isoformat()
                desc = ev.get("what") or ev.get("description") or "ঘটনা"
                self.case_engine.add_event(
                    case_id=case_id,
                    user_id=user_id,
                    title=desc,
                    event_date=date_str,
                    date_precision=ev.get("precision", "day"),
                    description=desc,
                    event_type="incident",
                )

        # 5. Mark intake session as confirmed and link created_case_id
        self.db.update_intake_session(
            session_id,
            status="confirmed",
            created_case_id=case_id,
        )

        self.audit.log(
            actor_id=user_id,
            actor_role="citizen",
            action="confirm_intake_and_create_case",
            object_type="intake_session",
            object_id=session_id,
            meta={"case_id": case_id, "confirmed_facts_count": len(confirmed_facts)},
        )

        return {
            "session_id": session_id,
            "case_id": case_id,
            "case": case,
            "confirmed_facts_count": len(confirmed_facts),
            "status": "confirmed",
        }


# Singleton intake engine instance
intake_engine = IntakeEngine()
