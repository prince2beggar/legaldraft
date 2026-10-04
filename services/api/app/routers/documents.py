"""
Document Ingestion & Management API Router (SRS Section 5.3 M03, 9.3 S4).
Endpoints:
- POST /api/v1/documents/upload
- POST /api/v1/documents/resumable/initiate
- POST /api/v1/documents/resumable/chunk
- GET  /api/v1/documents
- GET  /api/v1/documents/{id}
- GET  /api/v1/documents/{id}/status
- POST /api/v1/documents/{id}/intent
- PATCH /api/v1/documents/fields/{id}
- POST /api/v1/documents/fields/{id}/verify
- DELETE /api/v1/documents/{id}
- Web UI routes: /documents/upload, /documents/intent, /documents/viewer, /documents/status
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from packages.trust_kernel.document_engine import document_service
from packages.trust_kernel.notice_engine import notice_engine
from services.api.app.routers.auth import get_current_user

router = APIRouter(tags=["Document Ingestion (M03) & Notice Interpreter (M04)"])
STATIC_DIR = Path(__file__).resolve().parents[4] / "backend" / "app" / "static"


class ResumableInitRequest(BaseModel):
    filename: str = Field(..., description="Document file name")
    total_size: int = Field(..., ge=1, description="Total size in bytes")
    total_chunks: int = Field(..., ge=1, description="Total number of chunks")
    sha256_hash: str = Field(..., description="Hex SHA-256 hash of complete file")


class IntentRequest(BaseModel):
    intent: str = Field(..., description="respond_notice | verify_deed | prepare_matter | calculate_deadlines | archive")


class EditFieldRequest(BaseModel):
    value: str = Field(..., description="New corrected value for field")
    confirm: bool = Field(default=False, description="Must be true to transition state to 'reviewed' (AC-M03-2)")


class CalculateRelativeDateRequest(BaseModel):
    trigger_date: str = Field(..., description="Date document received (YYYY-MM-DD)")
    days: int = Field(default=15, description="Number of calendar days")
    include_trigger_day: bool = Field(default=False, description="Whether trigger date counts as day 1")
    label: str = Field(default="নোটিশের জবাব দাখিল", description="Deadline label")


class ConfirmDeadlineRequest(BaseModel):
    due_date: str = Field(..., description="Target due date (YYYY-MM-DD)")
    title: str = Field(default="আইনি নোটিশের জবাব দাখিল", description="Deadline title")
    case_id: str | None = Field(default=None, description="Optional associated case ID")
    calculation_steps: list[str] = Field(default_factory=list, description="Reasoning / calculation steps")
    note: str | None = Field(default=None, description="Basis note")
    is_user_set: bool = Field(default=False, description="Whether explicitly overridden by user")


class SaveToCaseRequest(BaseModel):
    case_id: str | None = Field(default=None, description="Existing case ID or None to create new")
    new_case_title: str | None = Field(default=None, description="Title for new case if creating")
    selected_task_indices: list[int] | None = Field(default=None, description="Selected checklist item indices")
    confirmed_deadline: dict[str, Any] | None = Field(default=None, description="Confirmed deadline details to save")


class DismissDeadlineRequest(BaseModel):
    status: str = Field(default="completed", description="completed | dismissed")


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------


@router.post("/api/v1/documents/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    intent: str = Form(default="understand"),
    case_id: str | None = Form(default=None),
    user: dict[str, Any] = Depends(get_current_user),
):
    """
    Direct upload endpoint for document files.
    Enforces file type check, virus scan, deduplication, and full ingestion pipeline.
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file upload.")

    try:
        doc = document_service.upload_document(
            owner_id=user["id"],
            filename=file.filename or "uploaded_document.pdf",
            file_bytes=content,
            intent=intent,
            case_id=case_id,
        )
        return {"status": "success", "document": doc}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/api/v1/documents/resumable/initiate")
def initiate_resumable_upload(
    req: ResumableInitRequest,
    user: dict[str, Any] = Depends(get_current_user),
):
    """Initiates a resumable chunked upload session."""
    session = document_service.initiate_resumable_upload(
        owner_id=user["id"],
        filename=req.filename,
        total_size=req.total_size,
        total_chunks=req.total_chunks,
        sha256_hash=req.sha256_hash,
    )
    return session


@router.post("/api/v1/documents/resumable/chunk")
async def upload_resumable_chunk(
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    chunk: UploadFile = File(...),
    user: dict[str, Any] = Depends(get_current_user),
):
    """Uploads an individual chunk in a resumable session."""
    data = await chunk.read()
    try:
        res = document_service.upload_chunk(upload_id, chunk_index, data)
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/api/v1/documents")
def list_documents(user: dict[str, Any] = Depends(get_current_user)):
    """Lists current user's documents."""
    docs = document_service.db.list_documents(owner_id=user["id"])
    return {"documents": docs, "count": len(docs)}


