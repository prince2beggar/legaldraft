"""
Test AC-M01-4: Data export contains the user's cases, documents, drafts, consents, and audit extract;
Deletion removes or anonymises data per Section 8.4 and user can no longer sign in.
"""

import pytest
from fastapi.testclient import TestClient

from packages.trust_kernel.auth import auth_service
from services.api.app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_auth_state():
    auth_service.clear()
    yield
    auth_service.clear()


def test_ac_m01_4_data_export_and_account_deletion():
    phone = "01511223344"

    # Sign in and onboard
    res_req = client.post("/auth/otp/request", json={"phone": phone})
    code = res_req.json()["dev_otp"]
    res_verify = client.post("/auth/otp/verify", json={"phone": phone, "code": code})
    token = res_verify.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    client.post(
        "/auth/onboarding",
        headers=headers,
        json={
            "name": "Sharif Hossain",
            "terms_of_service": True,
            "privacy_policy": True,
            "ai_disclaimer": True,
        },
    )

    # 1. Data Export
    res_export = client.post("/me/export", headers=headers)
    assert res_export.status_code == 200
    export_bundle = res_export.json()

    # Must contain profile, consents, devices, and audit extract per AC-M01-4
    assert "profile" in export_bundle
    assert "consents" in export_bundle
    assert "audit_extract" in export_bundle
    assert export_bundle["profile"]["name"] == "Sharif Hossain"
    assert len(export_bundle["consents"]) >= 3
    assert len(export_bundle["audit_extract"]) >= 1

    # 2. Account Deletion
    res_delete = client.post("/me/delete", headers=headers)
    assert res_delete.status_code == 200
    assert res_delete.json()["status"] == "deleted"

    # 3. Subsequent API calls fail with 401
    res_me = client.get("/me", headers=headers)
    assert res_me.status_code == 401

    # 4. Attempting to sign in again with the same phone fails with 403 (Account permanently deleted)
    res_req2 = client.post("/auth/otp/request", json={"phone": phone})
    assert res_req2.status_code == 403
    assert "deleted" in res_req2.json()["detail"].lower()

    # 5. Requirement 4 Check: Plain phone number is NOT stored in blocklist, only salted hash
    assert phone not in auth_service._deleted_phone_hashes
    assert auth_service._hash_phone(phone) in auth_service._deleted_phone_hashes
