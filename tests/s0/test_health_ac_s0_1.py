"""
Test AC-S0-1: Health and Readiness Endpoints
"""

from fastapi.testclient import TestClient

from services.api.app.main import app

client = TestClient(app)


def test_liveness_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "AIN-AI"
    assert data["version"] == "2.0.0"
    assert "timestamp" in data


def test_readiness_endpoint():
    response = client.get("/health/ready")
    assert response.status_code in (200, 503)
    data = response.json()
    assert "status" in data
    assert "checks" in data
    assert "database" in data["checks"]


def test_feature_flags_endpoint():
    response = client.get("/health/flags")
    assert response.status_code == 200
    flags = response.json()
    assert isinstance(flags, dict)
    assert flags.get("M01_AUTH") is True
    assert flags.get("M12_RESEARCH_WORKSPACE") is False
