"""
Test AC-M01-1: A new user can sign up with a phone number and reach /home in <=4 screens.
Screen Flow: /welcome -> /signin -> /otp -> /onboarding -> /home
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


def test_ac_m01_1_signup_and_onboarding_flow():
    phone = "01711223344"

    # Screen 1: Welcome & Public Page access
    res_welcome = client.get("/welcome")
    assert res_welcome.status_code == 200
    assert "text/html" in res_welcome.headers.get("content-type", "")

    # Screen 2: /signin - Request OTP
    res_otp_req = client.post("/auth/otp/request", json={"phone": phone, "lang": "bn"})
    assert res_otp_req.status_code == 200
    data_otp_req = res_otp_req.json()
    assert data_otp_req["status"] == "sent"
    otp_code = data_otp_req["dev_otp"]
    assert len(otp_code) == 6

    # Screen 3: /otp - Verify OTP
    res_otp_verify = client.post(
        "/auth/otp/verify",
        json={"phone": phone, "code": otp_code, "device_label": "Mobile Chrome"},
    )
    assert res_otp_verify.status_code == 200
    data_verify = res_otp_verify.json()
    assert "access_token" in data_verify
    assert "refresh_token" in data_verify
    token = data_verify["access_token"]
    assert data_verify["user"]["is_onboarded"] is False

    # Screen 4: /onboarding - Separate versioned consents
    headers = {"Authorization": f"Bearer {token}"}
    res_onboard = client.post(
        "/auth/onboarding",
        headers=headers,
        json={
            "name": "Barrister Rafiq",
            "preferred_lang": "bn",
            "numeral_style": "bn",
            "terms_of_service": True,
            "privacy_policy": True,
            "ai_disclaimer": True,
        },
    )
    assert res_onboard.status_code == 200
    data_onboard = res_onboard.json()
    assert data_onboard["status"] == "onboarded"
    assert data_onboard["user"]["name"] == "Barrister Rafiq"
    assert data_onboard["user"]["is_onboarded"] is True

    # User can now access the authenticated dashboard / home shell
    res_home = client.get("/", headers=headers)
    assert res_home.status_code == 200
    assert "আইন-AI" in res_home.text
