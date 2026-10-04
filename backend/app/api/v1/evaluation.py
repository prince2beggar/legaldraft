from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.feedback import FeedbackEntry
from app.models.user import User
from app.schemas.evaluation import FeedbackSubmission, EvaluationSuiteReport
from app.services.evaluation_service import evaluation_service
from services.api.app.routers.auth import get_current_user

router = APIRouter()

@router.post("/feedback")
def submit_feedback(
    data: FeedbackSubmission,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Submits user/lawyer feedback on AI output for continuous evaluation & improvement.
    """
    user_id = current_user.get("sub", "anonymous")

    entry = FeedbackEntry(
        document_id=data.document_id,
        user_id=user_id,
        rating=data.rating,
        feedback_category=data.feedback_category,
        original_text=data.original_text,
        corrected_text=data.corrected_text,
        reviewer_reasoning=data.reviewer_reasoning
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {
        "status": "success",
        "message": "Feedback recorded for AI quality improvement and regression benchmarking.",
        "feedback_id": entry.id
    }

@router.post("/benchmark/run", response_model=EvaluationSuiteReport)
def run_benchmark_evaluations(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Runs automated legal benchmark test cases against the current rule, retrieval, and extraction pipeline.
    """
    if current_user.get("role") not in ("admin", "reviewer"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden. Admin or reviewer role required.",
        )
    return evaluation_service.run_suite(db)
