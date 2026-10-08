"""
Evaluation Harness API Router & Admin UI (SRS Section 8.7, 9.3 S3).
Provides endpoints to list golden evaluation suites, trigger test runs,
review metrics, and serve the admin evaluations dashboard.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from packages.trust_kernel.db import db_manager
from packages.trust_kernel.eval_harness import eval_harness
from services.api.app.routers.auth import get_current_user

router = APIRouter(tags=["Evaluation Harness"])

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


class RunEvaluationRequest(BaseModel):
    suite_name: str = Field(..., description="Name of the golden evaluation suite")
    gate_threshold: float = Field(
        default=0.80, description="Minimum accuracy rate required to pass the gate (0.0 to 1.0)"
    )


@router.get("/api/v1/evals/golden-sets")
def list_golden_sets(
    user: dict[str, Any] = Depends(require_reviewer_or_admin),
) -> dict[str, Any]:
    """Lists all registered golden evaluation test sets."""
    suites = eval_harness.list_suites()
    return {
        "golden_sets": [
            {
                "suite_name": s,
                "label": "FAKE_TEST_DATA",
                "case_count": len(eval_harness.golden_suites.get(s, [])),
            }
            for s in suites
        ]
    }


@router.post("/api/v1/evals/run")
def trigger_eval_run(
    req: RunEvaluationRequest,
    user: dict[str, Any] = Depends(require_reviewer_or_admin),
) -> dict[str, Any]:
    """Executes a golden evaluation suite and evaluates quality gates."""
    try:
        run_result = eval_harness.run_suite(req.suite_name, req.gate_threshold)
        return {"status": "success", "run": run_result}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/api/v1/evals/runs")
def list_past_eval_runs(
    user: dict[str, Any] = Depends(require_reviewer_or_admin),
) -> dict[str, Any]:
    """Retrieves list of past evaluation runs."""
    runs = db_manager.list_eval_runs()
    return {"runs": runs, "count": len(runs)}


@router.get("/api/v1/evals/runs/{run_id}")
def get_eval_run_detail(
    run_id: str,
    user: dict[str, Any] = Depends(require_reviewer_or_admin),
) -> dict[str, Any]:
    """Retrieves full details and case-level results of an evaluation run."""
    run = db_manager.get_eval_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Eval run '{run_id}' not found.")
    cases = db_manager.list_eval_results(run_id)
    return {"run": run, "cases": cases}


@router.get("/admin/evals", response_class=HTMLResponse)
def get_admin_evals_page() -> HTMLResponse:
    """Serves the Admin Evaluation Dashboard."""
    html_file = STATIC_DIR / "admin_evals.html"
    if not html_file.exists():
        raise HTTPException(status_code=404, detail="admin_evals.html not found")
    return HTMLResponse(content=html_file.read_text(encoding="utf-8"))
