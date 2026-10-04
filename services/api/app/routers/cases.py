"""
FastAPI Router for Case Folder (M06), Home / Next Action (M02), and Notifications (M07).

Endpoints:
- /api/v1/cases (list, create)
- /api/v1/cases/{id} (get full 8-tab case, update, delete with document action)
- /api/v1/cases/{id}/parties (add, delete)
- /api/v1/cases/{id}/events (add, list)
- /api/v1/cases/{id}/facts (add, accept, dismiss)
- /api/v1/cases/{id}/notes (add, delete with strict privacy flag)
- /api/v1/cases/{id}/documents (attach, detach)
- /api/v1/cases/{id}/review (execute case.review.v1 via AI Gateway)
- /api/v1/documents/{id}/save-to-case (save notice to case)
- /api/v1/home (aggregated home view with greeting, ProblemInput, NextActionCard, QuickActions, My Cases, Upcoming)
- /api/v1/home/next-action (deterministic 10-priority next action)
- /api/v1/notifications & /api/v1/me/notifications (list notifications)
- /api/v1/notifications/trigger (trigger pending notifications in-process)
- /api/v1/me/notification-preferences (get, update)
- /api/v1/admin/notifications/failed (admin failure view)
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from packages.trust_kernel.case_engine import CaseEngine
from packages.trust_kernel.home_engine import HomeEngine
from packages.trust_kernel.notification_engine import NotificationEngine
from services.api.app.routers.auth import get_current_user

router = APIRouter(tags=["Cases, Home & Notifications"])

case_engine = CaseEngine()
home_engine = HomeEngine()
notification_engine = NotificationEngine()


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------

class CreateCaseRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    case_type: str = Field(default="general")
    description: str | None = None
    objective: str | None = None
    urgency: str = Field(default="normal")
    status: str = Field(default="new")
    legacy_matter_id: str | None = None
    metadata: dict[str, Any] | None = None


class UpdateCaseRequest(BaseModel):
    title: str | None = None
    case_type: str | None = None
    description: str | None = None
    objective: str | None = None
    urgency: str | None = None
    status: str | None = None
    metadata_json: str | None = None


class DeleteCaseRequest(BaseModel):
    document_action: str = Field(default="keep", pattern="^(keep|unlink|delete)$")


class CreatePartyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    role: str = Field(default="third_party")
    contact_info: str | None = None


class CreateEventRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    event_date: str = Field(..., min_length=4, max_length=32)
    date_precision: str = Field(default="day")
    description: str | None = None
    event_type: str = Field(default="other")


class CreateFactRequest(BaseModel):
    fact_text: str = Field(..., min_length=1)
    source_doc_id: str | None = None


class CreateNoteRequest(BaseModel):
    note_text: str = Field(..., min_length=1)
    is_private: bool = True
    include_in_analysis: bool = False


class AttachDocumentRequest(BaseModel):
    document_id: str = Field(..., min_length=1)


class SaveNoticeToCaseRequest(BaseModel):
    case_id: str | None = None
    case_title: str | None = None


class NotificationPreferencesRequest(BaseModel):
    enable_in_app: bool | None = None
    enable_sms: bool | None = None
    quiet_hours_enabled: bool | None = None
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    language: str | None = None


# ---------------------------------------------------------------------------
# Cases Endpoints (M06)
# ---------------------------------------------------------------------------

@router.get("/cases")
def list_cases(current_user: dict[str, Any] = Depends(get_current_user)):
    """Lists cases belonging to authenticated user."""
    return {"cases": case_engine.list_cases(current_user["id"])}


@router.post("/cases", status_code=status.HTTP_201_CREATED)
def create_case(payload: CreateCaseRequest, current_user: dict[str, Any] = Depends(get_current_user)):
    """Creates a new case folder."""
    case = case_engine.create_case(
        user_id=current_user["id"],
        title=payload.title,
        case_type=payload.case_type,
        description=payload.description,
        objective=payload.objective,
        urgency=payload.urgency,
        status=payload.status,
        legacy_matter_id=payload.legacy_matter_id,
        metadata=payload.metadata,
    )
    return {"case": case}


@router.get("/cases/{case_id}")
def get_case(case_id: str, current_user: dict[str, Any] = Depends(get_current_user)):
    """Retrieves full case details with all 8 tabs."""
    try:
        case = case_engine.get_case(case_id, current_user["id"])
        return {"case": case}
    except LookupError as ex:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ex))
    except PermissionError as ex:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(ex))


@router.put("/cases/{case_id}")
def update_case(
    case_id: str,
    payload: UpdateCaseRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Updates case properties and status."""
    try:
        data = {k: v for k, v in payload.dict().items() if v is not None}
        case = case_engine.update_case(case_id, current_user["id"], **data)
        return {"case": case}
    except LookupError as ex:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ex))
    except PermissionError as ex:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(ex))


