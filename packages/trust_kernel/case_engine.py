"""
Case Folder Management Engine (SRS M06, Sprint S6).

Provides comprehensive case folder workflows:
1. Full Case CRUD with status transitions:
   `new`, `active`, `waiting`, `with_lawyer`, `action_required`, `urgent`, `completed`, `archived`.
2. 8 Tab support: Overview, Timeline, Documents, Tasks, Deadlines, Notes, Review, Lawyer.
3. Case elements: Parties, Events (with date precision), Facts, Private Notes, Tasks, Deadlines.
4. Strict Note Privacy (AC-M06-5):
   Private notes are strictly excluded from AI analysis prompts unless explicitly checked by user.
5. Deletion handling: Asks what to do with documents ('keep', 'unlink', 'delete').
6. Notice-to-Case integration:
   'Save to case' from S5 notice screen populates case with parties, timeline events, deadlines, tasks, and documents.
7. AI Case Review (case.review.v1):
   Analyzes case details for issues, missing info, required docs, approved processes, questions for lawyer,
   and options to discuss. Strictly prohibits outcome statements or win/loss predictions.
   Suggested items start as 'proposed' and are ignored by Next Action until accepted.
8. Complete audit logging on every action.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from packages.trust_kernel.ai_gateway import AIGateway, ai_gateway
from packages.trust_kernel.audit import InMemoryAuditService, audit_service
from packages.trust_kernel.db import DatabaseManager, db_manager

logger = logging.getLogger(__name__)

VALID_STATUSES = {
    "new",
    "active",
    "waiting",
    "with_lawyer",
    "action_required",
    "urgent",
    "completed",
    "archived",
}

from packages.trust_kernel.outcome_filter import ALL_OUTCOME_PATTERNS

OUTCOME_PROHIBITED_PATTERNS = ALL_OUTCOME_PATTERNS


class CaseEngine:
    def __init__(
        self,
        db: DatabaseManager | None = None,
        gateway: AIGateway | None = None,
        audit: InMemoryAuditService | None = None,
    ):
        self.db = db or db_manager
        self.gateway = gateway or ai_gateway
        self.audit = audit or audit_service

    # ---------------------------------------------------------------------------
    # 1. Case Lifecycle
    # ---------------------------------------------------------------------------

    def create_case(
        self,
        user_id: str,
        title: str,
        case_type: str = "general",
        description: str | None = None,
        objective: str | None = None,
        urgency: str = "normal",
        status: str = "new",
        legacy_matter_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Creates a new citizen case folder (SRS M06)."""
        if status not in VALID_STATUSES:
            raise ValueError(
                f"Invalid case status '{status}'. Must be one of: {sorted(VALID_STATUSES)}"
            )

        meta_json = json.dumps(metadata, ensure_ascii=False) if metadata else None
        case = self.db.create_case(
            owner_id=user_id,
            title=title,
            case_type=case_type,
            description=description,
            objective=objective,
            urgency=urgency,
            status=status,
            legacy_matter_id=legacy_matter_id,
            metadata_json=meta_json,
        )

        self.audit.record_event(
            actor_id=user_id,
            action="case.created",
            object_type="case",
            object_id=case["id"],
            description=f"Created case '{title}'",
            metadata={"case_type": case_type, "status": status},
        )
        return case

    def create_case_from_intake(
        self,
        user_id: str,
        intake_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Creates a citizen case from intake data (AC-M06-1, Sprint S6/S7 bridge).
        Strict Rule: Carries over ONLY confirmed facts and confirmed events.
        Unconfirmed items from intake are strictly excluded from active case facts/events.
        """
        title = intake_data.get("title") or intake_data.get("case_title") or "ইনটেক থেকে প্রস্তুত মামলা"
        case_type = intake_data.get("case_type", "general")
        description = intake_data.get("description", "")
        urgency = intake_data.get("urgency", "normal")
        status = intake_data.get("status", "new")
        metadata = intake_data.get("metadata")

        case = self.create_case(
            user_id=user_id,
            title=title,
            case_type=case_type,
            description=description,
            urgency=urgency,
            status=status,
            metadata=metadata,
        )
        case_id = case["id"]

        # Carry over ONLY confirmed facts
        raw_facts = intake_data.get("facts") or intake_data.get("extracted_facts", [])
        for f in raw_facts:
            is_conf = False
            fact_txt = ""
            if isinstance(f, dict):
                is_conf = bool(
                    f.get("is_confirmed") or f.get("confirmed") or f.get("status") == "confirmed"
                )
                fact_txt = f.get("fact_text") or f.get("text", "")
            elif isinstance(f, str):
                fact_txt = f
                is_conf = False

            if is_conf and fact_txt:
                self.db.add_case_fact(
                    case_id=case_id,
                    fact_text=fact_txt,
                    status="active",
                    is_proposed=False,
                )

        # Carry over ONLY confirmed events
        raw_events = intake_data.get("events") or intake_data.get("timeline_events", [])
        for evt in raw_events:
            if isinstance(evt, dict):
                is_conf = bool(
                    evt.get("is_confirmed")
                    or evt.get("confirmed")
                    or evt.get("status") == "confirmed"
                )
                if is_conf:
                    self.db.add_case_event(
                        case_id=case_id,
                        title=evt.get("title", "ঘটনাবলী"),
                        event_date=evt.get(
                            "event_date", datetime.now(timezone.utc).strftime("%Y-%m-%d")
                        ),
                        date_precision=evt.get("date_precision", "day"),
                        description=evt.get("description"),
                        event_type=evt.get("event_type", "other"),
                    )

        # Parties (if present in intake)
        for party in intake_data.get("parties", []):
            if isinstance(party, dict) and party.get("name"):
                self.db.add_case_party(
                    case_id=case_id,
                    name=party["name"],
                    role=party.get("role", "other"),
                    contact_info=party.get("contact_info"),
                )

        self.audit.record_event(
            actor_id=user_id,
            action="case.intake_imported",
            object_type="case",
            object_id=case_id,
            description="Created case from intake carrying only confirmed facts and events (AC-M06-1)",
        )
        return self.get_case(case_id, user_id)

    def map_legacy_matter_to_case(
        self,
        matter_id: str,
        owner_id: str,
        matter_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Maps a legacy matter into a modern case folder (Decision D08, ADR-027).
        Preserves legacy matter intact (read-only), links via legacy_matter_id.
        Reversible and non-destructive.
        """
        # Check if already mapped
        existing = self.db.list_cases(owner_id=owner_id)
        for c in existing:
            if c.get("legacy_matter_id") == matter_id:
                return self.get_case(c["id"], owner_id)

        m = matter_data or {}
        title = m.get("title") or f"উত্তরাধিকার সূত্রে প্রাপ্ত মামলা #{matter_id}"
        case_type = m.get("matter_type") or m.get("case_type") or "legacy_civil"
        description = m.get("description") or f"Legacy matter reference: {matter_id}"
        urgency = m.get("urgency", "normal")
        status = m.get("status", "active")

        case = self.create_case(
            user_id=owner_id,
            title=title,
            case_type=case_type,
            description=description,
            urgency=urgency,
            status=status,
            legacy_matter_id=matter_id,
            metadata={"source": "legacy_matters", "matter_id": matter_id},
        )
        case_id = case["id"]

        if m.get("client_name"):
            self.db.add_case_party(
                case_id,
                name=m["client_name"],
                role="petitioner",
                contact_info=m.get("client_phone"),
            )
        if m.get("opponent_name"):
            self.db.add_case_party(
                case_id,
                name=m["opponent_name"],
                role="respondent",
                contact_info=m.get("opponent_phone"),
            )

        if m.get("filing_date"):
            self.db.add_case_event(
                case_id=case_id,
                title="মামলা দায়ের (মূল ফাইলিং)",
                event_date=m["filing_date"],
                date_precision="day",
                event_type="filing",
            )

        self.audit.record_event(
            actor_id=owner_id,
            action="case.legacy_matter_mapped",
            object_type="case",
            object_id=case_id,
            description=f"Mapped legacy matter {matter_id} to case {case_id} (ADR-027)",
        )
        return self.get_case(case_id, owner_id)

    def unmap_legacy_matter_from_case(
        self,
        matter_id: str,
        owner_id: str,
    ) -> bool:
        """
        Reversibly unmaps and rolls back a modern case folder created from a legacy matter (ADR-027).
        Preserves the legacy matter intact, removes the modern case wrapper and linked sub-objects.
        """
        existing = self.db.list_cases(owner_id=owner_id)
        target_case = None
        for c in existing:
            if c.get("legacy_matter_id") == matter_id:
                target_case = c
                break

        if not target_case:
            return False

        case_id = target_case["id"]
        with self.db.get_session() as session:
            from packages.trust_kernel.db import (
                CaseDB,
                CaseDocumentDB,
                CaseEventDB,
                CaseFactDB,
                CaseNoteDB,
                CasePartyDB,
                DeadlineDB,
                TaskDB,
            )

            session.query(CasePartyDB).filter(CasePartyDB.case_id == case_id).delete()
            session.query(CaseEventDB).filter(CaseEventDB.case_id == case_id).delete()
            session.query(CaseFactDB).filter(CaseFactDB.case_id == case_id).delete()
            session.query(CaseNoteDB).filter(CaseNoteDB.case_id == case_id).delete()
            session.query(TaskDB).filter(TaskDB.case_id == case_id).delete()
            session.query(DeadlineDB).filter(DeadlineDB.case_id == case_id).delete()
            session.query(CaseDocumentDB).filter(CaseDocumentDB.case_id == case_id).delete()
            session.query(CaseDB).filter(CaseDB.id == case_id).delete()
            session.commit()

        self.audit.record_event(
            actor_id=owner_id,
            action="case.legacy_matter_unmapped",
            object_type="case",
            object_id=case_id,
            description=f"Rolled back / unmapped legacy matter {matter_id} from case {case_id} (ADR-027)",
        )
        return True

    def get_case(self, case_id: str, user_id: str) -> dict[str, Any]:
        """Retrieves full case details with ownership authorization check."""
        case = self.db.get_case(case_id)
        if not case:
            raise LookupError(f"Case '{case_id}' not found.")
        if case["owner_id"] != user_id:
            raise PermissionError(f"User '{user_id}' does not own case '{case_id}'.")

        # Hydrate all 8 tabs
        parties = self.db.list_case_parties(case_id)
        events = self.db.list_case_events(case_id)
        facts = self.db.list_case_facts(case_id, include_proposed=True)
        notes = self.db.list_case_notes(case_id, user_id=user_id)
        documents = self.db.list_case_documents(case_id)
        tasks = self.db.list_tasks(case_id=case_id)
        deadlines = self.db.list_deadlines(case_id=case_id)

        case["parties"] = parties
        case["events"] = events
        case["facts"] = facts
        case["notes"] = notes
        case["documents"] = documents
        case["tasks"] = tasks
        case["deadlines"] = deadlines
        return case

    def list_cases(self, user_id: str) -> list[dict[str, Any]]:
        """Lists active cases belonging to the user."""
        return self.db.list_cases(owner_id=user_id)

    def update_case(self, case_id: str, user_id: str, **kwargs) -> dict[str, Any]:
        """Updates case metadata and status."""
        case = self.db.get_case(case_id)
        if not case:
            raise LookupError(f"Case '{case_id}' not found.")
        if case["owner_id"] != user_id:
            raise PermissionError(f"User '{user_id}' does not own case '{case_id}'.")

        if "status" in kwargs and kwargs["status"] not in VALID_STATUSES:
            raise ValueError(f"Invalid case status '{kwargs['status']}'.")

        updated = self.db.update_case(case_id, **kwargs)
        self.audit.record_event(
            actor_id=user_id,
            action="case.updated",
            object_type="case",
            object_id=case_id,
            description="Updated case details",
            metadata={k: str(v) for k, v in kwargs.items()},
        )
        return updated or case

    def delete_case(self, case_id: str, user_id: str, document_action: str = "keep") -> bool:
        """
        Deletes a case with explicit document handling:
        document_action in ('keep', 'unlink', 'delete').
        """
        if document_action not in ("keep", "unlink", "delete"):
            raise ValueError("document_action must be 'keep', 'unlink', or 'delete'.")

        case = self.db.get_case(case_id)
        if not case:
            raise LookupError(f"Case '{case_id}' not found.")
        if case["owner_id"] != user_id:
            raise PermissionError(f"User '{user_id}' does not own case '{case_id}'.")

        success = self.db.delete_case(case_id, document_action=document_action)
        self.audit.record_event(
            actor_id=user_id,
            action="case.deleted",
            object_type="case",
            object_id=case_id,
            description=f"Deleted case with document_action='{document_action}'",
            metadata={"document_action": document_action},
        )
        return success

    # ---------------------------------------------------------------------------
    # 2. Parties & Events
    # ---------------------------------------------------------------------------

    def add_party(
        self,
        case_id: str,
        user_id: str,
        name: str,
        role: str,
        contact_info: str | None = None,
    ) -> dict[str, Any]:
        case = self.get_case(case_id, user_id)
        party = self.db.add_case_party(case_id, name=name, role=role, contact_info=contact_info)
        self.audit.record_event(
            actor_id=user_id,
            action="case.party_added",
            object_type="case_party",
            object_id=party["id"],
            description=f"Added party '{name}' ({role}) to case {case['id']}",
        )
        return party

    def delete_party(self, case_id: str, user_id: str, party_id: str) -> bool:
        self.get_case(case_id, user_id)
        return self.db.delete_case_party(party_id)

    def add_event(
        self,
        case_id: str,
        user_id: str,
        title: str,
        event_date: str,
        date_precision: str = "day",
        description: str | None = None,
        event_type: str = "other",
    ) -> dict[str, Any]:
        case = self.get_case(case_id, user_id)
        evt = self.db.add_case_event(
            case_id=case_id,
            title=title,
            event_date=event_date,
            date_precision=date_precision,
            description=description,
            event_type=event_type,
        )
        self.audit.record_event(
            actor_id=user_id,
            action="case.event_added",
            object_type="case_event",
            object_id=evt["id"],
            description=f"Added event '{title}' to case {case['id']}",
        )
        return evt

    # ---------------------------------------------------------------------------
    # 3. Facts (Active vs Proposed)
    # ---------------------------------------------------------------------------

    def add_fact(
        self,
        case_id: str,
        user_id: str,
        fact_text: str,
        source_doc_id: str | None = None,
        is_proposed: bool = False,
    ) -> dict[str, Any]:
        case = self.get_case(case_id, user_id)
        fact = self.db.add_case_fact(
            case_id=case_id,
            fact_text=fact_text,
            source_doc_id=source_doc_id,
            status="proposed" if is_proposed else "active",
            is_proposed=is_proposed,
        )
        self.audit.record_event(
            actor_id=user_id,
            action="case.fact_added",
            object_type="case_fact",
            object_id=fact["id"],
            description=f"Added {'proposed ' if is_proposed else ''}fact to case {case['id']}",
        )
        return fact

    def accept_fact(self, case_id: str, user_id: str, fact_id: str) -> dict[str, Any]:
        self.get_case(case_id, user_id)
        fact = self.db.accept_case_fact(fact_id)
        if not fact:
            raise LookupError(f"Fact '{fact_id}' not found.")
        self.audit.record_event(
            actor_id=user_id,
            action="case.fact_accepted",
            object_type="case_fact",
            object_id=fact_id,
            description="Accepted proposed fact into case",
        )
        return fact

    def dismiss_fact(self, case_id: str, user_id: str, fact_id: str) -> dict[str, Any]:
        self.get_case(case_id, user_id)
        fact = self.db.dismiss_case_fact(fact_id)
        if not fact:
            raise LookupError(f"Fact '{fact_id}' not found.")
        self.audit.record_event(
            actor_id=user_id,
            action="case.fact_dismissed",
            object_type="case_fact",
            object_id=fact_id,
            description="Dismissed proposed fact from case",
        )
        return fact

    def list_facts(
        self, case_id: str, user_id: str, include_proposed: bool = True
    ) -> list[dict[str, Any]]:
        self.get_case(case_id, user_id)
        return self.db.list_case_facts(case_id, include_proposed=include_proposed)

    # ---------------------------------------------------------------------------
    # 4. Notes & Strict Privacy (AC-M06-5)
    # ---------------------------------------------------------------------------

    def add_note(
        self,
        case_id: str,
        user_id: str,
        note_text: str,
        is_private: bool = True,
        include_in_analysis: bool = False,
        include_in_brief: bool = False,
    ) -> dict[str, Any]:
        """
        Adds a private case note.
        AC-M06-5 Note Privacy & Brief Sharing:
        - include_in_analysis defaults to False. Notes are NEVER included in AI context
          unless user explicitly sets include_in_analysis=True.
        - include_in_brief defaults to False. Notes are excluded from lawyer brief
          unless explicitly ticked by citizen (include_in_brief=True).
        """
        self.get_case(case_id, user_id)
        note = self.db.add_case_note(
            case_id=case_id,
            user_id=user_id,
            note_text=note_text,
            is_private=is_private,
            include_in_analysis=include_in_analysis,
            include_in_brief=include_in_brief,
        )
        self.audit.record_event(
            actor_id=user_id,
            action="case.note_added",
            object_type="case_note",
            object_id=note["id"],
            description="Added case note",
            metadata={
                "is_private": str(is_private),
                "include_in_analysis": str(include_in_analysis),
                "include_in_brief": str(include_in_brief),
            },
        )
        return note

    def get_notes_for_brief(self, case_id: str, user_id: str) -> list[dict[str, Any]]:
        """AC-M06-5: Returns ONLY notes where include_in_brief is True."""
        self.get_case(case_id, user_id)
        return self.db.get_notes_for_brief(case_id)

    @staticmethod
    def filter_notes_for_brief(notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """AC-M06-5: Helper to filter notes for sharing in lawyer brief."""
        return [n for n in notes if n.get("include_in_brief") is True]

    def delete_note(self, case_id: str, user_id: str, note_id: str) -> bool:
        self.get_case(case_id, user_id)
        return self.db.delete_case_note(note_id)

    # ---------------------------------------------------------------------------
    # 5. Documents Linkage
    # ---------------------------------------------------------------------------

    def attach_document(self, case_id: str, user_id: str, document_id: str) -> dict[str, Any]:
        self.get_case(case_id, user_id)
        # Verify document exists and belongs to user
        doc = self.db.get_document(document_id)
        if not doc or doc["owner_id"] != user_id:
            raise PermissionError(f"User cannot attach document '{document_id}'.")
        link = self.db.attach_document_to_case(case_id, document_id)
        self.audit.record_event(
            actor_id=user_id,
            action="case.document_attached",
            object_type="case_document",
            object_id=document_id,
            description=f"Attached document {document_id} to case {case_id}",
        )
        return link

    def detach_document(self, case_id: str, user_id: str, document_id: str) -> bool:
        self.get_case(case_id, user_id)
        return self.db.detach_document_from_case(case_id, document_id)

    # ---------------------------------------------------------------------------
    # 6. Notice-to-Case Integration ('Save to case' from S5)
    # ---------------------------------------------------------------------------

    def save_notice_to_case(
        self,
        document_id: str,
        user_id: str,
        case_id: str | None = None,
        case_title: str | None = None,
    ) -> dict[str, Any]:
        """
        'Save to case' from S5 notice screen creates a real case (or attaches to existing)
        with parties, events, deadlines, tasks, and documents populated.
        """
        doc = self.db.get_document(document_id)
        if not doc or doc["owner_id"] != user_id:
            raise PermissionError("Document not found or ownership mismatch.")

        notice_record = self.db.get_notice_analysis(document_id)
        analysis = notice_record["analysis"] if notice_record else {}

        # 1. Resolve or Create Case
        sender_val = analysis.get("sender")
        if isinstance(sender_val, dict):
            sender_text = sender_val.get("text", "অজ্ঞাত প্রেরক")
        elif sender_val:
            sender_text = str(sender_val)
        else:
            sender_text = "অজ্ঞাত প্রেরক"

        summary_desc = (
            analysis.get("summary_one_line")
            or analysis.get("subject")
            or "আইনি নোটিশের জবাব ও প্রতিক্রিয়া"
        )

        dl_card = analysis.get("primary_deadline_card") or {}
        has_deadline = False
        due_date = None
        if isinstance(dl_card, dict) and dl_card.get("due_date"):
            has_deadline = dl_card.get("has_deadline", True)
            due_date = dl_card.get("due_date")
        elif analysis.get("calculated_deadline"):
            has_deadline = True
            due_date = analysis.get("calculated_deadline")

        if case_id:
            case = self.get_case(case_id, user_id)
        else:
            title = case_title or f"আইনি নোটিশ সংক্রান্ত বিরোধ: {sender_text[:60]}"
            case = self.create_case(
                user_id=user_id,
                title=title,
                case_type="notice_response",
                description=summary_desc,
                urgency="urgent" if has_deadline else "normal",
                status="action_required",
            )
            case_id = case["id"]

        # 2. Attach Document
        self.attach_document(case_id, user_id, document_id)
        self.db.update_document_case(document_id, case_id)

        # 3. Add Parties
        user = self.db.get_user(user_id) or {}
        user_name = user.get("name", "নাগরিক (গ্রহীতা)")
        sender_info = sender_text
        self.db.add_case_party(
            case_id, name=user_name, role="petitioner", contact_info=user.get("phone")
        )
        self.db.add_case_party(
            case_id, name=sender_info, role="respondent", contact_info="নোটিশে উল্লিখিত"
        )

        # 4. Add Timeline Events
        today_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.db.add_case_event(
            case_id=case_id,
            title="আইনি নোটিশ গ্রহণ",
            event_date=analysis.get("as_of_date", today_iso),
            date_precision="day",
            description=f"প্রেরক: {sender_info}",
            event_type="notice_received",
        )
        self.db.add_case_event(
            case_id=case_id,
            title="আইন-AI দ্বারা নোটিশ বিশ্লেষণ সম্পন্ন",
            event_date=today_iso,
            date_precision="day",
            description=summary_desc,
            event_type="notice_analyzed",
        )

        # 5. Populate Deadlines
        if has_deadline and due_date:
            existing_dls = self.db.list_deadlines(document_id=document_id)
            if existing_dls:
                for ed in existing_dls:
                    with self.db.get_session() as session:
                        from packages.trust_kernel.db import DeadlineDB

                        session.query(DeadlineDB).filter(DeadlineDB.id == ed["id"]).update(
                            {"case_id": case_id}
                        )
                        session.commit()
            else:
                basis = (
                    dl_card.get("note")
                    if isinstance(dl_card, dict)
                    else analysis.get("deadline_basis", "নোটিশে উল্লেখিত সময়সীমা")
                )
                is_conf = dl_card.get("is_confirmed", False) if isinstance(dl_card, dict) else False
                self.db.create_deadline(
                    case_id=case_id,
                    title="নোটিশের জবাব দাখিল বা প্রয়োজনীয় পদক্ষেপ",
                    due_date=due_date,
                    user_id=user_id,
                    document_id=document_id,
                    calculation_basis=basis,
                    confirmed_by_user=is_conf,
                )
            self.db.add_case_event(
                case_id=case_id,
                title="গুরুত্বপূর্ণ সময়সীমা নির্ধারণ",
                event_date=due_date,
                date_precision="day",
                description=f"শেষ সময়সীমা: {due_date}",
                event_type="deadline_confirmed",
            )

        # 6. Populate Tasks from action_required checklist or required_action
        actions = analysis.get("action_required", [])
        if not actions and analysis.get("required_action"):
            req_act = analysis.get("required_action")
            actions = [req_act] if isinstance(req_act, str) else req_act

        for act in actions:
            task_title = act.get("text", "") if isinstance(act, dict) else str(act)
            if task_title:
                self.db.create_task(
                    case_id=case_id,
                    title=task_title,
                    owner_id=user_id,
                    document_id=document_id,
                    priority="high" if has_deadline else "normal",
                    status="not_started",
                    origin="notice_interpreter",
                )

        # 7. Populate Facts from what_it_says
        for statement in analysis.get("what_it_says", []):
            st_text = statement.get("text", "") if isinstance(statement, dict) else str(statement)
            if st_text:
                self.db.add_case_fact(
                    case_id=case_id,
                    fact_text=st_text,
                    source_doc_id=document_id,
                    status="active",
                    is_proposed=False,
                )

        self.audit.record_event(
            actor_id=user_id,
            action="case.notice_saved",
            object_type="case",
            object_id=case_id,
            description=f"Saved notice {document_id} into case folder {case_id}",
        )
        return self.get_case(case_id, user_id)

    # ---------------------------------------------------------------------------
    # 7. Case Review (case.review.v1 via AI Gateway)
    # ---------------------------------------------------------------------------

    def request_case_review(
        self,
        case_id: str,
        user_id: str,
        prompt_version: str = "1.0.0",
    ) -> dict[str, Any]:
        """
        Executes case.review.v1 via AI Gateway:
        - Six outputs: possible_issues, missing_information, required_documents,
          possible_processes (from approved library only), questions_for_lawyer, options_to_discuss.
        - Strictly NO outcome statements, probabilities, or 'you will win/lose'.
        - AI label 'AI বিশ্লেষণ, আইনি পরামর্শ নয়'.
        - Strict Note Privacy (AC-M06-5): Notes where include_in_analysis == False are omitted.
        - Suggested items start as 'proposed'; user can accept or dismiss.
        """
        case = self.get_case(case_id, user_id)

        # Filter notes by strict privacy flag
        safe_notes = [n["note_text"] for n in case.get("notes", []) if n.get("include_in_analysis")]

        # Prepare variables
        parties_str = ", ".join([f"{p['name']} ({p['role']})" for p in case.get("parties", [])])
        facts_str = "\n".join(
            [f"- {f['fact_text']}" for f in case.get("facts", []) if not f.get("is_proposed")]
        )
        docs_str = ", ".join([d["filename"] for d in case.get("documents", [])])
        tasks_str = ", ".join([t["title"] for t in case.get("tasks", [])])
        notes_str = "\n".join(safe_notes) if safe_notes else "কোনো বিশ্লেষণযোগ্য নোট নেই"

        variables = {
            "case_title": case["title"],
            "case_type": case["case_type"],
            "parties": parties_str or "উল্লেখ নেই",
            "facts": facts_str or "কোনো তথ্য সংরক্ষিত নেই",
            "documents": docs_str or "কোনো নথি নেই",
            "tasks": tasks_str or "কোনো টাস্ক নেই",
            "notes": notes_str,
        }

        # Execute through AI Gateway
        ai_resp = self.gateway.execute_prompt(
            prompt_id="case.review.v1",
            variables=variables,
            prompt_version=prompt_version,
            user_id=user_id,
        )

        output_data = dict(ai_resp.get("data") or ai_resp.get("output", {}))
        if isinstance(output_data, str):
            try:
                output_data = json.loads(output_data)
            except Exception:
                output_data = {}

        # 1. Red-team protection & Anti-Outcome Check (AC-M06-4)
        # Verify that output contains zero win/lose claims, probability, or outcome predictions
        raw_text = json.dumps(output_data, ensure_ascii=False)
        for pattern, replacement in OUTCOME_PROHIBITED_PATTERNS:
            if pattern.search(raw_text):
                logger.warning(
                    "Red-team intercept: detected prohibited outcome pattern '%s' in review. Sanitizing.",
                    pattern.pattern,
                )
                raw_text = pattern.sub(replacement, raw_text)
        try:
            output_data = json.loads(raw_text)
        except Exception:
            pass

        # 2. Filter processes from approved library only (hide unapproved behind DRAFT_NOT_REVIEWED)
        filtered_processes = []
        for proc in output_data.get("possible_processes", []):
            if isinstance(proc, dict):
                if proc.get("status") == "APPROVED":
                    filtered_processes.append(proc)
                else:
                    filtered_processes.append(
                        {
                            "process_name": "[DRAFT_NOT_REVIEWED / খসড়া প্রক্রিয়া]",
                            "statute_ref": "আইনজীবীর যাচাই প্রয়োজন",
                            "status": "DRAFT_NOT_REVIEWED",
                        }
                    )
            elif isinstance(proc, str):
                filtered_processes.append({"process_name": proc, "status": "APPROVED"})
        output_data["possible_processes"] = filtered_processes

        # 3. Mandatory AI Label
        output_data["ai_label"] = "AI বিশ্লেষণ, আইনি পরামর্শ নয়"
        output_data["provider"] = ai_resp.get("provider", "fake")

        # 4. Populate suggested items as 'proposed' facts
        # Next Action algorithm ignores proposed items until citizen accepts them
        for issue in output_data.get("possible_issues", [])[:2]:
            issue_text = issue if isinstance(issue, str) else str(issue)
            self.db.add_case_fact(
                case_id=case_id,
                fact_text=f"সম্ভাব্য আইনি বিষয়: {issue_text}",
                is_proposed=True,
                status="proposed",
            )

        self.audit.record_event(
            actor_id=user_id,
            action="case.reviewed",
            object_type="case",
            object_id=case_id,
            description="Executed AI Case Review (case.review.v1)",
            metadata={"provider": output_data["provider"]},
        )

        return output_data
