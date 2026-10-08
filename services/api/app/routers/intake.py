"""
Intake & Triage API Endpoints (SRS M11 / Sprint S7).
Routes:
- POST /intake/sessions
- GET /intake/sessions/:id
- PATCH /intake/sessions/:id
- POST /intake/sessions/:id/abandon
- POST /intake/sessions/:id/resume
- POST /intake/sessions/:id/profile
- POST /intake/sessions/:id/confirm
- GET /emergency-contacts
- POST /admin/emergency-contacts
- PATCH /admin/emergency-contacts/:id
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from packages.trust_kernel.db import db_manager
from packages.trust_kernel.intake_engine import intake_engine
from services.api.app.routers.auth import get_current_user

router = APIRouter(tags=["intake"])


# ---------------------------------------------------------------------------
# Request & Response Schemas
# ---------------------------------------------------------------------------


class CreateSessionRequest(BaseModel):
    triage_chips: list[str] = Field(default_factory=list)


class UpdateSessionRequest(BaseModel):
    question_key: str | None = None
    answer_value: Any = None
    step: int | None = None
    answers: dict[str, Any] | None = None


class ConfirmCaseRequest(BaseModel):
    title: str | None = None
    case_type: str | None = None
    objective: str | None = None
    facts: list[Any] = Field(default_factory=list)
    proposed_facts: list[Any] = Field(default_factory=list)
    events: list[Any] = Field(default_factory=list)


class EmergencyContactCreateRequest(BaseModel):
    title: str
    phone: str
    category: str = "emergency"
    description_bn: str | None = None
    description_en: str | None = None
    is_verified: bool = False
    last_verified_at: str | None = None
    verified_by: str | None = None
    display_order: int = 0


class EmergencyContactUpdateRequest(BaseModel):
    title: str | None = None
    phone: str | None = None
    category: str | None = None
    description_bn: str | None = None
    description_en: str | None = None
    is_verified: bool | None = None
    last_verified_at: str | None = None
    verified_by: str | None = None
    is_active: bool | None = None
    display_order: int | None = None


# ---------------------------------------------------------------------------
# Emergency Contacts Endpoints (Public & Admin)
# ---------------------------------------------------------------------------


@router.get("/emergency-contacts")
def list_emergency_contacts(active_only: bool = True):
    """
    Returns emergency contacts for the UrgentBanner and helpline directory.
    Includes verification metadata (last_verified_at).
    """
    contacts = db_manager.list_emergency_contacts(active_only=active_only)
    if not contacts:
        # Seed default contacts on first load
        db_manager.seed_default_emergency_contacts()
        contacts = db_manager.list_emergency_contacts(active_only=active_only)
    return {"contacts": contacts, "total": len(contacts)}


@router.post("/admin/emergency-contacts")
def create_emergency_contact(
    req: EmergencyContactCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Admin endpoint to create a new emergency contact."""
    if current_user.get("role") not in {"admin", "lawyer"}:
        raise HTTPException(status_code=403, detail="Forbidden. Admin access required.")

    contact = db_manager.create_emergency_contact(
        title=req.title,
        phone=req.phone,
        category=req.category,
        description_bn=req.description_bn,
        description_en=req.description_en,
        is_verified=req.is_verified,
        last_verified_at=req.last_verified_at,
        verified_by=req.verified_by or current_user["sub"],
        display_order=req.display_order,
    )
    return {"contact": contact, "status": "created"}


class VerifyEmergencyContactRequest(BaseModel):
    source_note: str


