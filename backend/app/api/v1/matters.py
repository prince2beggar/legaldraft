from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.core.database import get_db
from app.models.matter import Matter
from app.models.organization import Organization
from app.models.user import User
from packages.trust_kernel.policy_consent import policy_consent
from services.api.app.routers.auth import get_current_user

router = APIRouter()

class MatterCreate(BaseModel):
    title: str
    matter_type: str = "commercial_lease"
    client_name: Optional[str] = None
    notes: Optional[str] = None

class MatterResponse(BaseModel):
    id: str
    title: str
    matter_type: str
    client_name: Optional[str]
    status: str
    facts_data: Dict[str, Any]
    created_at: str

@router.post("/", response_model=MatterResponse)
def create_matter(
    data: MatterCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    # Ensure default organization exists for backward compatibility
    org = db.query(Organization).first()
    if not org:
        org = Organization(name="Default Law Office", org_type="law_firm")
        db.add(org)
        db.commit()
        db.refresh(org)

    owner_id = current_user["sub"]

    matter = Matter(
        org_id=org.id,
        user_id=owner_id,
        title=data.title,
        matter_type=data.matter_type,
        client_name=data.client_name,
        status="active",
        notes=data.notes,
        facts_data={},
    )
    db.add(matter)
    db.commit()
    db.refresh(matter)

    return MatterResponse(
        id=matter.id,
        title=matter.title,
        matter_type=matter.matter_type,
        client_name=matter.client_name,
        status=matter.status,
        facts_data=matter.facts_data or {},
        created_at=matter.created_at.isoformat(),
    )

@router.get("/", response_model=List[MatterResponse])
def list_matters(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_role = current_user.get("role", "citizen")
    if user_role in ("admin", "reviewer"):
        matters = db.query(Matter).order_by(Matter.created_at.desc()).all()
    else:
        # Cross-tenant isolation: Citizens only see matters they own
        matters = (
            db.query(Matter)
            .filter(Matter.user_id == current_user["sub"])
            .order_by(Matter.created_at.desc())
            .all()
        )

    return [
        MatterResponse(
            id=m.id,
            title=m.title,
            matter_type=m.matter_type,
            client_name=m.client_name,
            status=m.status,
            facts_data=m.facts_data or {},
            created_at=m.created_at.isoformat(),
        )
        for m in matters
    ]

@router.get("/{matter_id}", response_model=MatterResponse)
def get_matter(
    matter_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    matter = db.query(Matter).filter(Matter.id == matter_id).first()
    if not matter:
        raise HTTPException(status_code=404, detail="Matter not found")

    actor = {"id": current_user["sub"], "role": current_user.get("role", "citizen")}
    obj = {"id": matter.id, "owner_id": matter.user_id, "object_type": "case"}

    # Enforce ownership & consent check via PolicyConsent.can (SRS Section 3.2, X-001)
    if not policy_consent.can(actor=actor, action="read", obj=obj):
        raise HTTPException(
            status_code=403,
            detail="Forbidden. You do not own this matter and consent has not been granted.",
        )

    return MatterResponse(
        id=matter.id,
        title=matter.title,
        matter_type=matter.matter_type,
        client_name=matter.client_name,
        status=matter.status,
        facts_data=matter.facts_data or {},
        created_at=matter.created_at.isoformat(),
    )
