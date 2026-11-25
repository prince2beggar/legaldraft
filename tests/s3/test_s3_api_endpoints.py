"""
API Endpoint Integration Tests for Sprint S3 (Rules Engine & Eval Harness).
Verifies:
1. GET /api/v1/rules returns registered rules with versions.
2. POST /api/v1/rules/compute executes computation and returns reasoned output.
3. POST /api/v1/rules/test runs rule test suite.
4. GET /admin/rules serves the responsive rules UI.
5. GET /api/v1/evals/golden-sets returns available golden evaluation suites.
6. POST /api/v1/evals/run triggers evaluation and computes quality gates.
7. GET /api/v1/evals/runs returns historical runs.
8. GET /admin/evals serves the responsive evaluation dashboard.
"""

from fastapi.testclient import TestClient

from services.api.app.main import app

client = TestClient(app)


def test_api_list_rules():
    response = client.get("/api/v1/rules")
    assert response.status_code == 200
    data = response.json()
    assert "rules" in data
    assert len(data["rules"]) >= 1
    rule = data["rules"][0]
    assert "versions" in rule


def test_api_compute_rule():
    payload = {
        "rule_id": "relative_period.calendar_days.v1",
        "inputs": {"start_date": "2026-10-01", "days": 30, "include_trigger_day": False},
    }
    response = client.post("/api/v1/rules/compute", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["result"]["result_date"] == "2026-10-31"
    assert data["result"]["holiday_calendar_used"] == "EMPTY_FAKE_TEST_DATA"


def test_api_run_rule_tests():
    payload = {"rule_id": "relative_period.calendar_days.v1", "version": "1.0.0"}
    response = client.post("/api/v1/rules/test", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_tests"] >= 3
    assert data["failed_tests"] == 0


def test_admin_rules_html_served():
    response = client.get("/admin/rules")
    assert response.status_code == 200
    assert "আইনি রুলস ইঞ্জিন" in response.text
    assert "relative_period.calendar_days.v1" in response.text


from packages.trust_kernel.auth import create_access_token


def _get_admin_headers():
    token = create_access_token(
        data={"sub": "01700000000", "phone": "01700000000", "role": "admin"}
    )
    return {"Authorization": f"Bearer {token}"}


def test_api_list_golden_sets():
    response = client.get("/api/v1/evals/golden-sets", headers=_get_admin_headers())
    assert response.status_code == 200
    data = response.json()
    assert "golden_sets" in data
    assert len(data["golden_sets"]) >= 3
    for gs in data["golden_sets"]:
        assert gs["label"] == "FAKE_TEST_DATA"


def test_api_trigger_eval_run():
    payload = {"suite_name": "limitation_deadline_calculation_golden.v1", "gate_threshold": 0.80}
    response = client.post("/api/v1/evals/run", json=payload, headers=_get_admin_headers())
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["run"]["gate_passed"] is True
    assert data["run"]["accuracy_rate"] == 1.0


def test_api_list_eval_runs():
    response = client.get("/api/v1/evals/runs", headers=_get_admin_headers())
    assert response.status_code == 200
    data = response.json()
    assert "runs" in data
    assert len(data["runs"]) >= 1


def test_admin_evals_html_served():
    response = client.get("/admin/evals")
    assert response.status_code == 200
    assert "আইনি মূল্যায়ন ও কোয়ালিটি গেট" in response.text
    assert "limitation_deadline_calculation_golden.v1" in response.text
