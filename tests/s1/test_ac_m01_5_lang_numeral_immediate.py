"""
Test AC-M01-5: Language and numeral changes apply immediately across all screens.
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


def test_ac_m01_5_language_and_numeral_immediate_reflection():
    phone = "01611223344"

    # Sign in
    res_req = client.post("/auth/otp/request", json={"phone": phone})
    code = res_req.json()["dev_otp"]
    res_verify = client.post("/auth/otp/verify", json={"phone": phone, "code": code})
    token = res_verify.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Default settings must be Bengali ("bn")
    res_me_init = client.get("/me", headers=headers)
    assert res_me_init.status_code == 200
    assert res_me_init.json()["preferred_lang"] == "bn"
    assert res_me_init.json()["numeral_style"] == "bn"

    # Update language to English and numeral style to English
    res_update = client.patch(
        "/me",
        headers=headers,
        json={"preferred_lang": "en", "numeral_style": "en", "name": "Advocate John"},
    )
    assert res_update.status_code == 200
    assert res_update.json()["user"]["preferred_lang"] == "en"
    assert res_update.json()["user"]["numeral_style"] == "en"

    # Immediate query to /me reflects the updated language and numerals
    res_me_after = client.get("/me", headers=headers)
    assert res_me_after.status_code == 200
    assert res_me_after.json()["preferred_lang"] == "en"
    assert res_me_after.json()["numeral_style"] == "en"
    assert res_me_after.json()["name"] == "Advocate John"

    # Home request with English preference renders English title
    res_home = client.get("/?lang=en", headers=headers)
    assert res_home.status_code == 200
    assert "English" in res_home.text or 'lang="en"' in res_home.text
