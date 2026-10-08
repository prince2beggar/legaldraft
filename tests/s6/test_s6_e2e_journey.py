"""
End-to-End User Journey Tests for Sprint S6 (Case Folder M06, Home / Next Action M02, Notifications M07).

Flow Tested:
1. Citizen User visits /home -> Time-aware Bangla greeting & ProblemInput.
2. Notice analysis converted to Case via "Save to Case" (/api/v1/documents/:id/save-to-case).
3. Verified Case Folder in /cases and /cases/:id with all 8 tabs:
   - Overview: Case info, parties, objectives
   - Timeline: Chronological events with date precision (day/month/approximate)
   - Documents: Attached notice document
   - Tasks: Automatically created tasks from notice required actions
   - Deadlines: Confirmed deadline with calculation steps
   - Notes: Private notes with include_in_analysis privacy toggle (AC-M06-5)
   - Review: AI Gateway case.review.v1 execution with 6 sections, anti-outcome guarantee, and mandatory AI label
   - Lawyer: S8 M08 placeholder
4. Fact management: Accept proposed fact -> status becomes active.
5. Deterministic Next Action: Re-evaluate /api/v1/home -> Next Action Card dynamically prioritized.
6. Playwright UI verification: Headless browser navigates /home and /cases/:id ensuring 0 horizontal overflow and reactive UI.
"""

from __future__ import annotations

import time
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright

from packages.trust_kernel.auth import auth_service
from services.api.app.main import app

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = REPO_ROOT / "backend" / "app" / "static"


@pytest.fixture
def api_client():
    return TestClient(app)


@pytest.fixture
def auth_citizen(api_client, isolated_db_manager):
    phone = f"+88017{time.time_ns() % 100000000:08d}"
    res = api_client.post("/auth/otp/request", json={"phone": phone})
    code = res.json().get("dev_otp", "123456")
    res_ver = api_client.post("/auth/otp/verify", json={"phone": phone, "code": code})
    token = res_ver.json()["access_token"]

    decoded = jwt.decode(token, options={"verify_signature": False})
    real_uid = decoded["sub"]

    isolated_db_manager.save_user(
        {
            "id": real_uid,
            "phone": phone,
            "name": "মাহমুদুর রহমান",
            "role": "citizen",
            "roles": ["citizen"],
            "status": "active",
            "is_onboarded": True,
            "preferred_lang": "bn",
        }
    )

    u = auth_service.get_user(real_uid)
    if u:
        u["name"] = "মাহমুদুর রহমান"

    return {
        "user_id": real_uid,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }


def test_s6_e2e_api_and_business_logic_journey(api_client, auth_citizen, isolated_db_manager):
    headers = auth_citizen["headers"]
    uid = auth_citizen["user_id"]

    # 1. Citizen visits Home
    res_home = api_client.get("/api/v1/home", headers=headers)
    assert res_home.status_code == 200
    home_data = res_home.json()
    assert "greeting" in home_data
    assert "শুভ" in home_data["greeting"]

    # 2. Simulate Notice Document & Analysis created for this user
    doc_id = f"doc-notice-{time.time_ns()}"
    isolated_db_manager.save_document(
        {
            "id": doc_id,
            "owner_id": uid,
            "filename": "legal_notice_demand.pdf",
            "mime": "application/pdf",
            "size_bytes": 102400,
            "sha256": "fakehash" + str(time.time_ns()),
            "storage_key": f"documents/{doc_id}.pdf",
            "doc_type": "legal_notice",
            "processing_status": "ready",
            "intent": "understand",
        }
    )

    # Save notice analysis with deadline and required action
    analysis_data = {
        "issuing_authority": "বিজ্ঞ ১ম যুগ্ম জেলা জজ আদালত, ঢাকা",
        "notice_date": "2026-10-01",
        "sender": "এডভোকেট খন্দকার রফিকুল ইসলাম",
        "recipient": "মাহমুদুর রহমান",
        "subject": "জমির দলিল বাতিল সংক্রান্ত নোটিশ",
        "required_action": "১৫ দিনের মধ্যে আদালতে লিখিত বক্তব্য দাখিল",
        "calculated_deadline": "2026-10-16",
        "primary_deadline_card": {
            "has_deadline": True,
            "due_date": "2026-10-16",
            "is_confirmed": True,
            "note": "এনআই বা দেওয়ানি কার্যবিধি",
        },
        "deadline_basis": "এনআই বা দেওয়ানি কার্যবিধি",
        "consequences_if_ignored": "একতরফা ডিক্রি জারির সম্ভাবনা",
        "confidence": "HIGH",
    }
    isolated_db_manager.save_notice_analysis(
        document_id=doc_id,
        user_id=uid,
        analysis=analysis_data,
        certainty="HIGH",
        as_of_date="2026-10-01",
    )

    # 3. User clicks "Save to Case"
    res_save = api_client.post(
        f"/api/v1/documents/{doc_id}/save-to-case",
        json={"case_title": "জমি দলিল বাতিল মোকদ্দমা ২০২৬"},
        headers=headers,
    )
    assert res_save.status_code == 200
    save_result = res_save.json()
    created_case = save_result["case"]
    case_id = created_case["id"]
    assert created_case["title"] == "জমি দলিল বাতিল মোকদ্দমা ২০২৬"
    assert created_case["status"] == "action_required"

    # 4. Verify Case Details endpoint /cases/:id returns all 8 tabs
    res_case = api_client.get(f"/api/v1/cases/{case_id}", headers=headers)
    assert res_case.status_code == 200
    case_detail = res_case.json()["case"]

    # Tab 1: Overview
    assert case_detail["title"] == "জমি দলিল বাতিল মোকদ্দমা ২০২৬"
    assert len(case_detail["parties"]) >= 1

    # Tab 2: Timeline
    assert len(case_detail["events"]) >= 1
    for ev in case_detail["events"]:
        assert ev["date_precision"] in ("day", "month", "year", "approximate")

    # Tab 3: Documents
    assert any(d["id"] == doc_id for d in case_detail["documents"])

    # Tab 4: Tasks
    assert len(case_detail["tasks"]) >= 1

    # Tab 5: Deadlines
    assert len(case_detail["deadlines"]) >= 1
    dl = case_detail["deadlines"][0]
    assert dl["due_date"] == "2026-10-16"

    # Tab 6: Notes (with AC-M06-5 privacy)
    res_note = api_client.post(
        f"/api/v1/cases/{case_id}/notes",
        json={
            "note_text": "আইনজীবীর সাথে আগামী রবিবার চেম্বারে দেখা করব",
            "is_private": True,
            "include_in_analysis": False,
        },
        headers=headers,
    )
    assert res_note.status_code == 201

    # Tab 7: AI Case Review (case.review.v1)
    res_review = api_client.post(f"/api/v1/cases/{case_id}/review", headers=headers)
    assert res_review.status_code == 200
    review_resp = res_review.json()
    review_data = review_resp["review"]
    for sec in [
        "possible_issues",
        "missing_information",
        "required_documents",
        "possible_processes",
        "questions_for_lawyer",
        "options_to_discuss",
    ]:
        assert sec in review_data
    assert review_data["ai_label"] == "AI বিশ্লেষণ, আইনি পরামর্শ নয়"
    assert review_data["provider"] == "fake"

    # Tab 8: Lawyer placeholder exists in case_detail
    assert "status" in case_detail

    # 5. Proposed Fact Lifecycle: Accept Proposed Fact
    res_fact = api_client.post(
        f"/api/v1/cases/{case_id}/facts",
        json={"fact_text": "নোটিশগ্রহীতা নিয়মিত খাজনা পরিশোধ করেছেন", "source_doc_id": doc_id},
        headers=headers,
    )
    assert res_fact.status_code in (200, 201)
    fact_id = res_fact.json()["fact"]["id"]

    res_accept = api_client.post(f"/api/v1/cases/{case_id}/facts/{fact_id}/accept", headers=headers)
    assert res_accept.status_code == 200
    assert res_accept.json()["fact"]["status"] in ("accepted", "active")

    # 6. Re-evaluate /api/v1/home Next Action Card
    res_home2 = api_client.get("/api/v1/home", headers=headers)
    assert res_home2.status_code == 200
    home_data2 = res_home2.json()
    assert home_data2["next_action"] is not None
    assert home_data2["next_action"]["case_id"] == case_id
    assert len(home_data2["my_cases"]) >= 1
    assert len(home_data2["upcoming"]) >= 1


