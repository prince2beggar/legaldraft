"""
Guided Drafting API Endpoints (SRS M05 / M10 / Sprint S8).
Routes:
- GET /templates
- GET /templates/:id
- POST /admin/templates
- PATCH /admin/templates/:id
- POST /admin/templates/:id/approve
- POST /admin/templates/:id/retire
- POST /admin/templates/:id/test-render
- POST /drafts
- GET /drafts
- GET /drafts/:id
- PATCH /drafts/:id/answers
- POST /drafts/:id/check
- POST /drafts/:id/generate
- POST /drafts/:id/checklist/:item_id/confirm
- POST /drafts/:id/finalize
- GET /drafts/:id/export
- DELETE /drafts/:id
- POST /drafts/:id/ai-help
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field

from packages.trust_kernel.db import db_manager
from packages.trust_kernel.draft_engine import draft_engine
from services.api.app.routers.auth import get_current_user

router = APIRouter(tags=["drafts"])


# ---------------------------------------------------------------------------
# Request & Response Schemas
# ---------------------------------------------------------------------------


class TemplateCreateRequest(BaseModel):
    code: str
    title_bn: str
    title_en: str
    category: str
    description_bn: str
    description_en: str | None = None
    what_needed_bn: str | None = None
    version: int = 1
    effective_from: str | None = None
    effective_to: str | None = None
    questions_schema: list[dict[str, Any]] = Field(default_factory=list)
    clauses: list[dict[str, Any]] = Field(default_factory=list)
    checklist_schema: list[dict[str, Any]] = Field(default_factory=list)
    sample_answers: dict[str, Any] = Field(default_factory=dict)


class TemplateUpdateRequest(BaseModel):
    title_bn: str | None = None
    title_en: str | None = None
    category: str | None = None
    description_bn: str | None = None
    description_en: str | None = None
    what_needed_bn: str | None = None
    effective_from: str | None = None
    effective_to: str | None = None
    questions_schema: list[dict[str, Any]] | None = None
    clauses: list[dict[str, Any]] | None = None
    checklist_schema: list[dict[str, Any]] | None = None
    sample_answers: dict[str, Any] | None = None


class TemplateApproveRequest(BaseModel):
    note: str
    effective_from: str | None = None
    effective_to: str | None = None


class TemplateRetireRequest(BaseModel):
    note: str | None = None


class CreateDraftRequest(BaseModel):
    template_id: str
    case_id: str | None = None
    title: str | None = None


class UpdateAnswersRequest(BaseModel):
    answers: dict[str, Any] = Field(default_factory=dict)
    selected_clause_ids: list[str] | None = None


class ConfirmChecklistItemRequest(BaseModel):
    confirmed: bool = True


class AIHelpRequest(BaseModel):
    question_id: str
    user_query: str = ""


# ---------------------------------------------------------------------------
# Template Endpoints (Citizen & Admin)
# ---------------------------------------------------------------------------


@router.get("/templates")
def list_templates(
    category: str | None = None,
    current_user: dict = Depends(get_current_user),
):
    """Returns available templates for drafting. Citizens only receive approved templates in prod (AC-M05-1)."""
    user_role = current_user.get("role", "citizen")
    available = draft_engine.get_available_templates(user_role=user_role)
    if category:
        available = [t for t in available if t.get("category") == category]
    return {"templates": available, "count": len(available)}


@router.get("/templates/{template_id}")
def get_template(
    template_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Returns details and questions schema for a template."""
    tmpl = db_manager.get_template(template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")

    user_role = current_user.get("role", "citizen")
    is_staging = draft_engine.is_staging_allowed()
    if user_role == "citizen" and tmpl["status"] != "approved" and not is_staging:
        raise HTTPException(status_code=403, detail="Template is not approved for citizen drafting")

    return tmpl


@router.post("/admin/templates")
def admin_create_template(
    req: TemplateCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Admin creates a new drafting template."""
    if current_user.get("role") not in ("admin", "reviewer"):
        raise HTTPException(status_code=403, detail="Admin or reviewer role required")

    try:
        created = db_manager.create_template(
            code=req.code,
            title_bn=req.title_bn,
            title_en=req.title_en,
            category=req.category,
            description_bn=req.description_bn,
            description_en=req.description_en,
            what_needed_bn=req.what_needed_bn,
            version=req.version,
            status="draft_not_reviewed",
            author_id=current_user["sub"],
            effective_from=req.effective_from,
            effective_to=req.effective_to,
            questions_schema=req.questions_schema,
            clauses=req.clauses,
            checklist_schema=req.checklist_schema,
            sample_answers=req.sample_answers,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return created


@router.patch("/admin/templates/{template_id}")
def admin_update_template(
    template_id: str,
    req: TemplateUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    """Admin updates template schema or metadata."""
    if current_user.get("role") not in ("admin", "reviewer"):
        raise HTTPException(status_code=403, detail="Admin or reviewer role required")

    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    updated = db_manager.update_template(template_id, **updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Template not found")
    return updated


@router.post("/admin/templates/{template_id}/approve")
def admin_approve_template(
    template_id: str,
    req: TemplateApproveRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Approves template. Enforces dual custody: approver_id != author_id (AC-M05-1).
    Writes audit entry.
    """
    if current_user.get("role") not in ("admin", "reviewer"):
        raise HTTPException(status_code=403, detail="Admin or reviewer role required")

    try:
        approved = db_manager.approve_template(
            template_id=template_id,
            approver_id=current_user["sub"],
            note=req.note,
            effective_from=req.effective_from,
            effective_to=req.effective_to,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return approved


@router.post("/admin/templates/{template_id}/retire")
def admin_retire_template(
    template_id: str,
    req: TemplateRetireRequest,
    current_user: dict = Depends(get_current_user),
):
    """Retires a template from citizen drafting."""
    if current_user.get("role") not in ("admin", "reviewer"):
        raise HTTPException(status_code=403, detail="Admin or reviewer role required")

    try:
        retired = db_manager.retire_template(
            template_id=template_id,
            actor_id=current_user["sub"],
            note=req.note,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return retired


@router.post("/admin/templates/{template_id}/test-render")
def admin_test_render_template(
    template_id: str,
    sample_answers: dict[str, Any] | None = None,
    current_user: dict = Depends(get_current_user),
):
    """Test-renders template clauses using sample answers without creating a permanent citizen draft."""
    if current_user.get("role") not in ("admin", "reviewer"):
        raise HTTPException(status_code=403, detail="Admin or reviewer role required")

    tmpl = db_manager.get_template(template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")

    answers = sample_answers or tmpl.get("sample_answers", {})

    # Render clauses with answers
    rendered_clauses = []
    for c in tmpl.get("clauses", []):
        text_tpl = c.get("text_template_bn", "")
        for k, v in answers.items():
            text_tpl = text_tpl.replace(f"{{{k}}}", str(v))
        rendered_clauses.append({"id": c["id"], "title_bn": c.get("title_bn"), "text": text_tpl})

    return {
        "template_code": tmpl["code"],
        "sample_answers": answers,
        "clauses": rendered_clauses,
        "status": "success",
    }


# ---------------------------------------------------------------------------
# Citizen Drafting Flow Endpoints (M05)
# ---------------------------------------------------------------------------


@router.post("/drafts")
def create_draft(
    req: CreateDraftRequest,
    current_user: dict = Depends(get_current_user),
):
    """Starts a new draft from an approved template (AC-M05-1)."""
    try:
        draft = draft_engine.start_draft(
            user_id=current_user["sub"],
            template_id=req.template_id,
            case_id=req.case_id,
            title=req.title,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return draft


@router.get("/drafts")
def list_drafts(
    case_id: str | None = None,
    current_user: dict = Depends(get_current_user),
):
    """Lists drafts belonging to authenticated user."""
    drafts = db_manager.list_drafts(user_id=current_user["sub"], case_id=case_id)
    return {"drafts": drafts, "count": len(drafts)}


@router.get("/drafts/{draft_id}")
def get_draft(
    draft_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Returns draft with template metadata, current answers, and prefill origins."""
    draft = db_manager.get_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft["user_id"] != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Access denied")

    tmpl = db_manager.get_template(draft["template_id"])
    return {"draft": draft, "template": tmpl}


@router.patch("/drafts/{draft_id}/answers")
def save_draft_answers(
    draft_id: str,
    req: UpdateAnswersRequest,
    current_user: dict = Depends(get_current_user),
):
    """Saves answers and clause selections with autosave support."""
    try:
        updated = draft_engine.save_answers(
            draft_id=draft_id,
            user_id=current_user["sub"],
            answers=req.answers,
            selected_clause_ids=req.selected_clause_ids,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return updated


@router.post("/drafts/{draft_id}/check")
def check_draft_consistency(
    draft_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Runs consistency and validation checks (AC-M05-5)."""
    try:
        check_result = draft_engine.run_consistency_checks(
            draft_id=draft_id,
            user_id=current_user["sub"],
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return check_result


@router.post("/drafts/{draft_id}/generate")
def generate_draft_preview(
    draft_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Renders live document preview with watermark (AC-M05-3)."""
    try:
        preview = draft_engine.render_document_preview(
            draft_id=draft_id,
            user_id=current_user["sub"],
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return preview


@router.post("/drafts/{draft_id}/checklist/{item_id}/confirm")
def confirm_checklist_item(
    draft_id: str,
    item_id: str,
    req: ConfirmChecklistItemRequest,
    current_user: dict = Depends(get_current_user),
):
    """Confirms or toggles execution checklist item (AC-M05-3)."""
    try:
        updated = draft_engine.toggle_checklist_item(
            draft_id=draft_id,
            user_id=current_user["sub"],
            item_id=item_id,
            confirmed=req.confirmed,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return updated


@router.post("/drafts/{draft_id}/finalize")
def finalize_draft(
    draft_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Finalizes draft (AC-M05-3).
    Removes watermark only when all required answers + consistency checks + execution checklist items are confirmed.
    """
    try:
        finalized = draft_engine.finalize_draft(
            draft_id=draft_id,
            user_id=current_user["sub"],
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return finalized


@router.get("/drafts/{draft_id}/export")
def export_draft(
    draft_id: str,
    format: str = Query(default="pdf", pattern="^(pdf|docx)$"),
    current_user: dict = Depends(get_current_user),
):
    """
    Exports draft to PDF or DOCX (AC-M05-4).
    Files are encrypted at rest with AES-256-GCM.
    Decrypted bytes are returned to the authenticated user on download.
    """
    try:
        res = draft_engine.export_draft(
            draft_id=draft_id,
            user_id=current_user["sub"],
            export_format=format,
        )
        content, filename, media_type = draft_engine.get_decrypted_export_bytes(
            export_id=res["export_id"],
            user_id=current_user["sub"],
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/drafts/{draft_id}/signing-checklist")
def get_signing_checklist(
    draft_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Returns document-specific post-finalization signing checklist (AC-M05-6)."""
    try:
        checklist = draft_engine.get_signing_checklist(
            draft_id=draft_id,
            user_id=current_user["sub"],
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return checklist


@router.post("/drafts/{draft_id}/ai-help")
def get_draft_ai_help(
    draft_id: str,
    req: AIHelpRequest,
    current_user: dict = Depends(get_current_user),
):
    """Invokes draft.helper.v1 for question rephrasing, optional clause suggestions, or term explanation."""
    try:
        help_result = draft_engine.get_ai_help(
            draft_id=draft_id,
            user_id=current_user["sub"],
            question_id=req.question_id,
            user_query=req.user_query,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return help_result


@router.delete("/drafts/{draft_id}")
def delete_draft(
    draft_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Deletes draft with ownership check and audit logging."""
    try:
        deleted = draft_engine.delete_draft(draft_id, user_id=current_user["sub"])
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    if not deleted:
        raise HTTPException(status_code=404, detail="Draft not found or unauthorized")
    return {"status": "deleted", "draft_id": draft_id}
