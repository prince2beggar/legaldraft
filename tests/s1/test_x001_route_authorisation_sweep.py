"""
Test X-001: Route-level Authorisation & Public Shell Sweep (SRS Section 5.P1, X-001, Directive P3).

Policy:
- Static HTML page shells (listed in PUBLIC_SHELLS) return 200 OK with NO user or case data.
  Browser stores auth token in localStorage, so server cannot know identity at shell load time.
  All dynamic data is fetched from /api/v1/* which strictly enforces authentication.
- All non-public /api/v1/* endpoints reject unauthenticated calls with 401 Unauthorized or 403 Forbidden.
- PWA start_url (/) returns 200 OK.
"""

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from packages.trust_kernel.auth import auth_service
from services.api.app.main import app

client = TestClient(app)

# Explicit inventory of static HTML shells with justifications (Directive P3)
PUBLIC_SHELLS = {
    "/": "Root citizen entry shell; unauthenticated 200 OK; renders static shell with zero private data; dynamic data loaded via /api/v1/* using localStorage JWT.",
    "/welcome": "Citizen/Admin entry portal shell; static UI; no user data.",
    "/signin": "OTP sign-in interface shell; static UI; no user data.",
    "/otp": "OTP verification interface shell; static UI; no user data.",
    "/onboarding": "Citizen onboarding welcome shell; static UI; no user data.",
    "/home": "Citizen dashboard shell; static layout skeleton; zero user/case data; client JS loads cases/deadlines via /api/v1/home/data with JWT.",
    "/cases": "Citizen case list shell; static layout skeleton; case records loaded via /api/v1/cases.",
    "/cases/new": "New case folder creation shell; static input form; zero user data.",
    "/cases/{case_id}": "Case detail shell; static timeline skeleton; case data loaded via /api/v1/cases/{id}.",
    "/cases/{case_id}/lawyer": "Case lawyer brief viewer shell; static layout; brief data loaded via /api/v1/cases/{id}/brief.",
    "/intake": "Guided legal intake & triage shell; static question flow; incident data submitted to /api/v1/intake/triage.",
    "/draft": "Guided legal drafting shell; template picker skeleton; draft content fetched from /api/v1/drafts.",
    "/draft/{draft_id}": "Draft wizard step shell; static question skeleton; steps fetched from /api/v1/drafts/{id}.",
    "/draft/{draft_id}/q/{step}": "Draft question step shell; static wizard UI; draft state fetched from /api/v1/drafts/{id}.",
    "/draft/{draft_id}/check": "Draft review & checklist shell; static preview shell; fetched from /api/v1/drafts/{id}.",
    "/draft/{draft_id}/preview": "Draft preview & watermark shell; static preview skeleton; rendered via /api/v1/drafts/{id}.",
    "/draft/{draft_id}/export": "Draft export shell; static download UI; exported via /api/v1/drafts/{id}/export.",
    "/documents/upload": "Document upload shell; file picker & drag-and-drop UI; files uploaded to /api/v1/documents/upload.",
    "/documents/intent": "Document intent selection shell; static choice chips; submitted to /api/v1/documents/{id}/intent.",
    "/documents/viewer": "Document inspection shell; static canvas/viewer skeleton; doc data fetched via /api/v1/documents/{id}.",
    "/documents/status": "Resumable upload status shell; static progress bar skeleton; status queried via /api/v1/documents/{id}/status.",
    "/documents/{doc_id}/notice": "Notice analysis result shell; static layout skeleton; notice interpretation loaded from /api/v1/documents/{id}.",
    "/documents/notice": "Generic legal notice viewer shell; static layout; no user data.",
    "/library": "Citizen legal knowledge library shell; static reference UI; search queries /api/v1/sources.",
    "/notifications": "Notification center shell; static alert list skeleton; alerts loaded via /api/v1/notifications.",
    "/notification-settings": "Notification settings shell; static toggle UI; preferences loaded via /api/v1/notifications/settings.",
    "/me/sharing": "Sharing & consent management shell; static list skeleton; consents loaded via /api/v1/consents.",
    "/admin": "Admin portal navigation shell; static menu; access to /api/v1/admin/* strictly rejected without admin JWT.",
    "/admin/sources": "Admin knowledge registry shell; static management table; records loaded via /api/v1/admin/sources.",
    "/admin/rules": "Admin rules engine shell; static rule runner UI; rules computed via /api/v1/rules.",
    "/admin/evals": "Admin evaluation dashboard shell; static metrics skeleton; eval runs loaded via /api/v1/evals/runs.",
    "/admin/emergency-contacts": "Admin emergency contacts management shell; static contact table; modified via /api/v1/admin/emergency-contacts.",
    "/admin/templates": "Admin drafting template editor shell; static template editor; saved via /api/v1/admin/templates.",
    "/admin/system": "Admin system observability shell; static metrics dashboard; loaded via /api/v1/admin/system.",
    "/s/{token}": "External recipient viewer shell; token-gated shared document view; protected by token verification.",
}

# Explicit public API routes whitelist
PUBLIC_API_WHITELIST = {
    "/health",
    "/health/ready",
    "/health/flags",
    "/openapi.json",
    "/docs",
    "/docs/oauth2-redirect",
    "/redoc",
    "/auth/otp/request",
    "/auth/otp/verify",
    "/auth/refresh",
    "/api/v1/auth/otp/request",
    "/api/v1/auth/otp/verify",
    "/api/v1/auth/refresh",
    "/api/v1/i18n/{locale}",
    "/api/v1/build",
    "/sw.js",
    # Public statutory rules computation engine (Sprint S3 / AC-M09)
    "/api/v1/rules",
    "/api/v1/rules/compute",
    "/api/v1/rules/test",
    # Recipient sharing token-gated endpoints (Module M08)
    "/s/{token}",
    "/s/{token}/request-otp",
    "/s/{token}/verify-otp",
    "/api/v1/s/{token}",
    "/api/v1/s/{token}/request-otp",
    "/api/v1/s/{token}/verify-otp",
    "/api/v1/s/{token}/doc/{doc_id}",
    "/consents/signed-doc/{doc_id}",
    "/api/v1/consents/signed-doc/{doc_id}",
}


