"""
Test AC-M01-2: 6th wrong OTP attempt locks verification for 15 minutes.
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


def test_ac_m01_2_otp_rate_limit_and_15_minute_lockout():
    phone = "01811223344"

    # Request code
    res_req = client.post("/auth/otp/request", json={"phone": phone})
    assert res_req.status_code == 200
    real_code = res_req.json()["dev_otp"]
    wrong_code = "000000" if real_code != "000000" else "999999"

    # Attempts 1 through 5: should return 400 Bad Request with decreasing remaining attempts
    for attempt in range(1, 6):
        res = client.post("/auth/otp/verify", json={"phone": phone, "code": wrong_code})
        assert res.status_code == 400
        data = res.json()
        assert "remaining_attempts" in data["detail"] or "attempts" in data["detail"]

    # 6th wrong attempt: must lock for 15 minutes with HTTP 423 Locked
    res_6th = client.post("/auth/otp/verify", json={"phone": phone, "code": wrong_code})
    assert res_6th.status_code == 423
    data_6th = res_6th.json()
    assert "locked for 15 minutes" in data_6th["detail"].lower()

    # Subsequent attempt even with the CORRECT code is blocked during lockout
    res_blocked = client.post("/auth/otp/verify", json={"phone": phone, "code": real_code})
    assert res_blocked.status_code == 423

    # New OTP request during lockout is also blocked with 423
    res_req_blocked = client.post("/auth/otp/request", json={"phone": phone})
    assert res_req_blocked.status_code == 423