@router.delete("/cases/{case_id}")
def delete_case(
    case_id: str,
    payload: DeleteCaseRequest = DeleteCaseRequest(),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Deletes a case with explicit document handling ('keep', 'unlink', 'delete')."""
    try:
        ok = case_engine.delete_case(case_id, current_user["id"], document_action=payload.document_action)
        return {"success": ok, "document_action": payload.document_action}
    except LookupError as ex:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ex))
    except PermissionError as ex:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(ex))


# --- Parties ---
@router.post("/cases/{case_id}/parties", status_code=status.HTTP_201_CREATED)
def add_case_party(
    case_id: str,
    payload: CreatePartyRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    try:
        party = case_engine.add_party(
            case_id=case_id,
            user_id=current_user["id"],
            name=payload.name,
            role=payload.role,
            contact_info=payload.contact_info,
        )
        return {"party": party}
    except PermissionError as ex:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(ex))


@router.delete("/cases/{case_id}/parties/{party_id}")
def delete_case_party(
    case_id: str,
    party_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    try:
        ok = case_engine.delete_party(case_id=case_id, user_id=current_user["id"], party_id=party_id)
        return {"success": ok}
    except PermissionError as ex:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(ex))


# --- Events ---
@router.post("/cases/{case_id}/events", status_code=status.HTTP_201_CREATED)
def add_case_event(
    case_id: str,
    payload: CreateEventRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    try:
        evt = case_engine.add_event(
            case_id=case_id,
            user_id=current_user["id"],
            title=payload.title,
            event_date=payload.event_date,
            date_precision=payload.date_precision,
            description=payload.description,
            event_type=payload.event_type,
        )
        return {"event": evt}
    except PermissionError as ex:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(ex))


# --- Facts ---
@router.post("/cases/{case_id}/facts", status_code=status.HTTP_201_CREATED)
def add_case_fact(
    case_id: str,
    payload: CreateFactRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    try:
        fact = case_engine.add_fact(
            case_id=case_id,
            user_id=current_user["id"],
            fact_text=payload.fact_text,
            source_doc_id=payload.source_doc_id,
        )
        return {"fact": fact}
    except PermissionError as ex:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(ex))


@router.post("/cases/{case_id}/facts/{fact_id}/accept")
def accept_case_fact(
    case_id: str,
    fact_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    try:
        fact = case_engine.accept_fact(case_id=case_id, user_id=current_user["id"], fact_id=fact_id)
        return {"fact": fact}
    except PermissionError as ex:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(ex))


@router.post("/cases/{case_id}/facts/{fact_id}/dismiss")
def dismiss_case_fact(
    case_id: str,
    fact_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    try:
        fact = case_engine.dismiss_fact(case_id=case_id, user_id=current_user["id"], fact_id=fact_id)
        return {"fact": fact}
    except PermissionError as ex:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(ex))


# --- Notes ---
@router.post("/cases/{case_id}/notes", status_code=status.HTTP_201_CREATED)
def add_case_note(
    case_id: str,
    payload: CreateNoteRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    try:
        note = case_engine.add_note(
            case_id=case_id,
            user_id=current_user["id"],
            note_text=payload.note_text,
            is_private=payload.is_private,
            include_in_analysis=payload.include_in_analysis,
        )
        return {"note": note}
    except PermissionError as ex:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(ex))


@router.delete("/cases/{case_id}/notes/{note_id}")
def delete_case_note(
    case_id: str,
    note_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    try:
        ok = case_engine.delete_note(case_id=case_id, user_id=current_user["id"], note_id=note_id)
        return {"success": ok}
    except PermissionError as ex:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(ex))


# --- Documents ---
@router.post("/cases/{case_id}/documents", status_code=status.HTTP_201_CREATED)
def attach_case_document(
    case_id: str,
    payload: AttachDocumentRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    try:
        link = case_engine.attach_document(case_id=case_id, user_id=current_user["id"], document_id=payload.document_id)
        return {"document_link": link}
    except PermissionError as ex:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(ex))


@router.delete("/cases/{case_id}/documents/{doc_id}")
def detach_case_document(
    case_id: str,
    doc_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    try:
        ok = case_engine.detach_document(case_id=case_id, user_id=current_user["id"], document_id=doc_id)
        return {"success": ok}
    except PermissionError as ex:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(ex))


# --- AI Case Review (case.review.v1) ---
@router.post("/cases/{case_id}/review")
def review_case(
    case_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """
    Executes AI case review (case.review.v1) through AI Gateway:
    - 6 sections: possible_issues, missing_information, required_documents,
      possible_processes, questions_for_lawyer, options_to_discuss.
    - Zero outcome statements or win/loss predictions.
    - Strict Note Privacy: private notes omitted unless include_in_analysis=True.
    """
    try:
        result = case_engine.request_case_review(case_id=case_id, user_id=current_user["id"])
        return {"review": result}
    except LookupError as ex:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ex))
    except PermissionError as ex:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(ex))


# --- Notice to Case Integration ---
@router.post("/documents/{doc_id}/save-to-case")
def save_notice_to_case(
    doc_id: str,
    payload: SaveNoticeToCaseRequest = SaveNoticeToCaseRequest(),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Saves S5 notice analysis into a new or existing case folder."""
    try:
        case = case_engine.save_notice_to_case(
            document_id=doc_id,
            user_id=current_user["id"],
            case_id=payload.case_id,
            case_title=payload.case_title,
        )
        return {"case": case}
    except PermissionError as ex:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(ex))