@router.post("/admin/emergency-contacts/{contact_id}/verify")
def verify_emergency_contact(
    contact_id: str,
    req: VerifyEmergencyContactRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Admin verification action.
    Requires:
    1. Admin user role (forbidden for non-admins).
    2. Non-empty source_note (official source URL or reference).
    3. Writes immutable audit ledger entry.
    """
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=403, detail="Forbidden. Admin access required to verify numbers."
        )

    note = (req.source_note or "").strip()
    if not note:
        raise HTTPException(
            status_code=422,
            detail="Source note (official URL or reference) is required to verify an emergency contact.",
        )

    contact = db_manager.get_emergency_contact(contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="Emergency contact not found.")

    now_iso = db_manager.now_iso()
    admin_id = str(current_user.get("id") or current_user.get("sub") or "admin")
    updated = db_manager.update_emergency_contact(
        contact_id,
        is_verified=True,
        last_verified_at=now_iso,
        verified_by=admin_id,
        source_note=note,
    )

    from packages.trust_kernel.audit import audit_service

    audit_service.log(
        actor_id=admin_id,
        actor_role="admin",
        action="emergency_contact.verify",
        object_type="emergency_contact",
        object_id=contact_id,
        ip="127.0.0.1",
        meta={
            "source_note": note,
            "verified_at": now_iso,
            "phone": contact["phone"],
        },
    )
    return {"contact": updated, "status": "verified"}


# ---------------------------------------------------------------------------
# Intake Sessions Endpoints
# ---------------------------------------------------------------------------


@router.post("/intake/sessions")
def create_session(
    req: CreateSessionRequest,
    current_user: dict = Depends(get_current_user),
):
    """Creates a new intake session with initial triage chips."""
    session = intake_engine.create_session(
        user_id=current_user["sub"],
        triage_chips=req.triage_chips,
    )
    return {"session": session, "status": "created"}


@router.get("/intake/sessions/{session_id}")
def get_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Retrieves an existing intake session."""
    try:
        session = intake_engine.get_session(session_id, user_id=current_user["sub"])
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    if not session:
        raise HTTPException(status_code=404, detail="Intake session not found.")
    return {"session": session}


@router.patch("/intake/sessions/{session_id}")
def update_session_answer(
    session_id: str,
    req: UpdateSessionRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Saves an answer to a question in the intake flow.
    Automatically evaluates triage urgency (only raises, never lowers).
    """
    updated: dict[str, Any] | None = None
    try:
        if req.question_key is not None:
            updated = intake_engine.save_answer(
                session_id=session_id,
                user_id=current_user["sub"],
                question_key=req.question_key,
                answer_value=req.answer_value,
                step=req.step,
            )
        elif req.answers:
            session_res: dict[str, Any] | None = None
            for k, v in req.answers.items():
                session_res = intake_engine.save_answer(
                    session_id=session_id,
                    user_id=current_user["sub"],
                    question_key=k,
                    answer_value=v,
                    step=req.step,
                )
            updated = session_res or intake_engine.get_session(
                session_id, user_id=current_user["sub"]
            )
        else:
            updated = intake_engine.get_session(session_id, user_id=current_user["sub"])
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if not updated:
        raise HTTPException(status_code=404, detail="Intake session not found.")

    return {"session": updated, "status": "saved"}


@router.post("/intake/sessions/{session_id}/abandon")
def abandon_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Marks session as abandoned, preserving all answers."""
    try:
        session = intake_engine.abandon_session(session_id, user_id=current_user["sub"])
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return {"session": session, "status": "abandoned"}


@router.post("/intake/sessions/{session_id}/resume")
def resume_session(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Resumes an abandoned or in-progress session with preserved answers."""
    try:
        session = intake_engine.resume_session(session_id, user_id=current_user["sub"])
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return {"session": session, "status": "resumed"}


@router.post("/intake/sessions/{session_id}/profile")
def generate_profile(
    session_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Executes intake.profile.v1 AI task and returns sanitized Case Profile."""
    try:
        profile = intake_engine.generate_case_profile(session_id, user_id=current_user["sub"])
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"profile": profile, "status": "generated"}


@router.post("/intake/sessions/{session_id}/confirm")
def confirm_and_create_case(
    session_id: str,
    req: ConfirmCaseRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Creates a new case from the confirmed profile.
    Carries over only confirmed facts and events (AC-M06-1 and AC-M11-3).
    """
    try:
        result = intake_engine.confirm_and_create_case(
            session_id=session_id,
            user_id=current_user["sub"],
            confirmed_data=req.model_dump(),
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result
