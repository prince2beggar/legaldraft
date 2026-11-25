"""
AIN-AI Core API Application Entrypoint
Unified FastAPI service adhering to SRS Section 2.1 & 2.2.
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# Add repository root to sys.path so packages.* and backend.* are resolvable
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Load environment configuration from .env file
from dotenv import load_dotenv  # noqa: E402

env_file = REPO_ROOT / ".env"
if env_file.exists():
    load_dotenv(dotenv_path=env_file)
else:
    load_dotenv()

# Legacy backend support
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from packages.trust_kernel.audit import audit_service
from packages.trust_kernel.i18n import i18n
from services.api.app.logging_config import logger
from services.api.app.routers.auth import (
    get_current_user,
)
from services.api.app.routers.auth import (
    router as auth_router,
)
from services.api.app.routers.cases import router as cases_router
from services.api.app.routers.documents import router as documents_router
from services.api.app.routers.drafts import router as drafts_router
from services.api.app.routers.evals import router as evals_router
from services.api.app.routers.health import router as health_router
from services.api.app.routers.intake import router as intake_router
from services.api.app.routers.knowledge import router as knowledge_router
from services.api.app.routers.library import router as library_router
from services.api.app.routers.rules import router as rules_router
from services.api.app.routers.sharing import router as sharing_router
from services.api.app.routers.tax import router as tax_router

app = FastAPI(
    title="AIN-AI (আইন-AI) API",
    description="Bangladesh Legal-Tech Platform - Trust Kernel, Drafting, Documents & Advisory",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# Security Headers Middleware
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    # Standard security headers (X-001, Hardening)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    path = request.url.path
    if path in ("/docs", "/redoc", "/openapi.json"):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https://fastapi.tiangolo.com; "
            "font-src 'self' data: https://cdn.jsdelivr.net; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
    else:
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
    # Cache control for shared links and sensitive routes (AC-M08-2)
    if (
        path.startswith("/s/")
        or path.startswith("/api/v1/s/")
        or "/consents" in path
        or path.startswith("/me/sharing")
    ):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
    return response


# CORS Middleware (H2 / S9 Hardening)
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000",
    ).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Audit & Logging Middleware
@app.middleware("http")
async def audit_and_logging_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "127.0.0.1"
    path = request.url.path
    method = request.method

    response = await call_next(request)

    # Log non-health state changes into audit service
    if method in ("POST", "PUT", "PATCH", "DELETE") and not path.startswith("/health"):
        actor_id = request.headers.get("x-user-id", "anonymous")
        actor_role = request.headers.get("x-user-role", "citizen")
        audit_service.log(
            actor_id=actor_id,
            actor_role=actor_role,
            action=f"{method} {path}",
            object_type="api_request",
            object_id=path,
            ip=client_ip,
            meta={"status_code": response.status_code},
        )

    logger.info(f"{method} {path} completed with status {response.status_code}")
    return response


# Include Health routes
app.include_router(health_router)
app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(library_router, prefix="/api/v1")
app.include_router(knowledge_router, prefix="/api/v1")
app.include_router(rules_router)
app.include_router(evals_router)
app.include_router(documents_router)
app.include_router(cases_router, prefix="/api/v1")
app.include_router(intake_router)
app.include_router(intake_router, prefix="/api/v1")
app.include_router(drafts_router)
app.include_router(drafts_router, prefix="/api/v1")
app.include_router(sharing_router)
app.include_router(tax_router, prefix="/api/v1")


# Mount i18n lookup endpoint
@app.get("/api/v1/i18n/{locale}")
def get_translations(locale: str = "bn"):
    """Returns frontend localization dictionary for requested locale."""
    return i18n.get_catalog(locale)


# Mount existing v1 API routes if available in backend
try:
    import backend.app.models as _legacy_models  # noqa: F401
    from backend.app.core.database import Base as LegacyBase
    from backend.app.core.database import engine as legacy_engine

    LegacyBase.metadata.create_all(bind=legacy_engine)

    from backend.app.api.v1 import api_router as legacy_v1_router

    # Guard ALL legacy API routes behind authentication (SRS X-001)
    app.include_router(
        legacy_v1_router,
        prefix="/api/v1",
        dependencies=[Depends(get_current_user)],
    )
    logger.info(
        "Successfully mounted legacy v1 API routers under /api/v1 (protected by get_current_user)"
    )
except Exception as e:  # noqa: BLE001
    logger.warning(f"Note on legacy API router mounting: {e!s}")

# Mount static web app if available
STATIC_DIR = REPO_ROOT / "backend" / "app" / "static"
SERVER_START_TIME = datetime.now(timezone.utc).isoformat()

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.middleware("http")
    async def block_mock_variants_in_prod(request: Request, call_next):
        from packages.trust_kernel.auth import is_dev_mode

        if not is_dev_mode():
            if request.query_params.get("variant") or request.query_params.get("mock"):
                from fastapi.responses import JSONResponse

                return JSONResponse(
                    status_code=404,
                    content={"detail": "Mock variants are disabled when DEV_MODE=false"},
                )
        return await call_next(request)

    @app.get("/signin")
    @app.get("/welcome")
    @app.get("/otp")
    @app.get("/onboarding")
    def serve_auth_page():
        import re

        from fastapi.responses import HTMLResponse

        from packages.trust_kernel.auth import is_dev_mode

        signin_file = STATIC_DIR / "signin.html"
        if signin_file.exists():
            content = signin_file.read_text(encoding="utf-8")
            if not is_dev_mode():
                # Strictly strip out demo login buttons in production / non-dev mode (Sprint S7 E5)
                content = re.sub(
                    r"<!-- DEV_MODE_START -->.*?<!-- DEV_MODE_END -->", "", content, flags=re.DOTALL
                )
            return HTMLResponse(content, status_code=200)
        return HTMLResponse("<h1>AIN-AI Sign In</h1>", status_code=200)

    def get_build_stamp() -> dict[str, str]:
        import hashlib
        import subprocess

        git_commit = "87fe026"
        is_dirty = False
        try:
            res = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT),
            )
            if res.returncode == 0 and res.stdout.strip():
                git_commit = res.stdout.strip()
            status_res = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=str(REPO_ROOT),
            )
            if status_res.returncode == 0 and status_res.stdout.strip():
                is_dirty = True
        except Exception:
            pass

        git_hash = f"{git_commit}-dirty" if is_dirty else git_commit

        static_hash = "00000000"
        try:
            hasher = hashlib.sha256()
            for p in sorted(STATIC_DIR.rglob("*")):
                if p.is_file():
                    hasher.update(p.name.encode("utf-8"))
                    hasher.update(p.read_bytes())
            static_hash = hasher.hexdigest()[:8]
        except Exception:
            pass

        build_id = f"{git_hash}+{static_hash}"
        return {
            "version": "2.0.0",
            "build_id": build_id,
            "git_hash": git_hash,
            "static_hash": static_hash,
        }

    @app.get("/api/v1/build")
    def get_build_info():
        from packages.trust_kernel.auth import is_dev_mode

        info = get_build_stamp()
        if os.getenv("DEMO_MODE", "").lower() in ("true", "1"):
            mode = "demo"
        elif is_dev_mode():
            mode = "dev"
        else:
            mode = "prod"

        return {
            "version": info["version"],
            "build_id": info["build_id"],
            "git_hash": info["git_hash"],
            "static_hash": info["static_hash"],
            "started_at": SERVER_START_TIME,
            "mode": mode,
        }

    @app.get("/sw.js")
    def serve_sw():
        from fastapi.responses import Response

        from packages.trust_kernel.auth import is_dev_mode

        info = get_build_stamp()
        if is_dev_mode():
            content = (
                f"// Service Worker disabled when DEV_MODE=true\n"
                f"// Build ID: {info['build_id']}\n"
                f"self.addEventListener('install', () => self.skipWaiting());\n"
                f"self.addEventListener('activate', () => self.clients.claim());\n"
            )
            return Response(
                content=content,
                media_type="application/javascript",
                headers={
                    "Service-Worker-Allowed": "/",
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                },
            )
        sw_path = STATIC_DIR / "sw.js"
        if sw_path.exists():
            content = sw_path.read_text(encoding="utf-8")
            content = content.replace("__DYNAMIC_BUILD_ID__", info["build_id"])
            return Response(
                content=content,
                media_type="application/javascript",
                headers={
                    "Service-Worker-Allowed": "/",
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                },
            )
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="sw.js not found")

    @app.get("/")
    def serve_index(
        request: Request,
        lang: str = "bn",
        accept_language: str | None = Header(default=None),
        authorization: str | None = Header(default=None),
    ):
        import re

        from fastapi.responses import HTMLResponse

        home_file = STATIC_DIR / "home.html"
        content = home_file.read_text(encoding="utf-8")
        if lang == "en":
            content = content.replace('<html lang="bn">', '<html lang="en">')
            content = content.replace(
                "<title>আইন-AI — হোম ও পরবর্তী পদক্ষেপ</title>",
                "<title>AIN-AI — Home & Next Action (English)</title>",
            )
        is_demo = os.getenv("DEMO_MODE", "").lower() in ("true", "1")
        if is_demo and "demoModeBanner" not in content:
            demo_banner = '<div id="demoModeBanner" style="background:#fef3c7; color:#92400e; border-bottom:1px solid #f59e0b; padding:8px 16px; text-align:center; font-weight:700; font-size:13px; position:sticky; top:0; z-index:9999; width:100%; box-sizing:border-box; white-space:nowrap; flex-shrink:0;">⚠️ ডেমো ডেটা — নমুনা (Demo Mode)</div>'
            content = content.replace("<body>", f"<body>\n{demo_banner}")

        is_dev = os.getenv("DEV_MODE", "false").lower() in ("true", "1") or is_demo
        info = get_build_stamp()
        stamp_str = (
            f"build: {info['git_hash']} | static: {info['static_hash']} | id: {info['build_id']}"
        )
        if is_dev:
            content = re.sub(
                r'<div class="build-stamp"[^>]*>.*?</div>',
                f'<div class="build-stamp" id="buildStamp" style="font-size:11px; color:#94a3b8; text-align:center; padding:12px 0; pointer-events:none;">{stamp_str}</div>',
                content,
            )
        else:
            content = re.sub(
                r'<div class="build-stamp"[^>]*>.*?</div>',
                '<div class="build-stamp" id="buildStamp" style="display:none;"></div>',
                content,
            )
        return HTMLResponse(content=content, status_code=200)

    def _require_auth_page(
        request: Request, authorization: str | None, page_name: str, fallback_title: str
    ):
        import re

        from fastapi.responses import HTMLResponse

        target_file = STATIC_DIR / page_name
        if target_file.exists():
            content = target_file.read_text(encoding="utf-8")
        else:
            content = f"<h1>{fallback_title}</h1>"

        is_demo = os.getenv("DEMO_MODE", "").lower() in ("true", "1")
        if is_demo and "demoModeBanner" not in content:
            demo_banner = '<div id="demoModeBanner" style="background:#fef3c7; color:#92400e; border-bottom:1px solid #f59e0b; padding:8px 16px; text-align:center; font-weight:700; font-size:13px; position:sticky; top:0; z-index:9999; width:100%; box-sizing:border-box; white-space:nowrap; flex-shrink:0;">⚠️ ডেমো ডেটা — নমুনা (Demo Mode)</div>'
            content = content.replace("<body>", f"<body>\n{demo_banner}")

        is_dev = os.getenv("DEV_MODE", "false").lower() in ("true", "1") or is_demo
        info = get_build_stamp()
        stamp_str = (
            f"build: {info['git_hash']} | static: {info['static_hash']} | id: {info['build_id']}"
        )
        if is_dev:
            content = re.sub(
                r'<div class="build-stamp"[^>]*>.*?</div>',
                f'<div class="build-stamp" id="buildStamp" style="font-size:11px; color:#94a3b8; text-align:center; padding:12px 0; pointer-events:none;">{stamp_str}</div>',
                content,
            )
        else:
            content = re.sub(
                r'<div class="build-stamp"[^>]*>.*?</div>',
                '<div class="build-stamp" id="buildStamp" style="display:none;"></div>',
                content,
            )

        return HTMLResponse(content=content, status_code=200)

    @app.get("/admin", response_class=HTMLResponse)
    def serve_admin(
        request: Request,
        authorization: str | None = Header(default=None),
    ):
        return _require_auth_page(request, authorization, "admin.html", "AIN-AI Admin Portal")

    @app.get("/admin/legacy-ingest", response_class=HTMLResponse)
    def serve_legacy_ingest(
        request: Request,
        authorization: str | None = Header(default=None),
    ):
        from packages.trust_kernel.auth import is_dev_mode
        if not is_dev_mode():
            raise HTTPException(status_code=404, detail="Not Found")
        return _require_auth_page(
            request, authorization, "legacy_ingest.html", "AIN-AI Legacy Ingest (DEV ONLY)"
        )

    @app.get("/library")
    def serve_library(
        request: Request,
        authorization: str | None = Header(default=None),
    ):
        return _require_auth_page(request, authorization, "library.html", "AIN-AI Citizen Library")

    @app.get("/admin/sources")
    def serve_admin_sources(
        request: Request,
        authorization: str | None = Header(default=None),
    ):
        return _require_auth_page(
            request, authorization, "admin_sources.html", "AIN-AI Admin Knowledge Center"
        )

    @app.get("/home", response_class=HTMLResponse)
    def serve_home(request: Request, authorization: str | None = Header(default=None)):
        return _require_auth_page(request, authorization, "home.html", "AIN-AI Citizen Home")

    @app.get("/cases", response_class=HTMLResponse)
    @app.get("/cases/new", response_class=HTMLResponse)
    def serve_cases(request: Request, authorization: str | None = Header(default=None)):
        return _require_auth_page(request, authorization, "cases.html", "AIN-AI Case Folders")

    @app.get("/cases/{case_id}", response_class=HTMLResponse)
    def serve_case_detail(
        case_id: str, request: Request, authorization: str | None = Header(default=None)
    ):
        return _require_auth_page(
            request, authorization, "case_detail.html", f"AIN-AI Case Detail: {case_id}"
        )

    @app.get("/notifications", response_class=HTMLResponse)
    def serve_notifications(request: Request, authorization: str | None = Header(default=None)):
        return _require_auth_page(
            request, authorization, "notifications.html", "AIN-AI Notifications"
        )

    @app.get("/notification-settings", response_class=HTMLResponse)
    def serve_notification_settings(
        request: Request, authorization: str | None = Header(default=None)
    ):
        return _require_auth_page(
            request, authorization, "notification_settings.html", "AIN-AI Notification Settings"
        )

    @app.get("/intake", response_class=HTMLResponse)
    def serve_intake(request: Request, authorization: str | None = Header(default=None)):
        return _require_auth_page(request, authorization, "intake.html", "AIN-AI Citizen Intake")

    @app.get("/draft", response_class=HTMLResponse)
    @app.get("/draft/{draft_id}", response_class=HTMLResponse)
    @app.get("/draft/{draft_id}/q/{step}", response_class=HTMLResponse)
    @app.get("/draft/{draft_id}/check", response_class=HTMLResponse)
    @app.get("/draft/{draft_id}/preview", response_class=HTMLResponse)
    @app.get("/draft/{draft_id}/export", response_class=HTMLResponse)
    def serve_draft(request: Request, authorization: str | None = Header(default=None)):
        return _require_auth_page(request, authorization, "draft.html", "AIN-AI Guided Drafting")

    @app.get("/tax", response_class=HTMLResponse)
    def serve_tax(request: Request, authorization: str | None = Header(default=None)):
        return _require_auth_page(request, authorization, "tax.html", "AIN-AI Tax & VAT Workspace")

    @app.get("/admin/emergency-contacts", response_class=HTMLResponse)
    def serve_admin_emergency_contacts(
        request: Request, authorization: str | None = Header(default=None)
    ):
        return _require_auth_page(
            request,
            authorization,
            "admin_emergency_contacts.html",
            "AIN-AI Admin Emergency Contacts",
        )

    @app.get("/admin/templates", response_class=HTMLResponse)
    def serve_admin_templates(request: Request, authorization: str | None = Header(default=None)):
        return _require_auth_page(
            request, authorization, "admin_templates.html", "AIN-AI Admin Templates"
        )

    @app.get("/cases/{case_id}/brief", response_class=HTMLResponse)
    @app.get("/cases/{case_id}/lawyer", response_class=HTMLResponse)
    def serve_case_lawyer_brief(
        case_id: str, request: Request, authorization: str | None = Header(default=None)
    ):
        return _require_auth_page(
            request, authorization, "case_brief.html", f"AIN-AI Case Brief: {case_id}"
        )

    @app.get("/me/sharing", response_class=HTMLResponse)
    def serve_me_sharing(request: Request, authorization: str | None = Header(default=None)):
        return _require_auth_page(
            request, authorization, "sharing.html", "AIN-AI Sharing Management"
        )

    @app.get("/admin/system", response_class=HTMLResponse)
    def serve_admin_system(request: Request, authorization: str | None = Header(default=None)):
        return _require_auth_page(
            request, authorization, "admin_system.html", "AIN-AI System Observability"
        )
