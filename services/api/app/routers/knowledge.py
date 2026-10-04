"""
Admin Legal Knowledge Center API Router (SRS Section 5.10 M10, 9.3 S2).
Endpoints for managing sources, version ingestion pipeline, review queue, diff, and approval.
Restricted to 'admin' and 'reviewer' roles.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from packages.trust_kernel.db import db_manager
from packages.trust_kernel.source_registry import source_registry
from services.api.app.routers.auth import get_current_user

router = APIRouter(prefix="/admin/sources", tags=["Admin Knowledge Center"])


def require_reviewer_or_admin(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    role = user.get("role", "citizen")
    roles = user.get("roles", [role])
    if "admin" not in roles and "reviewer" not in roles and role not in ("admin", "reviewer"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden. Admin or reviewer role required (SRS M10).",
        )
    return user


class CreateSourceRequest(BaseModel):
    title: str = Field(..., description="Official title of the law/source")
    title_bn: str | None = Field(default=None, description="Bangla title")
    source_type: str = Field(default="statute", description="statute | rule | circular | judgment")
    authority: str = Field(default="Parliament of Bangladesh")
    jurisdiction: str = Field(default="BD")
    language: str = Field(default="bn")
    official: bool = Field(default=True)
    rights: str = Field(
        default="official", description="official | public_domain | licensed | unlicensed"
    )
    url: str | None = None
    source_label: str = Field(default="FAKE_TEST_DATA", description="Labels test vs official data")


class UploadVersionRequest(BaseModel):
    version_label: str = Field(default="1.0", description="Version string e.g. 1.0, 2020 Amendment")
    effective_from: str = Field(..., description="Effective start date YYYY-MM-DD")
    effective_to: str | None = Field(default=None, description="Effective end date YYYY-MM-DD")
    publication_date: str | None = Field(default=None)
    content: str = Field(..., description="Document raw text or extracted text")


class ReviewDecisionRequest(BaseModel):
    decision: str = Field(..., description="approve | reject")
    approval_notes: str | None = Field(default=None)


@router.get("")
def list_sources(
    source_type: str | None = Query(default=None),
    admin_user: dict[str, Any] = Depends(require_reviewer_or_admin),
):
    """Lists all sources in the registry."""
    filters = {}
    if source_type:
        filters["source_type"] = source_type
    sources = db_manager.list_sources(filters=filters if filters else None)

    # Attach version summaries to each source
    enriched = []
    for s in sources:
        versions = db_manager.list_source_versions(source_id=s["id"])
        enriched.append(
            {
                **s,
                "version_count": len(versions),
                "versions": versions,
            }
        )
    return {"sources": enriched}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_source(
    req: CreateSourceRequest,
    admin_user: dict[str, Any] = Depends(require_reviewer_or_admin),
):
    """Registers a new canonical legal source."""
    source_id = source_registry.create_source(
        meta=req.model_dump(),
        actor_id=admin_user["id"],
    )
    return {"source_id": source_id, "message": "Source created successfully"}


@router.post("/{source_id}/versions/upload", status_code=status.HTTP_202_ACCEPTED)
def upload_version(
    source_id: str,
    req: UploadVersionRequest,
    admin_user: dict[str, Any] = Depends(require_reviewer_or_admin),
):
    """
    Uploads a new document version and triggers the asynchronous ingestion pipeline.
    Uploader ID is recorded for AC-M10-1 separation.
    """
    source = db_manager.get_source(source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    version_id = source_registry.add_version(
        source_id=source_id,
        file_content=req.content,
        effective_from=req.effective_from,
        effective_to=req.effective_to,
        version_label=req.version_label,
        uploader_id=admin_user["id"],
        publication_date=req.publication_date,
    )

    jobs = db_manager.list_ingestion_jobs(source_id=source_id)
    latest_job = jobs[0] if jobs else None

    return {
        "version_id": version_id,
        "job_id": latest_job["id"] if latest_job else None,
        "status": "processing",
        "message": "Ingestion pipeline initiated",
    }


@router.get("/jobs/{job_id}/status")
def get_job_status(
    job_id: str,
    admin_user: dict[str, Any] = Depends(require_reviewer_or_admin),
):
    """Returns the per-step status of an ingestion job (AC-M10-6)."""
    job = db_manager.get_ingestion_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return {"job": job}


@router.post("/jobs/{job_id}/retry")
def retry_job(
    job_id: str,
    admin_user: dict[str, Any] = Depends(require_reviewer_or_admin),
):
    """Retries a failed ingestion job (AC-M10-6)."""
    try:
        res = source_registry.retry_ingestion_job(job_id)
        return {"message": "Job retried successfully", "result": res}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/versions/{version_id}/diff")
def get_version_diff(
    version_id: str,
    predecessor_id: str | None = Query(default=None),
    admin_user: dict[str, Any] = Depends(require_reviewer_or_admin),
):
    """
    Computes passage differences between version_id and a predecessor version (AC-M10-2).
    """
    version = db_manager.get_source_version(version_id)
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")

    pred_id = predecessor_id
    if not pred_id:
        # Auto-detect latest prior approved version
        all_versions = db_manager.list_source_versions(source_id=version["source_id"])
        approved = [v for v in all_versions if v["id"] != version_id and v["status"] == "approved"]
        if approved:
            pred_id = approved[-1]["id"]

    if not pred_id:
        return {
            "version_a_id": None,
            "version_b_id": version_id,
            "message": "Initial version (no prior version for diff).",
            "added_count": len(db_manager.get_source_passages(version_id)),
            "removed_count": 0,
            "modified_count": 0,
            "added": db_manager.get_source_passages(version_id),
            "removed": [],
            "modified": [],
        }

    diff = source_registry.compute_version_diff(pred_id, version_id)
    return diff


@router.post("/versions/{version_id}/review")
def review_version(
    version_id: str,
    req: ReviewDecisionRequest,
    reviewer: dict[str, Any] = Depends(require_reviewer_or_admin),
):
    """
    Approves or rejects a source version.
    ENFORCES AC-M10-1: A source version cannot be approved by its uploader.
    ENFORCES AC-M10-2: Date overlap check and version superseding.
    """
    version = db_manager.get_source_version(version_id)
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")

    if req.decision == "approve":
        # Check uploader separation (AC-M10-1)
        if version.get("uploader_id") and reviewer["id"] == version["uploader_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="A source version cannot be approved by its uploader (SRS AC-M10-1 violation).",
            )
        try:
            source_registry.approve(
                version_id=version_id,
                reviewer_id=reviewer["id"],
                approval_notes=req.approval_notes,
            )
            return {"message": "Version approved successfully", "status": "approved"}
        except PermissionError as pe:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
        except ValueError as ve:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(ve))

    elif req.decision == "reject":
        source_registry.reject(
            version_id=version_id,
            reviewer_id=reviewer["id"],
            notes=req.approval_notes or "Rejected by reviewer",
        )
        return {"message": "Version rejected", "status": "rejected"}

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid decision")


@router.get("/review-queue")
def get_review_queue(admin_user: dict[str, Any] = Depends(require_reviewer_or_admin)):
    """Returns all versions awaiting reviewer decision."""
    versions = db_manager.list_source_versions(status="review_pending")
    enriched = []
    for v in versions:
        source = db_manager.get_source(v["source_id"])
        enriched.append(
            {
                "version": v,
                "source_title": source["title"] if source else "Unknown Source",
                "source_type": source["source_type"] if source else "statute",
                "uploader_id": v.get("uploader_id"),
            }
        )
    return {"pending_count": len(enriched), "queue": enriched}
