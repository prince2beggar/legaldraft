"""
AIN-AI Core API Application Entrypoint
Unified FastAPI service adhering to SRS Section 2.1 & 2.2.
"""

import sys
from pathlib import Path

from fastapi import Depends, FastAPI, Header, Request
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
    get_current_user_optional,
)
from services.api.app.routers.auth import (
    router as auth_router,
)
from services.api.app.routers.cases import router as cases_router
from services.api.app.routers.documents import router as documents_router
from services.api.app.routers.evals import router as evals_router
from services.api.app.routers.health import router as health_router
from services.api.app.routers.knowledge import router as knowledge_router
from services.api.app.routers.library import router as library_router
from services.api.app.routers.rules import router as rules_router

app = FastAPI(
    title="AIN-AI (আইন-AI) API",
    description="Bangladesh Legal-Tech Platform - Trust Kernel, Drafting, Documents & Advisory",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
app.include_router(auth_router)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(library_router, prefix="/api/v1")
app.include_router(knowledge_router, prefix="/api/v1")
app.include_router(rules_router)
app.include_router(evals_router)
app.include_router(documents_router)
app.include_router(cases_router, prefix="/api/v1")


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
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/signin")
    @app.get("/welcome")
    @app.get("/otp")
    @app.get("/onboarding")
    def serve_auth_page():
        from fastapi.responses import HTMLResponse

        signin_file = STATIC_DIR / "signin.html"
        if signin_file.exists():
            return HTMLResponse(signin_file.read_text(encoding="utf-8"), status_code=200)
        return HTMLResponse("<h1>AIN-AI Sign In</h1>", status_code=200)

    @app.get("/")
    def serve_index(
        request: Request,
        lang: str = "bn",
        accept_language: str | None = Header(default=None),
        authorization: str | None = Header(default=None),
    ):
        from fastapi import HTTPException, status
        from fastapi.responses import HTMLResponse

        user = get_current_user_optional(request, authorization)
        if not user:
            accept = request.headers.get("accept", "")
            if "text/html" not in accept:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required. Please sign in via OTP.",
                )

            # Browser navigation: return 401 with HTML auto-redirect to /signin
            html_redirect = """<!DOCTYPE html>
<html lang="bn">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="0; url=/signin">
  <title>আইন-AI — প্রবেশ প্রয়োজন</title>
  <style>
    body { font-family: system-ui, -apple-system, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; background: #f8fafc; }
    .card { background: white; padding: 2.5rem; border-radius: 1rem; box-shadow: 0 10px 25px rgba(0,0,0,0.06); text-align: center; max-width: 440px; border: 1px solid #e2e8f0; }
    .icon { font-size: 3rem; margin-bottom: 0.5rem; }
    h2 { margin: 0.5rem 0; color: #0f172a; font-size: 1.25rem; font-weight: 700; }
    p { color: #64748b; font-size: 0.9rem; line-height: 1.5; margin: 0.75rem 0; }
    .btn { display: inline-block; margin-top: 1rem; padding: 0.75rem 1.5rem; background: #047857; color: white; text-decoration: none; border-radius: 0.75rem; font-weight: 600; font-size: 0.875rem; }
  </style>
</head>
<body>
  <div class="card">
    <div class="icon">⚖️</div>
    <h2>আইন-AI (AIN-AI)</h2>
    <p>অ্যাডভোকেট ড্যাশবোর্ড সুরক্ষার জন্য <strong>প্রবেশ বা অনবোর্ডিং</strong> বাধ্যতামূলক।</p>
    <p>আপনাকে সাইন-ইন পেজে নিয়ে যাওয়া হচ্ছে...</p>
    <a href="/signin" class="btn">লগইন বা অনবোর্ডিং করুন</a>
  </div>
  <script>
    window.location.replace('/signin');
  </script>
</body>
</html>"""
            return HTMLResponse(content=html_redirect, status_code=status.HTTP_401_UNAUTHORIZED)

        preferred = (
            "en"
            if (
                lang == "en"
                or (
                    accept_language
                    and "en" in accept_language.lower()
                    and "bn" not in accept_language.lower()
                )
            )
            else "bn"
        )
        index_file = STATIC_DIR / "index.html"
        content = index_file.read_text(encoding="utf-8")
        if preferred == "en":
            content = content.replace('<html lang="bn">', '<html lang="en">')
            content = content.replace(
                "<title>Bangladesh Legal Intelligence & Operations SaaS</title>",
                "<title>AIN-AI — Bangladesh Legal Intelligence & Operations SaaS (English)</title>",
            )
        return HTMLResponse(content=content, status_code=200)

    @app.get("/admin")
    def serve_admin(
        request: Request,
        authorization: str | None = Header(default=None),
    ):
        from fastapi import HTTPException, status
        from fastapi.responses import FileResponse, HTMLResponse

        user = get_current_user_optional(request, authorization)
        if not user:
            accept = request.headers.get("accept", "")
            if "text/html" not in accept:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required. Please sign in via OTP.",
                )
            html_redirect = """<!DOCTYPE html>
<html lang="bn">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="0; url=/signin">
  <title>অ্যাডমিন প্রবেশ প্রয়োজন — AIN-AI</title>
</head>
<body style="font-family: sans-serif; text-align: center; padding: 40px; background: #f8fafc;">
  <h2>🔒 অ্যাডমিন প্যানেল — প্রমাণীকরণ প্রয়োজন</h2>
  <p>অ্যাডমিন প্যানেলে প্রবেশের জন্য অনুগ্রহ করে সাইন-ইন করুন।</p>
  <p><a href="/signin" style="display:inline-block; padding:10px 20px; background:#047857; color:#fff; text-decoration:none; border-radius:8px;">লগইন করুন</a></p>
  <script>window.location.replace('/signin');</script>
</body>
</html>"""
            return HTMLResponse(content=html_redirect, status_code=status.HTTP_401_UNAUTHORIZED)

        if user.get("role") not in ("admin", "reviewer"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden. Admin or reviewer role required.",
            )
        return FileResponse(str(STATIC_DIR / "admin.html"))

    @app.get("/library")
    def serve_library(
        request: Request,
        authorization: str | None = Header(default=None),
    ):
        from fastapi import HTTPException, status
        from fastapi.responses import FileResponse, HTMLResponse

        user = get_current_user_optional(request, authorization)
        if not user:
            accept = request.headers.get("accept", "")
            if "text/html" not in accept:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required. Please sign in via OTP.",
                )
            html_redirect = """<!DOCTYPE html>
<html lang="bn">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="0; url=/signin">
  <title>আইন পাঠাগার — প্রবেশ প্রয়োজন</title>
</head>
<body style="font-family: sans-serif; text-align: center; padding: 40px; background: #f8fafc;">
  <h2>🔒 আইন পাঠাগার — সাইন ইন প্রয়োজন</h2>
  <p>আইন পাঠাগার ব্যবহারের জন্য অনুগ্রহ করে সাইন-ইন করুন।</p>
  <p><a href="/signin" style="display:inline-block; padding:10px 20px; background:#0B5D4B; color:#fff; text-decoration:none; border-radius:8px;">সাইন ইন করুন</a></p>
  <script>window.location.replace('/signin');</script>
</body>
</html>"""
            return HTMLResponse(content=html_redirect, status_code=status.HTTP_401_UNAUTHORIZED)

        library_file = STATIC_DIR / "library.html"
        if library_file.exists():
            return FileResponse(str(library_file))
        return HTMLResponse("<h1>AIN-AI Citizen Library</h1>", status_code=200)

    @app.get("/admin/sources")
    def serve_admin_sources(
        request: Request,
        authorization: str | None = Header(default=None),
    ):
        from fastapi import HTTPException, status
        from fastapi.responses import FileResponse, HTMLResponse

        user = get_current_user_optional(request, authorization)
        if not user:
            accept = request.headers.get("accept", "")
            if "text/html" not in accept:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required. Please sign in via OTP.",
                )
            html_redirect = """<!DOCTYPE html>
<html lang="bn">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="0; url=/signin">
  <title>অ্যাডমিন প্রবেশ প্রয়োজন</title>
</head>
<body style="font-family: sans-serif; text-align: center; padding: 40px; background: #f8fafc;">
  <h2>🔒 নলেজ সেন্টার — প্রমাণীকরণ প্রয়োজন</h2>
  <p>অ্যাডমিন নলেজ সেন্টারে প্রবেশের জন্য অনুগ্রহ করে সাইন-ইন করুন।</p>
  <p><a href="/signin" style="display:inline-block; padding:10px 20px; background:#0B5D4B; color:#fff; text-decoration:none; border-radius:8px;">লগইন করুন</a></p>
  <script>window.location.replace('/signin');</script>
</body>
</html>"""
            return HTMLResponse(content=html_redirect, status_code=status.HTTP_401_UNAUTHORIZED)

        if user.get("role") not in ("admin", "reviewer"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden. Admin or reviewer role required.",
            )
        admin_sources_file = STATIC_DIR / "admin_sources.html"
        if admin_sources_file.exists():
            return FileResponse(str(admin_sources_file))
        return HTMLResponse("<h1>AIN-AI Admin Knowledge Center</h1>", status_code=200)

    def _require_auth_page(request: Request, authorization: str | None, page_name: str, fallback_title: str):
        from fastapi import HTTPException, status
        from fastapi.responses import HTMLResponse

        user = get_current_user_optional(request, authorization)
        if not user:
            accept = request.headers.get("accept", "")
            if "text/html" not in accept:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required. Please sign in via OTP.",
                )
            html_redirect = """<!DOCTYPE html>
<html lang="bn">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="0; url=/signin">
  <title>আইন-AI — প্রমাণীকরণ প্রয়োজন</title>
</head>
<body style="font-family: sans-serif; text-align: center; padding: 40px; background: #f8fafc;">
  <h2>🔒 প্রমাণীকরণ প্রয়োজন</h2>
  <p>এই পেজে প্রবেশের জন্য অনুগ্রহ করে সাইন-ইন করুন।</p>
  <p><a href="/signin" style="display:inline-block; padding:10px 20px; background:#0B5D4B; color:#fff; text-decoration:none; border-radius:8px;">সাইন ইন করুন</a></p>
  <script>window.location.replace('/signin');</script>
</body>
</html>"""
            return HTMLResponse(content=html_redirect, status_code=status.HTTP_401_UNAUTHORIZED)
        target_file = STATIC_DIR / page_name
        if target_file.exists():
            return HTMLResponse(target_file.read_text(encoding="utf-8"), status_code=200)
        return HTMLResponse(f"<h1>{fallback_title}</h1>", status_code=200)

    @app.get("/home", response_class=HTMLResponse)
    def serve_home(request: Request, authorization: str | None = Header(default=None)):
        return _require_auth_page(request, authorization, "home.html", "AIN-AI Citizen Home")

    @app.get("/cases", response_class=HTMLResponse)
    @app.get("/cases/new", response_class=HTMLResponse)
    def serve_cases(request: Request, authorization: str | None = Header(default=None)):
        return _require_auth_page(request, authorization, "cases.html", "AIN-AI Case Folders")

    @app.get("/cases/{case_id}", response_class=HTMLResponse)
    def serve_case_detail(case_id: str, request: Request, authorization: str | None = Header(default=None)):
        return _require_auth_page(request, authorization, "case_detail.html", f"AIN-AI Case Detail: {case_id}")

    @app.get("/notifications", response_class=HTMLResponse)
    def serve_notifications(request: Request, authorization: str | None = Header(default=None)):
        return _require_auth_page(request, authorization, "notifications.html", "AIN-AI Notifications")

    @app.get("/notification-settings", response_class=HTMLResponse)
    def serve_notification_settings(request: Request, authorization: str | None = Header(default=None)):
        return _require_auth_page(request, authorization, "notification_settings.html", "AIN-AI Notification Settings")
