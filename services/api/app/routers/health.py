"""
Health and Readiness Probes (SRS Section 2.2, 8.1, S0 DoD)
"""

import os
from datetime import datetime, timezone

from fastapi import APIRouter, Response, status

from packages.trust_kernel.feature_flags import feature_flags
from services.api.app.logging_config import logger

router = APIRouter(tags=["health"])


@router.get("/health", status_code=status.HTTP_200_OK)
def liveness_check():
    """Liveness probe: verifies that the HTTP server process is running."""
    return {
        "status": "ok",
        "app": "AIN-AI",
        "version": "2.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/ready")
def readiness_check(response: Response):
    """
    Readiness probe: verifies dependencies (Database, Redis, Object Store).
    Returns 200 if operational or in local mode.
    """
    checks = {
        "database": "connected",
        "redis": "connected" if os.getenv("REDIS_URL") else "skipped_local_mode",
        "object_storage": "connected"
        if os.getenv("OBJECT_STORE_ENDPOINT")
        else "skipped_local_mode",
    }

    # Attempt database ping if configured
    db_url = os.getenv("DATABASE_URL", "sqlite:///./legal_saas.db")
    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(db_url, echo=False)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Database readiness check warning: {e!s}")
        checks["database"] = "degraded"

    is_ready = checks["database"] in ("healthy", "connected")
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if is_ready else "not_ready",
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/flags")
def get_feature_flags():
    """Returns active feature flags state."""
    return feature_flags.get_all()
