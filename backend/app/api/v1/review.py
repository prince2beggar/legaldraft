from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.document import Document
from app.models.review import Review
from app.schemas.review import DocumentHealthReport
from app.services.review_agent import review_agent
from packages.trust_kernel.policy_consent import policy_consent
from services.api.app.routers.auth import get_current_user

router = APIRouter()

@router.get("/{document_id}/health", response_model=DocumentHealthReport)
def get_document_health_audit(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Performs an instant legal health check, statutory compliance audit, and risk scoring.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    owner_id = document.matter.user_id if document.matter else None
    actor = {"id": current_user["sub"], "role": current_user.get("role", "citizen")}
    obj = {"id": document.id, "owner_id": owner_id, "object_type": "document"}
    if not policy_consent.can(actor=actor, action="read", obj=obj):
        raise HTTPException(status_code=403, detail="Forbidden. You do not own this document.")

    facts = document.structured_facts or {}
    clauses = document.selected_clauses or []

    report = review_agent.audit_document(document_id, facts, clauses, db)

    # Persist or update review in DB
    existing_review = db.query(Review).filter(Review.document_id == document_id).first()
    if not existing_review:
        existing_review = Review(
            document_id=document_id,
            health_score=report.overall_health_score,
            completeness_score=report.completeness_score,
            risk_score=report.risk_score,
            issues_data=[i.model_dump() for i in report.issues],
            professional_review_recommended=report.professional_review_recommended
        )
        db.add(existing_review)
    else:
        existing_review.health_score = report.overall_health_score
        existing_review.completeness_score = report.completeness_score
        existing_review.risk_score = report.risk_score
        existing_review.issues_data = [i.model_dump() for i in report.issues]
        existing_review.professional_review_recommended = report.professional_review_recommended

    db.commit()
    return report
