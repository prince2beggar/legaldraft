"""
Taxation & VAT API Endpoints (SRS Module M23 / Phase 4 Ecosystem).
Routes:
- POST /api/v1/tax/calculate/income-tax
- POST /api/v1/tax/calculate/vat
- POST /api/v1/tax/returns
- GET /api/v1/tax/returns
- GET /api/v1/tax/returns/:id
- GET /api/v1/tax/returns/:id/it11ga
- GET /api/v1/tax/returns/:id/mushak91
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from packages.trust_kernel.audit import audit_service
from packages.trust_kernel.db import db_manager
from packages.trust_kernel.tax_engine import TaxEngine
from services.api.app.routers.auth import get_current_user

router = APIRouter(prefix="/tax", tags=["tax"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class IncomeTaxCalcRequest(BaseModel):
    category: str = Field(default="general", description="Taxpayer category")
    location: str = Field(default="dhaka_chattogram_cc", description="Jurisdiction location")
    assessment_year: str = Field(default="2024-2025")
    income_salary: float = Field(default=0.0)
    income_interest: float = Field(default=0.0)
    income_house: float = Field(default=0.0)
    income_agriculture: float = Field(default=0.0)
    income_business: float = Field(default=0.0)
    income_capital_gain: float = Field(default=0.0)
    income_other: float = Field(default=0.0)
    actual_investment: float = Field(default=0.0)
    advance_tax_paid: float = Field(default=0.0)
    net_wealth: float = Field(default=0.0)


class VatCalcRequest(BaseModel):
    tax_period: str = Field(default="2026-10")
    standard_sales: float = Field(default=0.0)
    reduced_sales: float = Field(default=0.0)
    reduced_rate: float = Field(default=0.05)
    exempt_sales: float = Field(default=0.0)
    zero_rated_export: float = Field(default=0.0)
    input_purchases_standard: float = Field(default=0.0)
    vds_deducted_by_buyers: float = Field(default=0.0)
    vds_withheld_from_suppliers: float = Field(default=0.0)


class TaxReturnSaveRequest(BaseModel):
    return_type: str = Field(default="income_tax")  # 'income_tax' | 'vat'
    tax_period: str = Field(default="2024-2025")
    taxpayer_name: str
    taxpayer_tin: str | None = None
    case_id: str | None = None
    inputs: dict[str, Any]
    status: str = Field(default="draft")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.post("/calculate/income-tax")
async def calculate_income_tax(
    req: IncomeTaxCalcRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Calculates individual income tax breakdown deterministically."""
    result = TaxEngine.calculate_income_tax(req.model_dump())
    return result


@router.post("/calculate/vat")
async def calculate_vat(
    req: VatCalcRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Calculates monthly VAT breakdown deterministically."""
    result = TaxEngine.calculate_vat(req.model_dump())
    return result


@router.post("/returns")
async def save_tax_return(
    req: TaxReturnSaveRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Computes and saves a tax return dossier."""
    inputs = req.inputs
    if req.return_type == "income_tax":
        calc = TaxEngine.calculate_income_tax(inputs)
        statement = TaxEngine.generate_it11ga_statement(
            profile={
                "taxpayer_name": req.taxpayer_name,
                "tin": req.taxpayer_tin or "১২ সংখ্যার টিআইএন",
                **inputs,
            },
            calc_result=calc,
        )
    else:
        calc = TaxEngine.calculate_vat(inputs)
        filing_date = inputs.get("filing_date") or datetime.now(timezone.utc).strftime("%d/%m/%Y")
        filing_time = inputs.get("filing_time") or datetime.now(timezone.utc).strftime("%I:%M %p")
        statement = {
            "form_code": "Mushak-9.1",
            "form_name_bn": "মূসক-৯.১ মাসিক দাখিলপত্র",
            "taxpayer_name": req.taxpayer_name,
            "business_nature": inputs.get("business_nature", "ব্যবসা ও অর্থনৈতিক কার্যক্রম"),
            "bin": req.taxpayer_tin or inputs.get("bin", "৯ সংখ্যার বিন"),
            "tax_period": req.tax_period,
            "address": inputs.get("address", "বাণিজ্যিক কার্যালয়ের ঠিকানা"),
            "date": filing_date,
            "time": filing_time,
            "calculation": calc,
        }

    tax_return = db_manager.create_tax_return(
        user_id=current_user["id"],
        return_type=req.return_type,
        tax_period=req.tax_period,
        taxpayer_name=req.taxpayer_name,
        taxpayer_tin=req.taxpayer_tin,
        case_id=req.case_id,
        inputs=inputs,
        calculation=calc,
        statement=statement,
        status=req.status,
    )

    audit_service.log(
        actor_id=current_user["id"],
        actor_role=current_user.get("role", "citizen"),
        action="SAVE_TAX_RETURN",
        object_type="tax_return",
        object_id=tax_return["id"],
        meta={"return_type": req.return_type, "tax_period": req.tax_period},
    )

    return tax_return


@router.get("/returns")
async def list_tax_returns(
    return_type: str | None = Query(None),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Lists tax returns owned by the current user."""
    return db_manager.list_tax_returns(user_id=current_user["id"], return_type=return_type)


@router.get("/returns/{return_id}")
async def get_tax_return_detail(
    return_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieves a single tax return with ownership isolation."""
    item = db_manager.get_tax_return(return_id)
    if not item:
        raise HTTPException(status_code=404, detail="Tax return not found")
    if item["user_id"] != current_user["id"] and current_user.get("role") not in ("admin", "reviewer"):
        raise HTTPException(status_code=403, detail="Forbidden: Cross-tenant tax access denied")
    return item


@router.delete("/returns/{return_id}")
async def delete_tax_return(
    return_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Deletes a tax return with ownership check."""
    item = db_manager.get_tax_return(return_id)
    if not item:
        raise HTTPException(status_code=404, detail="Tax return not found")
    if item["user_id"] != current_user["id"] and current_user.get("role") not in ("admin", "reviewer"):
        raise HTTPException(status_code=403, detail="Forbidden: Cross-tenant tax deletion denied")
    db_manager.delete_tax_return(return_id)
    audit_service.log(
        actor_id=current_user["id"],
        actor_role=current_user.get("role", "citizen"),
        action="DELETE_TAX_RETURN",
        object_type="tax_return",
        object_id=return_id,
        meta={"return_id": return_id},
    )
    return {"status": "deleted", "id": return_id}


@router.get("/returns/{return_id}/it11ga")
async def get_it11ga_statement(
    return_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Gets Form IT-11GA structured return document."""
    item = await get_tax_return_detail(return_id, current_user=current_user)
    if item["return_type"] != "income_tax":
        raise HTTPException(status_code=400, detail="Return is not an income tax return")
    return item["statement"]


@router.get("/returns/{return_id}/mushak91")
async def get_mushak91_statement(
    return_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Gets Mushak-9.1 structured return document."""
    item = await get_tax_return_detail(return_id, current_user=current_user)
    if item["return_type"] != "vat":
        raise HTTPException(status_code=400, detail="Return is not a VAT return")
    return item["statement"]
