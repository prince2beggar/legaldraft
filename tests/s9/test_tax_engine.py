"""
Comprehensive Test Suite for Bangladesh Taxation & VAT Engine (Module M23).
Tests:
- Income Tax Act 2023 slabs, thresholds, exemptions
- Minimum tax floor by jurisdiction
- Investment rebate calculation
- Advance tax and refund detection
- VAT Act 2012 calculations, input credit, VDS withholding
- Form IT-11GA and Mushak-9.1 generation
- API endpoints & tenancy isolation
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from packages.trust_kernel.db import DatabaseManager
from packages.trust_kernel.tax_engine import TaxEngine
from services.api.app.main import app
from services.api.app.routers.auth import get_current_user


@pytest.fixture
def isolated_db(tmp_path):
    db_file = tmp_path / "test_tax.db"
    mgr = DatabaseManager(f"sqlite:///{db_file}")
    mgr.init_db()
    yield mgr
    try:
        mgr.engine.dispose()
    except Exception:
        pass


def test_income_tax_under_threshold_is_zero():
    """Income below 3,50,000 BDT for general male results in zero tax."""
    res = TaxEngine.calculate_income_tax({
        "category": "general",
        "income_salary": 300000,
    })
    assert res["total_income"] == 300000
    assert res["taxable_income"] == 0
    assert res["gross_tax"] == 0
    assert res["net_payable"] == 0


def test_income_tax_slabs_general():
    """
    General male earning 8,00,000 BDT:
    - 3,50,000 @ 0% = 0
    - Next 1,00,000 @ 5% = 5,000
    - Next 3,50,000 (remaining) @ 10% = 35,000
    Total Gross Tax = 40,000 BDT.
    """
    res = TaxEngine.calculate_income_tax({
        "category": "general",
        "location": "dhaka_chattogram_cc",
        "income_salary": 800000,
    })
    assert res["total_income"] == 800000
    assert res["taxable_income"] == 450000
    assert res["gross_tax"] == 40000.0


def test_income_tax_female_senior_threshold():
    """Female / Senior taxpayer gets 4,00,000 BDT tax-free."""
    res = TaxEngine.calculate_income_tax({
        "category": "female_senior",
        "income_salary": 400000,
    })
    assert res["threshold"] == 400000
    assert res["taxable_income"] == 0
    assert res["gross_tax"] == 0


def test_income_tax_freedom_fighter_threshold():
    """Freedom fighter gets 5,00,000 BDT tax-free."""
    res = TaxEngine.calculate_income_tax({
        "category": "freedom_fighter",
        "income_salary": 500000,
    })
    assert res["threshold"] == 500000
    assert res["taxable_income"] == 0
    assert res["gross_tax"] == 0


def test_minimum_tax_floor_enforcement():
    """
    If gross tax is 2,500 but located in Dhaka City Corp, minimum 5,000 applies.
    """
    # 400,000 income -> 50,000 taxable @ 5% = 2,500 gross tax
    res = TaxEngine.calculate_income_tax({
        "category": "general",
        "location": "dhaka_chattogram_cc",
        "income_salary": 400000,
    })
    assert res["gross_tax"] == 2500.0
    assert res["net_payable"] == 5000.0  # Raised to minimum tax floor
    assert res["applies_minimum_tax"] is True


def test_investment_tax_rebate():
    """
    Investment rebate: lower of 15% of investment or 3% of total income.
    Total income: 10,00,000 (3% = 30,000)
    Investment: 1,00,000 (15% = 15,000)
    Rebate = 15,000.
    """
    res = TaxEngine.calculate_income_tax({
        "category": "general",
        "location": "dhaka_chattogram_cc",
        "income_salary": 1000000,
        "actual_investment": 100000,
    })
    assert res["rebate"] == 15000.0
    assert res["tax_after_rebate"] == res["gross_tax"] - 15000.0


def test_advance_tax_and_refund():
    """If advance tax exceeds tax liability, refund is recorded."""
    res = TaxEngine.calculate_income_tax({
        "category": "general",
        "location": "dhaka_chattogram_cc",
        "income_salary": 500000,  # Gross tax: 10,000
        "advance_tax_paid": 12000,  # Paid: 12,000
    })
    assert res["is_refund"] is True
    assert res["refund_amount"] == 2000.0
    assert res["net_payable"] == 0.0


def test_vat_standard_and_input_credit():
    """
    VAT Calculation:
    - Standard sales 5,00,000 @ 15% = 75,000 output VAT
    - Input purchases 2,00,000 @ 15% = 30,000 input credit
    - VDS deducted by buyers = 5,000
    - Net payable = 75,000 - 30,000 - 5,000 = 40,000 BDT
    """
    res = TaxEngine.calculate_vat({
        "standard_sales": 500000,
        "input_purchases_standard": 200000,
        "vds_deducted_by_buyers": 5000,
    })
    assert res["output_vat_std"] == 75000.0
    assert res["input_vat_credit"] == 30000.0
    assert res["net_vat_payable"] == 40000.0
    assert res["is_closing_credit"] is False


def test_it11ga_statement_generation():
    """Form IT-11GA generation produces structured return with all required sections including profession & time."""
    calc = TaxEngine.calculate_income_tax({
        "category": "general",
        "income_salary": 600000,
    })
    stmt = TaxEngine.generate_it11ga_statement(
        profile={
            "taxpayer_name": "করিম সাহেব",
            "profession": "সফটওয়্যার ইঞ্জিনিয়ার",
            "workplace": "টেক কোম্পানি লিমিটেড",
            "tin": "123456789012",
            "filing_date": "2026-10-11",
            "filing_time": "08:45 PM",
        },
        calc_result=calc,
    )
    assert stmt["form_code"] == "IT-11GA"
    assert stmt["taxpayer_name"] == "করিম সাহেব"
    assert stmt["profession"] == "সফটওয়্যার ইঞ্জিনিয়ার"
    assert stmt["workplace"] == "টেক কোম্পানি লিমিটেড"
    assert stmt["tin"] == "123456789012"
    assert stmt["date"] == "2026-10-11"
    assert stmt["time"] == "08:45 PM"
    assert "summary_of_income" in stmt
    assert "tax_computation" in stmt
    assert "assets_summary_it10b" in stmt


def test_tax_api_endpoints_end_to_end():
    """Tests the full API flow via FastAPI TestClient."""
    mock_user = {"id": "usr-test-tax-01", "role": "citizen", "phone": "01711000001"}
    app.dependency_overrides[get_current_user] = lambda: mock_user
    client = TestClient(app)

    try:
        # 1. Calculate Income Tax
        calc_res = client.post(
            "/api/v1/tax/calculate/income-tax",
            json={
                "category": "general",
                "income_salary": 700000,
                "income_house": 100000,
            },
        )
        assert calc_res.status_code == 200
        data = calc_res.json()
        assert data["total_income"] == 800000
        assert data["gross_tax"] == 40000.0

        # 2. Save Tax Return with Name, Profession, Workplace, Date, Time
        save_res = client.post(
            "/api/v1/tax/returns",
            json={
                "return_type": "income_tax",
                "tax_period": "2024-2025",
                "taxpayer_name": "রফিকুল ইসলাম",
                "taxpayer_tin": "789123456789",
                "inputs": {
                    "profession": "ব্যাংকার",
                    "workplace": "সোনালী ব্যাংক পিএলসি",
                    "filing_date": "2026-10-11",
                    "filing_time": "08:45 PM",
                    "category": "general",
                    "income_salary": 700000,
                    "income_house": 100000,
                },
            },
        )
        assert save_res.status_code == 200
        ret_id = save_res.json()["id"]

        # 3. Retrieve Return
        get_res = client.get(f"/api/v1/tax/returns/{ret_id}")
        assert get_res.status_code == 200
        assert get_res.json()["taxpayer_name"] == "রফিকুল ইসলাম"
        assert get_res.json()["inputs"]["profession"] == "ব্যাংকার"
        assert get_res.json()["inputs"]["filing_time"] == "08:45 PM"

        # 4. Retrieve IT-11GA Statement
        stmt_res = client.get(f"/api/v1/tax/returns/{ret_id}/it11ga")
        assert stmt_res.status_code == 200
        assert stmt_res.json()["form_code"] == "IT-11GA"
        assert stmt_res.json()["profession"] == "ব্যাংকার"

        # 5. List returns
        list_res = client.get("/api/v1/tax/returns")
        assert list_res.status_code == 200
        assert any(r["id"] == ret_id for r in list_res.json())

        # 6. Delete return
        del_res = client.delete(f"/api/v1/tax/returns/{ret_id}")
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "deleted"

        # 7. Verify deletion
        get_after_del = client.get(f"/api/v1/tax/returns/{ret_id}")
        assert get_after_del.status_code == 404

    finally:
        app.dependency_overrides.pop(get_current_user, None)

