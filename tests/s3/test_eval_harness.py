"""
Unit and Integration Tests for Evaluation Harness & Quality Gates (SRS Section 8.7, 9.3 S3).
Proves:
1. Golden test sets are properly configured and labeled FAKE_TEST_DATA.
2. Evaluation execution calculates accuracy rate and enforces quality gate (>= 80%).
3. Runs and individual test results are persisted in DB.
"""

from packages.trust_kernel.db import db_manager
from packages.trust_kernel.eval_harness import EvalHarness


def test_golden_suites_loaded_with_fake_test_data():
    """All golden suites and test items must be explicitly marked FAKE_TEST_DATA."""
    harness = EvalHarness()
    suites = harness.list_suites()
    assert len(suites) >= 3
    for s_name in suites:
        cases = harness.golden_suites[s_name]
        for c in cases:
            assert c.label == "FAKE_TEST_DATA"


def test_run_suite_and_quality_gate():
    """Executes golden suite, calculates accuracy, and passes 80% quality gate."""
    harness = EvalHarness()
    run_result = harness.run_suite("limitation_deadline_calculation_golden.v1", gate_threshold=0.80)
    assert run_result["total_cases"] == 3
    assert run_result["passed_cases"] == 3
    assert run_result["accuracy_rate"] == 1.0
    assert run_result["gate_passed"] is True


def test_eval_runs_and_results_persisted():
    """Verifies that evaluation runs and individual case outcomes are recorded in DB."""
    harness = EvalHarness()
    run = harness.run_suite("citation_exactness_golden.v1")
    run_id = run["run_id"]

    # Verify run record in DB
    stored_run = db_manager.get_eval_run(run_id)
    assert stored_run is not None
    assert stored_run["suite_name"] == "citation_exactness_golden.v1"
    assert stored_run["gate_passed"] is True

    # Verify case-level records
    cases = db_manager.list_eval_results(run_id)
    assert len(cases) == 2
    for c in cases:
        assert c["run_id"] == run_id
        assert c["score"] >= 0.0
        assert c["latency_ms"] >= 0.0


def test_rule_b06_eval_critical_error_gate_fails_despite_high_score():
    """
    Rule B6 / Legal Quality Gate:
    In legal work, zero critical errors are tolerated.
    A test suite execution with 95% passing rate (19/20) but 1 critical error
    MUST FAIL the quality gate (gate_passed is False).
    """
    from datetime import datetime, timedelta

    from packages.trust_kernel.eval_harness import GoldenTestCase

    harness = EvalHarness()

    # Create 20 test cases: 19 passing rules calculations, 1 failing critical calculation
    cases = []
    base_date = datetime.strptime("2026-10-01", "%Y-%m-%d")
    for i in range(19):
        expected_date = (base_date + timedelta(days=i + 1)).strftime("%Y-%m-%d")
        cases.append(
            GoldenTestCase(
                id=f"tc-pass-{i}",
                suite="custom_limitation_suite.v1",
                target_component="rules",
                input_payload={
                    "rule_id": "relative_period.calendar_days.v1",
                    "inputs": {"start_date": "2026-10-01", "days": i + 1, "include_trigger_day": False},
                },
                expected={"result_date": expected_date, "status": "SUCCESS"},
                is_critical=True,
                critical_error_rule="Statutory limitation calculation must be exact.",
            )
        )
    # The 20th case fails on purpose (expected date is intentionally different to simulate a critical error)
    cases.append(
        GoldenTestCase(
            id="tc-critical-fail-20",
            suite="custom_limitation_suite.v1",
            target_component="rules",
            input_payload={
                "rule_id": "relative_period.calendar_days.v1",
                "inputs": {"start_date": "2026-10-01", "days": 30, "include_trigger_day": False},
            },
            expected={"result_date": "2099-01-01", "status": "SUCCESS"},  # Mismatched expected
            is_critical=True,
            critical_error_rule="Statutory limitation calculation must be exact.",
        )
    )

    run_res = harness.run_suite(
        suite_name="custom_limitation_suite.v1",
        custom_cases=cases,
        custom_config={
            "min_score": 0.90,
            "max_critical_errors": 0,
            "critical_error_rule": "Zero critical statutory errors permitted.",
        },
    )

    assert run_res["total_cases"] == 20
    assert run_res["passed_cases"] == 19
    assert run_res["failed_cases"] == 1
    assert run_res["critical_errors"] == 1
    assert run_res["accuracy_rate"] == 0.95  # 95% accuracy!

    # Crucial legal-tech assertion: Must FAIL despite 95% average because critical_errors > 0
    assert run_res["gate_passed"] is False
    assert run_res["gate_criteria"]["max_critical_errors"] == 0
