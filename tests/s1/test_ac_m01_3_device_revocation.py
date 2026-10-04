"""
Test AC-M01-3: Revoking a device invalidates its refresh token; its next API call returns 401.
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


def test_ac_m01_3_device_revocation_invalidates_tokens():
    phone = "01911223344"
    device_id = "test-device-uuid-1234"

    # Step 1: Sign in with a specific device
    res_req = client.post("/auth/otp/request", json={"phone": phone})
    code = res_req.json()["dev_otp"]

    res_verify = client.post(
        "/auth/otp/verify",
        json={
            "phone": phone,
            "code": code,
            "device_id": device_id,
            "device_label": "Office Laptop",
        },
    )
    assert res_verify.status_code == 200
    access_token = res_verify.json()["access_token"]
    refresh_token = res_verify.json()["refresh_token"]

    headers = {"Authorization": f"Bearer {access_token}"}

    # Step 2: Access protected /me endpoint successfully
    res_me = client.get("/me", headers=headers)
    assert res_me.status_code == 200
    assert res_me.json()["phone"] == phone

    # Step 3: Refresh tokens works initially
    res_ref = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert res_ref.status_code == 200
    assert "access_token" in res_ref.json()

    # Step 4: Revoke the device via DELETE /me/devices/:id
    res_revoke = client.delete(f"/me/devices/{device_id}", headers=headers)
    assert res_revoke.status_code == 200
    assert res_revoke.json()["status"] == "revoked"

    # Step 5: Next API call using access token of revoked device must return 401
    res_me_revoked = client.get("/me", headers=headers)
    assert res_me_revoked.status_code == 401

    # Step 6: Using refresh token for revoked device must return 401
    res_ref_revoked = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert res_ref_revoked.status_code == 401
