"""
Rules Engine API Router & Admin UI (SRS Section 4.3, 8.3, 9.3 S3).
Provides endpoints to list registered rules, execute calculations deterministically,
run test suites, and serve the admin rules inspection UI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from packages.trust_kernel.db import db_manager
from packages.trust_kernel.rules_engine import rules_engine
from services.api.app.routers.auth import get_current_user

router = APIRouter(tags=["Rules Engine"])

STATIC_DIR = Path(__file__).resolve().parents[4] / "backend" / "app" / "static"


def require_reviewer_or_admin(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    role = user.get("role", "citizen")
    roles = user.get("roles", [role])
    if "admin" not in roles and "reviewer" not in roles and role not in ("admin", "reviewer"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden. Admin or reviewer role required.",
        )
    return user


class ComputeRuleRequest(BaseModel):
    rule_id: str = Field(
        ..., description="ID of the registered rule, e.g. relative_period.calendar_days.v1"
    )
    inputs: dict[str, Any] = Field(..., description="Input parameters matching rule schema")


class RunRuleTestsRequest(BaseModel):
    rule_id: str = Field(..., description="ID of the registered rule")
    version: str = Field(default="1.0.0", description="Rule version")


@router.get("/api/v1/rules")
def list_rules() -> dict[str, Any]:
    """Lists all registered legal rules and their active versions."""
    rules = db_manager.list_rules()
    data = []
    for r in rules:
        versions = db_manager.list_rule_versions(r["id"])
        data.append({**r, "versions": versions})
    return {"rules": data, "count": len(data)}


@router.post("/api/v1/rules/compute")
def compute_rule(req: ComputeRuleRequest) -> dict[str, Any]:
    """Executes a rule deterministically and returns the reasoned result."""
    try:
        result = rules_engine.compute(req.rule_id, req.inputs)
        return {"status": "success", "result": result}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/api/v1/rules/test")
def run_rule_tests(req: RunRuleTestsRequest) -> dict[str, Any]:
    """Runs all test cases for the specified rule and version."""
    results = rules_engine.run_rule_tests(req.rule_id, req.version)
    passed_count = sum(1 for r in results if r["passed"])
    return {
        "rule_id": req.rule_id,
        "version": req.version,
        "total_tests": len(results),
        "passed_tests": passed_count,
        "failed_tests": len(results) - passed_count,
        "results": results,
    }


@router.get("/admin/rules", response_class=HTMLResponse)
def get_admin_rules_page() -> HTMLResponse:
    """Serves the Admin Rules Engine & Test Runner interface."""
    html_file = STATIC_DIR / "admin_rules.html"
    if not html_file.exists():
        raise HTTPException(status_code=404, detail="admin_rules.html not found")
    return HTMLResponse(content=html_file.read_text(encoding="utf-8"))