@router.get("/api/v1/documents/{doc_id}")
def get_document_details(
    doc_id: str,
    user: dict[str, Any] = Depends(get_current_user),
):
    """
    Returns document details, pages, and fields.
    Enforces AC-M03-5 (ownership authorization; audit log on cross-user breach).
    Delegates to legacy drafting document handler if document was generated via drafting.
    """
    doc = document_service.db.get_document(doc_id)
    if not doc:
        # Check if legacy document exists before returning 404
        from backend.app.api.v1.documents import get_document as legacy_get_document
        from backend.app.core.database import SessionLocal
        from backend.app.models.document import Document as LegacyDocument

        db_session = SessionLocal()
        try:
            legacy_doc = db_session.query(LegacyDocument).filter(LegacyDocument.id == doc_id).first()
            if legacy_doc:
                return legacy_get_document(document_id=doc_id, db=db_session, current_user=user)
        finally:
            db_session.close()

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    if not doc.get("storage_key") or not doc.get("owner_id"):
        from backend.app.api.v1.documents import get_document as legacy_get_document
        from backend.app.core.database import SessionLocal

        db_session = SessionLocal()
        try:
            return legacy_get_document(document_id=doc_id, db=db_session, current_user=user)
        finally:
            db_session.close()

    try:
        return document_service.get_document_secure(
            doc_id=doc_id,
            actor_id=user["id"],
            actor_role=user.get("role", "citizen"),
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e



@router.get("/api/v1/documents/{doc_id}/status")
def get_document_status(
    doc_id: str,
    user: dict[str, Any] = Depends(get_current_user),
):
    """Returns live ingestion status, step progression, and error state."""
    doc = document_service.db.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if user.get("role") not in ("admin", "reviewer") and doc["owner_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden.")

    return {
        "id": doc["id"],
        "status": doc["processing_status"],
        "retry_count": doc.get("retry_count", 0),
        "error_message": doc.get("error_message"),
        "page_count": doc.get("page_count", 1),
    }


@router.post("/api/v1/documents/{doc_id}/intent")
def set_document_intent(
    doc_id: str,
    req: IntentRequest,
    user: dict[str, Any] = Depends(get_current_user),
):
    """Sets user's selected intent for document."""
    doc = document_service.db.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if user.get("role") not in ("admin", "reviewer") and doc["owner_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden.")

    document_service.db.set_document_intent(doc_id, req.intent)
    return {"status": "success", "intent": req.intent}


@router.patch("/api/v1/documents/fields/{field_id}")
def edit_field(
    field_id: str,
    req: EditFieldRequest,
    user: dict[str, Any] = Depends(get_current_user),
):
    """
    Edits an extracted field value.
    Enforces AC-M03-2: state changes to 'reviewed' ONLY after explicit confirm=True.
    """
    try:
        updated = document_service.edit_field_value(
            field_id=field_id,
            new_value=req.value,
            user_id=user["id"],
            confirm=req.confirm,
        )
        return {"status": "success", "field": updated}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/api/v1/documents/fields/{field_id}/verify")
def verify_field(
    field_id: str,
    user: dict[str, Any] = Depends(get_current_user),
):
    """Marks an extracted field as verified."""
    try:
        updated = document_service.verify_field_value(field_id=field_id, user_id=user["id"])
        return {"status": "success", "field": updated}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.delete("/api/v1/documents/{doc_id}")
def delete_document(
    doc_id: str,
    purge: bool = Query(default=True),
    user: dict[str, Any] = Depends(get_current_user),
):
    """Deletes and purges document file and extracted text with immutable audit ledger recording."""
    try:
        document_service.purge_document_with_audit(
            doc_id=doc_id,
            user_id=user["id"],
            user_role=user.get("role", "citizen"),
        )
        return {"status": "success", "message": "Document purged and recorded in audit ledger."}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


# ---------------------------------------------------------------------------
# Sprint S5: Notice Interpreter (M04) & Deadlines (M07) Endpoints
# ---------------------------------------------------------------------------


@router.get("/api/v1/documents/{doc_id}/notice")
def get_notice_interpretation(
    doc_id: str,
    as_of_date: str | None = Query(default=None),
    user: dict[str, Any] = Depends(get_current_user),
):
    """
    Interprets a legal notice document according to SRS M04.
    Returns 8 fixed sections with citation-grounded claims, DeadlineCard, and amber AI disclaimer.
    """
    try:
        res = notice_engine.interpret_notice(document_id=doc_id, user_id=user["id"], as_of_date=as_of_date)
        return {"status": "success", "notice": res}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Interpretation error: {e}") from e


@router.post("/api/v1/documents/{doc_id}/notice/simpler")
def explain_notice_simpler(
    doc_id: str,
    user: dict[str, Any] = Depends(get_current_user),
):
    """Rewrites the notice analysis in simpler everyday Bangla (SRS M04)."""
    try:
        simpler = notice_engine.explain_simpler(document_id=doc_id, user_id=user["id"])
        return {"status": "success", "simpler": simpler}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api/v1/documents/{doc_id}/notice/calculate_relative_date")
def calculate_relative_date(
    doc_id: str,
    req: CalculateRelativeDateRequest,
    user: dict[str, Any] = Depends(get_current_user),
):
    """
    Calculates exact deadline from trigger date using Rules Engine relative_period.calendar_days.v1 (AC-M04-3).
    Returns 'How we counted this' breakdown and Bangla numerals.
    """
    try:
        calc_result = notice_engine.calculate_relative_deadline(
            document_id=doc_id,
            trigger_date=req.trigger_date,
            days=req.days,
            include_trigger_day=req.include_trigger_day,
            label=req.label,
        )
        return {"status": "success", "calculation": calc_result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/api/v1/documents/{doc_id}/notice/confirm_deadline")
def confirm_deadline(
    doc_id: str,
    req: ConfirmDeadlineRequest,
    user: dict[str, Any] = Depends(get_current_user),
):
    """
    Confirms a deadline explicitly (AC-M04-2, AC-M07-1).
    Creates deadline record and schedules automated reminders.
    """
    try:
        deadline = notice_engine.db.create_deadline(
            case_id=req.case_id or f"case-{doc_id[:8]}",
            title=req.title,
            due_date=req.due_date,
            user_id=user["id"],
            document_id=doc_id,
            calc_steps=req.calculation_steps,
            calculation_basis=req.note,
            is_user_set=req.is_user_set,
            confirmed_by_user=True,
        )
        notice_engine._log_audit(user["id"], "deadline.confirmed", deadline["id"])
        return {"status": "success", "deadline": deadline}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/api/v1/documents/{doc_id}/notice/save_to_case")
def save_notice_to_case(
    doc_id: str,
    req: SaveToCaseRequest,
    user: dict[str, Any] = Depends(get_current_user),
):
    """
    Saves notice interpretation to case (SRS M04 Step 3):
    Creates case, links document, generates tasks from checklist, and saves confirmed deadline.
    """
    try:
        result = notice_engine.save_to_case(
            document_id=doc_id,
            user_id=user["id"],
            case_id=req.case_id,
            new_case_title=req.new_case_title,
            selected_task_indices=req.selected_task_indices,
            confirmed_deadline_data=req.confirmed_deadline,
        )
        return result
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api/v1/deadlines/{deadline_id}/dismiss")
def dismiss_deadline(
    deadline_id: str,
    req: DismissDeadlineRequest,
    user: dict[str, Any] = Depends(get_current_user),
):
    """
    Dismisses or meets a deadline (AC-M07-1).
    Cancels pending reminder schedules.
    """
    try:
        res = notice_engine.dismiss_or_meet_deadline(deadline_id, status=req.status)
        return {"status": "success", "result": res}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ---------------------------------------------------------------------------
# HTML Web Screens
# ---------------------------------------------------------------------------


@router.get("/documents/upload", response_class=HTMLResponse)
def get_documents_upload_page():
    html_file = STATIC_DIR / "documents_upload.html"
    if not html_file.exists():
        raise HTTPException(status_code=404, detail="documents_upload.html not found")
    return HTMLResponse(content=html_file.read_text(encoding="utf-8"))


@router.get("/documents/intent", response_class=HTMLResponse)
def get_document_intent_page():
    html_file = STATIC_DIR / "document_intent.html"
    if not html_file.exists():
        raise HTTPException(status_code=404, detail="document_intent.html not found")
    return HTMLResponse(content=html_file.read_text(encoding="utf-8"))


@router.get("/documents/viewer", response_class=HTMLResponse)
def get_document_viewer_page():
    html_file = STATIC_DIR / "document_viewer.html"
    if not html_file.exists():
        raise HTTPException(status_code=404, detail="document_viewer.html not found")
    return HTMLResponse(content=html_file.read_text(encoding="utf-8"))


@router.get("/documents/status", response_class=HTMLResponse)
def get_document_status_page():
    html_file = STATIC_DIR / "document_status.html"
    if not html_file.exists():
        raise HTTPException(status_code=404, detail="document_status.html not found")
    return HTMLResponse(content=html_file.read_text(encoding="utf-8"))


@router.get("/documents/{doc_id}/notice", response_class=HTMLResponse)
def get_document_notice_page(doc_id: str):
    html_file = STATIC_DIR / "document_notice.html"
    if not html_file.exists():
        raise HTTPException(status_code=404, detail="document_notice.html not found")
    return HTMLResponse(content=html_file.read_text(encoding="utf-8"))


@router.get("/documents/notice", response_class=HTMLResponse)
def get_documents_notice_generic_page():
    html_file = STATIC_DIR / "document_notice.html"
    if not html_file.exists():
        raise HTTPException(status_code=404, detail="document_notice.html not found")
    return HTMLResponse(content=html_file.read_text(encoding="utf-8"))