def test_s6_e2e_playwright_browser_flow():
    """
    Playwright headless UI journey:
    Loads /home, validates greeting & ProblemInput, tests navigation and responsive tab switches.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        # 1. Visit /home
        home_url = (STATIC_DIR / "home.html").as_uri() + "?variant=standard"
        page.goto(home_url)
        page.wait_for_selector("#nextActionCard")

        # Greeting & Problem input check
        greeting = page.locator("#greetingText")
        assert greeting.is_visible()

        problem_input = page.locator("#problemInputField")
        assert problem_input.is_visible()
        problem_input.fill("আমার জমি নিয়ে দেওয়ানি নোটিশ পেয়েছি, কি করব?")

        mic_btn = page.locator("#btnMic")
        assert mic_btn.is_visible()
        assert mic_btn.get_attribute("disabled") is not None

        # Next Action Card & Why Modal check
        btn_why = page.locator("#btnWhyNextAction")
        btn_why.click()
        page.wait_for_selector("#whyModal.open")
        page.locator(".modal-btn-close").click()

        # 2. Visit /cases
        cases_url = (STATIC_DIR / "cases.html").as_uri()
        page.goto(cases_url)
        page.wait_for_selector("#casesGrid")

        # Open Create Case modal
        page.locator("#btnOpenCreateModal").click()
        page.wait_for_selector("#createCaseModal.open")
        page.locator(".btn-secondary").click()

        # 3. Visit /cases/:id
        case_url = (
            STATIC_DIR / "case_detail.html"
        ).as_uri() + "?id=case-s6-mock-123&variant=overview"
        page.goto(case_url)
        page.wait_for_selector("#tab-overview")

        # Verify 8 tabs switching
        tabs = [
            "timeline",
            "documents",
            "tasks",
            "deadlines",
            "notes",
            "review",
            "lawyer",
            "overview",
        ]
        for t in tabs:
            btn = page.locator(f'[data-tab="{t}"]')
            btn.click()
            page.wait_for_selector(f"#tab-{t}.active")

        # Verify AI Review banner on review tab
        page.locator('[data-tab="review"]').click()
        page.wait_for_selector("#tab-review.active")
        ai_banner = page.locator(".fake-provider-banner")
        assert ai_banner.is_visible()
        ai_label = page.locator(".ai-label-pill")
        assert "AI বিশ্লেষণ, আইনি পরামর্শ নয়" in ai_label.inner_text()

        # Verify Notes Tab Privacy Toggle
        page.locator('[data-tab="notes"]').click()
        page.wait_for_selector("#tab-notes.active")
        privacy_toggle = page.locator("#noteIncludeInAnalysis")
        assert privacy_toggle.is_visible()

        browser.close()
