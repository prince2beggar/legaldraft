"""
Test X-001: Route-level Authorisation Sweep (SRS Section 5.P1, X-001, 9.3 S1).
Requirement:
"Every endpoint enforces authentication, role and ownership/consent checks via PolicyConsent.can;
add a test that iterates all routes and asserts an unauthenticated call fails."

Also covers:
- Legacy Advocate dashboard (/) requires login.
- /admin requires login and rejects regular citizens with 403 Forbidden.
"""

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from packages.trust_kernel.auth import auth_service
from services.api.app.main import app

client = TestClient(app)

PUBLIC_WHITELIST = {
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
    "/signin",
    "/welcome",
    "/otp",
    "/onboarding",
    "/api/v1/i18n/{locale}",
}


@pytest.fixture(autouse=True)
def clean_auth_state():
    auth_service.clear()
    yield
    auth_service.clear()


def test_x001_unauthenticated_route_sweep():
    """
    Iterates through EVERY route defined in the FastAPI application.
    Asserts that all non-whitelisted endpoints reject unauthenticated requests
    with 401 Unauthorized or 403 Forbidden.
    """
    tested_count = 0
    protected_count = 0

    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue

        path = route.path
        methods = route.methods or {"GET"}

        # Skip public endpoints and static mounts
        if path in PUBLIC_WHITELIST or path.startswith("/static"):
            continue

        for method in methods:
            if method in ("HEAD", "OPTIONS"):
                continue

            tested_count += 1
            # Execute request without any Authorization header or session cookies
            res = client.request(method, path)

            # Protected routes must return 401 Unauthorized or 403 Forbidden or 404 (if invalid path param)
            assert res.status_code in (401, 403), (
                f"Security Vulnerability (X-001 Violation): Route [{method} {path}] "
                f"allowed unauthenticated access with status {res.status_code}! Output: {res.text[:200]}"
            )
            protected_count += 1

    assert protected_count > 0, "No protected routes were evaluated in sweep"
    print(
        f"\n[X-001 Sweep] Successfully verified {protected_count} protected endpoints across all modules."
    )


def test_x001_legacy_dashboard_and_admin_security():
    """
    Verifies that the legacy Advocate Dashboard (/) and Admin portal (/admin)
    strictly enforce authentication and role separation.
    """
    # 1. Unauthenticated / -> 401
    res_dash_unauth = client.get("/")
    assert res_dash_unauth.status_code == 401

    # 2. Unauthenticated /admin -> 401
    res_admin_unauth = client.get("/admin")
    assert res_admin_unauth.status_code == 401

    # 3. Create regular Citizen user
    res_citizen_req = client.post("/auth/otp/request", json={"phone": "01755667788"})
    code_cit = res_citizen_req.json()["dev_otp"]
    res_cit_ver = client.post("/auth/otp/verify", json={"phone": "01755667788", "code": code_cit})
    cit_token = res_cit_ver.json()["access_token"]
    cit_headers = {"Authorization": f"Bearer {cit_token}"}

    # Citizen can access dashboard (/)
    res_dash_cit = client.get("/", headers=cit_headers)
    assert res_dash_cit.status_code == 200

    # Citizen CANNOT access /admin -> 403 Forbidden
    res_admin_cit = client.get("/admin", headers=cit_headers)
    assert res_admin_cit.status_code == 403
    assert "admin or reviewer" in res_admin_cit.json()["detail"].lower()

    # 4. Create Admin user
    # Pre-seeded admin account phone: 01700000001
    res_admin_req = client.post("/auth/otp/request", json={"phone": "01700000001"})
    code_adm = res_admin_req.json()["dev_otp"]
    res_adm_ver = client.post("/auth/otp/verify", json={"phone": "01700000001", "code": code_adm})
    adm_token = res_adm_ver.json()["access_token"]
    adm_headers = {"Authorization": f"Bearer {adm_token}"}

    # Admin CAN access /admin -> 200 OK
    res_admin_adm = client.get("/admin", headers=adm_headers)
    assert res_admin_adm.status_code == 200
    assert "admin" in res_admin_adm.text.lower() or "অ্যাডমিন" in res_admin_adm.text