# ---------------------------------------------------------------------------
# Home Endpoints (M02)
# ---------------------------------------------------------------------------

@router.get("/home")
def get_home(current_user: dict[str, Any] = Depends(get_current_user)):
    """Returns aggregated home view data (greeting, ProblemInput, NextActionCard, QuickActions, My Cases, Upcoming)."""
    return home_engine.get_home_data(current_user["id"])


@router.get("/home/next-action")
def get_next_action(current_user: dict[str, Any] = Depends(get_current_user)):
    """Computes deterministic Next Action from SRS 10-priority table."""
    return {"next_action": home_engine.calculate_next_action(current_user["id"])}


# ---------------------------------------------------------------------------
# Notifications Endpoints (M07)
# ---------------------------------------------------------------------------

@router.get("/notifications")
@router.get("/me/notifications")
def list_notifications(
    status: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Lists notifications for current user."""
    return {"notifications": case_engine.db.list_notifications(current_user["id"], status=status)}


@router.post("/notifications/trigger")
def trigger_notifications(current_user: dict[str, Any] = Depends(get_current_user)):
    """Triggers in-process scheduler cycle for pending notifications."""
    result = notification_engine.trigger_pending_notifications()
    return {"status": "ok", "result": result}


@router.get("/me/notification-preferences")
def get_notification_preferences(current_user: dict[str, Any] = Depends(get_current_user)):
    """Returns user notification preferences."""
    return {"preferences": case_engine.db.get_notification_preferences(current_user["id"])}


@router.put("/me/notification-preferences")
def update_notification_preferences(
    payload: NotificationPreferencesRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Updates user notification preferences."""
    data = {k: v for k, v in payload.dict().items() if v is not None}
    prefs = case_engine.db.save_notification_preferences(current_user["id"], data)
    return {"preferences": prefs}


@router.get("/admin/notifications/failed")
def get_failed_notifications(current_user: dict[str, Any] = Depends(get_current_user)):
    """Admin view of failed notifications after retries."""
    if current_user.get("role") not in ("admin", "reviewer"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required.")
    return {"failed_notifications": notification_engine.list_failed_notifications()}