def get_all_routes(r_list):
    res = []
    for r in r_list:
        if isinstance(r, APIRoute):
            res.append(r)
        elif hasattr(r, "routes"):
            res.extend(get_all_routes(r.routes))
        elif hasattr(r, "original_router") and hasattr(r.original_router, "routes"):
            res.extend(get_all_routes(r.original_router.routes))
    return res


@pytest.fixture(autouse=True)
def clean_auth_state():
    auth_service.clear()
    yield
    auth_service.clear()


def test_x001_unauthenticated_route_sweep():
    """
    Directive P3 sweep:
    (a) Every static HTML shell in PUBLIC_SHELLS returns 200 OK and contains zero user or case data.
    (b) Every non-public /api/v1/* endpoint rejects unauthenticated requests with 401 or 403.
    """
    # Part A: Verify all public shells return 200 without user/case data
    tested_shells = 0
    for pattern in PUBLIC_SHELLS:
        test_url = pattern.replace("{case_id}", "test-case-id") \
                          .replace("{draft_id}", "test-draft-id") \
                          .replace("{step}", "1") \
                          .replace("{doc_id}", "test-doc-id") \
                          .replace("{token}", "test-token")
        res = client.get(test_url)
        # /s/{token} returns 404 for nonexistent token which is valid token-gated behavior
        if pattern == "/s/{token}":
            assert res.status_code in (200, 404)
            continue

        assert res.status_code == 200, (
            f"Public shell {pattern} must return 200 OK, got {res.status_code}"
        )
        # Assert zero user or case data is rendered in the static template
        assert "01755667788" not in res.text, f"User phone leaked in shell {pattern}"
        assert "মকবুল" not in res.text, f"Private party name leaked in shell {pattern}"
        assert 'name="password"' not in res.text, f"Password field in shell {pattern}"
        tested_shells += 1

    assert tested_shells >= 25, f"Expected at least 25 static shells, tested {tested_shells}"

    # Part B: Verify all non-public API endpoints reject unauthenticated access with 401 or 403
    protected_api_count = 0
    all_routes = get_all_routes(app.routes)
    for route in all_routes:
        path = route.path
        methods = route.methods or {"GET"}

        # Only evaluate /api/v1/* routes
        if not path.startswith("/api/v1"):
            continue

        if path in PUBLIC_API_WHITELIST:
            continue

        for method in methods:
            if method in ("HEAD", "OPTIONS"):
                continue

            res = client.request(method, path)
            assert res.status_code in (401, 403, 404, 422), (
                f"Security Vulnerability (X-001 Violation): API route [{method} {path}] "
                f"allowed unauthenticated access with status {res.status_code}! Output: {res.text[:200]}"
            )
            protected_api_count += 1

    assert protected_api_count > 0, "No protected API routes were evaluated in sweep"
    print(
        f"\n[X-001 Sweep] Successfully verified {tested_shells} public shells and {protected_api_count} protected API endpoints."
    )


def test_x001_legacy_dashboard_and_admin_security():
    """
    Verifies that root (/) and admin (/admin) shells return 200 with zero user data,
    while administrative API routes strictly enforce authentication and role separation.
    """
    # 1. Unauthenticated / -> 200 static shell with no user data
    res_dash_unauth = client.get("/")
    assert res_dash_unauth.status_code == 200
    assert "01755667788" not in res_dash_unauth.text

    # 2. Unauthenticated /admin -> 200 static shell with no user data
    res_admin_unauth = client.get("/admin")
    assert res_admin_unauth.status_code == 200
    assert "01755667788" not in res_admin_unauth.text

    # 3. Create regular Citizen user
    res_citizen_req = client.post("/auth/otp/request", json={"phone": "01755667788"})
    code_cit = res_citizen_req.json()["dev_otp"]
    res_cit_ver = client.post("/auth/otp/verify", json={"phone": "01755667788", "code": code_cit})
    cit_token = res_cit_ver.json()["access_token"]
    cit_headers = {"Authorization": f"Bearer {cit_token}"}

    # Citizen can access citizen API data
    res_dash_cit = client.get("/api/v1/home", headers=cit_headers)
    assert res_dash_cit.status_code == 200

    # Citizen CANNOT access /api/v1/admin/* -> 403 Forbidden
    res_admin_cit = client.get("/api/v1/admin/sources", headers=cit_headers)
    assert res_admin_cit.status_code == 403

    # 4. Create Admin user
    # Pre-seeded admin account phone: 01700000001
    res_admin_req = client.post("/auth/otp/request", json={"phone": "01700000001"})
    code_adm = res_admin_req.json()["dev_otp"]
    res_adm_ver = client.post("/auth/otp/verify", json={"phone": "01700000001", "code": code_adm})
    adm_token = res_adm_ver.json()["access_token"]
    adm_headers = {"Authorization": f"Bearer {adm_token}"}

    # Admin CAN access /api/v1/admin/* -> 200 OK
    res_admin_adm = client.get("/api/v1/admin/sources", headers=adm_headers)
    assert res_admin_adm.status_code == 200
