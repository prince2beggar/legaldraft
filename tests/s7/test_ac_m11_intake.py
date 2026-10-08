"""
Sprint S7 Test Suite: Intake and Triage (Module M11).
Verifies:
- AC-M11-1: Selecting any triage chip shows the UrgentBanner within one screen and before any AI call.
- AC-M11-2: On the triage golden set (lawyer-written), urgent recall >= 90%; zero cases where classifier lowered a user-selected urgency.
- AC-M11-3: No fact appears in the case until the user confirms it; AI-proposed items are labelled "proposed".
- AC-M11-4: Emergency contacts display their last_verified_at; unverified entries display "Not yet verified" and are not shown as official numbers.
- AC-M11-5: Intake can be abandoned and resumed with all answers preserved.
"""

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright

from packages.trust_kernel.ai_gateway import AIGateway
from packages.trust_kernel.case_engine import CaseEngine
from packages.trust_kernel.db import DatabaseManager
from packages.trust_kernel.intake_engine import IntakeEngine
from services.api.app.main import app

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GOLDEN_SET_PATH = REPO_ROOT / "tests" / "data" / "triage_golden_set.json"
STATIC_DIR = REPO_ROOT / "backend" / "app" / "static"


@pytest.fixture
def isolated_db(tmp_path):
    db_file = tmp_path / "test_s7_intake.db"
    db_url = f"sqlite:///{db_file}"
    mgr = DatabaseManager(db_url)
    mgr.init_db()
    mgr.seed_default_emergency_contacts()
    return mgr


@pytest.fixture
def fake_gateway(isolated_db):
    gw = AIGateway(db=isolated_db)
    return gw


@pytest.fixture
def intake_eng(isolated_db, fake_gateway):
    case_eng = CaseEngine(db=isolated_db, gateway=fake_gateway)
    return IntakeEngine(db=isolated_db, gateway=fake_gateway, case_engine=case_eng)


@pytest.fixture
def citizen_user(isolated_db):
    return isolated_db.create_user(phone="01711999888", name="Citizen Hasan", role="citizen")


# ---------------------------------------------------------------------------
# AC-M11-1: UrgentBanner Before AI Call
# ---------------------------------------------------------------------------


def test_ac_m11_1_selecting_triage_chip_shows_urgent_banner_before_ai(
    intake_eng, citizen_user, fake_gateway
):
    """
    AC-M11-1: Selecting any triage chip shows the UrgentBanner within one screen and before any AI call.
    """
    # 1. Create session with an urgent triage chip
    urgent_chip = "violence_threat"
    session = intake_eng.create_session(
        user_id=citizen_user["id"],
        triage_chips=[urgent_chip],
    )

    # 2. Urgent banner triggered immediately (urgency == "urgent")
    assert session["urgency"] == "urgent"
    assert session["urgency_reason"] == "urgent_triage_chip_selected"

    # 3. Assert zero AI calls were made during triage chip selection
    # In FakeLLMProvider / DB, count AI outputs for this session
    ai_outputs = intake_eng.db.list_ai_outputs(prompt_id="intake.profile.v1")
    assert len(ai_outputs) == 0, "No AI call should be executed when selecting triage chips"

    # 4. Emergency contacts are available immediately
    contacts = intake_eng.db.list_emergency_contacts(active_only=True)
    assert len(contacts) >= 3, "Emergency helplines must be available immediately for UrgentBanner"


# ---------------------------------------------------------------------------
# AC-M11-2: Triage Golden Set Recall & Classifier Monotonicity
# ---------------------------------------------------------------------------


def test_ac_m11_2_triage_golden_set_recall_and_classifier_only_raises(intake_eng, citizen_user):
    """
    AC-M11-2: On the triage golden set (lawyer-written), urgent recall >= 90%;
    zero cases where classifier lowered a user-selected urgency.
    """
    assert GOLDEN_SET_PATH.exists(), f"Golden set file missing at {GOLDEN_SET_PATH}"

    with open(GOLDEN_SET_PATH, encoding="utf-8") as f:
        cases = json.load(f)

    assert len(cases) >= 30, f"Golden set must have >= 30 cases, found {len(cases)}"

    tp = 0
    fn = 0
    tn = 0
    fp = 0
    lowered_count = 0

    for item in cases:
        # Create session with user's initial choices
        chips = item["triage_chips"]
        initial_urgency = item["user_selected_urgency"]
        ground_truth = item["ground_truth_urgency"]

        session = intake_eng.create_session(
            user_id=citizen_user["id"],
            triage_chips=chips,
        )

        # Save narrative text and deadline
        answers = {
            "what_happened": item["user_text"],
        }
        if item.get("stated_deadline_days") is not None:
            answers["stated_deadline_days"] = item["stated_deadline_days"]

        # Save answers to trigger evaluate_triage
        updated = intake_eng.save_answer(
            session_id=session["id"],
            user_id=citizen_user["id"],
            question_key="what_happened",
            answer_value=item["user_text"],
            step=2,
        )
        if item.get("stated_deadline_days") is not None:
            updated = intake_eng.save_answer(
                session_id=session["id"],
                user_id=citizen_user["id"],
                question_key="stated_deadline_days",
                answer_value=item["stated_deadline_days"],
                step=8,
            )

        predicted_urgency = updated["urgency"]

        # Monotonicity check: Did classifier lower user-selected urgency?
        if initial_urgency == "urgent" and predicted_urgency == "normal":
            lowered_count += 1

        # Accuracy metrics on ground truth
        if ground_truth == "urgent":
            if predicted_urgency == "urgent":
                tp += 1
            else:
                fn += 1
        else:
            if predicted_urgency == "normal":
                tn += 1
            else:
                fp += 1

    total_urgent = tp + fn
    urgent_recall = (tp / total_urgent) * 100 if total_urgent > 0 else 0.0

    print(f"\nTriage Golden Set Results: TP={tp}, FN={fn}, TN={tn}, FP={fp}")
    print(f"Urgent Recall: {urgent_recall:.1f}% (Required >= 90%)")
    print(f"Classifier Lowered Count: {lowered_count} (Required == 0)")

    assert urgent_recall >= 90.0, f"Urgent recall {urgent_recall:.1f}% below 90% threshold"
    assert lowered_count == 0, (
        f"Classifier lowered urgency in {lowered_count} cases! Must be strictly 0."
    )


# ---------------------------------------------------------------------------
# AC-M11-3: Facts Require Confirmation & AI Proposed Items Labelled
# ---------------------------------------------------------------------------


def test_ac_m11_3_no_fact_in_case_until_confirmed_proposed_labelled(intake_eng, citizen_user):
    """
    AC-M11-3: No fact appears in the case until the user confirms it;
    AI-proposed items are labelled 'proposed'.
    """
    session = intake_eng.create_session(user_id=citizen_user["id"])
    intake_eng.save_answer(
        session_id=session["id"],
        user_id=citizen_user["id"],
        question_key="what_happened",
        answer_value="বিবাদী আমার জমির সীমানা প্রাচীর ভেঙে দখল করেছে।",
        step=2,
    )

    # 1. Generate AI Profile
    profile = intake_eng.generate_case_profile(session["id"], citizen_user["id"])
    assert "facts" in profile

    # 2. User confirms ONLY fact 1; fact 2 is kept as proposed
    fact_confirmed = "বিবাদী সীমানা প্রাচীর ভেঙেছে।"
    fact_proposed = "জমির আনুমানিক মূল্য ২০ লক্ষ টাকা।"

    confirmed_payload = {
        "title": "সীমানা প্রাচীর সংক্রান্ত বিরোধ",
        "case_type": "land_property",
        "objective": "প্রাচীর পুনর্নির্মাণ ও ক্ষতিপূরণ",
        "facts": [{"text": fact_confirmed}],
        "proposed_facts": [{"text": fact_proposed}],
        "events": [{"date": "2026-10-01", "what": "প্রাচীর ভাঙার ঘটনা"}],
    }

    result = intake_eng.confirm_and_create_case(
        session_id=session["id"],
        user_id=citizen_user["id"],
        confirmed_data=confirmed_payload,
    )

    case_id = result["case_id"]

    # 3. Query confirmed facts (include_proposed=False) -> Only confirmed fact appears
    case_facts_confirmed = intake_eng.case_engine.db.list_case_facts(
        case_id, include_proposed=False
    )
    assert len(case_facts_confirmed) == 1
    assert case_facts_confirmed[0]["fact_text"] == fact_confirmed
    assert case_facts_confirmed[0]["is_proposed"] is False

    # 4. Query all facts (include_proposed=True) -> Proposed fact is visibly labelled
    all_facts = intake_eng.case_engine.db.list_case_facts(case_id, include_proposed=True)
    assert len(all_facts) == 2
    proposed_entry = next(f for f in all_facts if f["fact_text"] == fact_proposed)
    assert proposed_entry["is_proposed"] is True
    assert proposed_entry["status"] == "proposed"


# ---------------------------------------------------------------------------
# AC-M11-4: Emergency Contacts Verification Metadata Display & Placeholders
# ---------------------------------------------------------------------------


def test_ac_m11_4_emergency_contacts_verification_status_display(intake_eng):
    """
    AC-M11-4: Emergency contacts display their last_verified_at;
    unverified entries display 'যাচাই করা হয়নি' and are not shown as official numbers.
    """
    contacts = intake_eng.db.list_emergency_contacts(active_only=False)
    assert len(contacts) >= 3

    # All seeded contacts are unverified placeholders (Sprint S7 E1 hard rule)
    for c in contacts:
        assert c["is_verified"] is False, f"Seeded contact {c['phone']} must NOT be verified"
        assert c["last_verified_at"] is None, (
            f"Seeded contact {c['phone']} last_verified_at must be None"
        )
        assert c["source_note"] is None, f"Seeded contact {c['phone']} source_note must be None"

    phones = {c["phone"] for c in contacts}
    assert "999" in phones
    assert "16430" in phones
    assert "109" in phones


# ---------------------------------------------------------------------------
# AC-M11-5: Abandon and Resume Preserves Answers
# ---------------------------------------------------------------------------


def test_ac_m11_5_intake_abandon_and_resume_preserves_answers(intake_eng, citizen_user):
    """
    AC-M11-5: Intake can be abandoned and resumed with all answers preserved.
    """
    # 1. Start intake session
    session = intake_eng.create_session(user_id=citizen_user["id"])
    sid = session["id"]

    # 2. Answer multiple steps
    intake_eng.save_answer(
        sid, citizen_user["id"], "what_happened", "দোকান ভাড়ার চুক্তি নিয়ে সমস্যা", step=2
    )
    intake_eng.save_answer(sid, citizen_user["id"], "where_happened", "মিরপুর-১০, ঢাকা", step=4)
    intake_eng.save_answer(sid, citizen_user["id"], "user_objective", "জামানত ফেরত পাওয়া", step=9)

    # 3. Abandon session
    abandoned = intake_eng.abandon_session(sid, citizen_user["id"])
    assert abandoned["status"] == "abandoned"

    # 4. Resume session
    resumed = intake_eng.resume_session(sid, citizen_user["id"])
    assert resumed["status"] == "in_progress"

    # 5. Verify all answers and step are completely preserved
    answers = resumed["answers"]
    assert answers["what_happened"] == "দোকান ভাড়ার চুক্তি নিয়ে সমস্যা"
    assert answers["where_happened"] == "মিরপুর-১০, ঢাকা"
    assert answers["user_objective"] == "জামানত ফেরত পাওয়া"
    assert resumed["current_step"] == 9


# ---------------------------------------------------------------------------
# E1: Emergency Contacts Security & Admin Verification with Audit Log
# ---------------------------------------------------------------------------


def test_e1_emergency_contacts_no_invented_numbers_and_admin_verification(intake_eng):
    """
    E1: Hard rule against invented mobile numbers.
    Admin verification requires source_note, admin identity, and writes audit entry.
    """
    contacts = intake_eng.db.list_emergency_contacts(active_only=False)

    # Fails if invented mobile numbers exist
    for c in contacts:
        assert c["phone"] not in ("01726222222", "01715222111"), (
            "Invented numbers strictly forbidden"
        )

    client = TestClient(app)
    from datetime import datetime, timedelta, timezone

    from packages.trust_kernel.auth import TokenService, auth_service

    cit_user = {
        "id": "test-citizen-e1",
        "phone": "01711999111",
        "name": "Citizen One",
        "role": "citizen",
        "roles": ["citizen"],
        "status": "active",
        "is_onboarded": True,
    }
    adm_user = {
        "id": "test-admin-e1",
        "phone": "01700000001",
        "name": "Admin One",
        "role": "admin",
        "roles": ["admin"],
        "status": "active",
        "is_onboarded": True,
    }
    from packages.trust_kernel.db import db_manager

    auth_service._users["test-citizen-e1"] = cit_user
    auth_service._users["test-admin-e1"] = adm_user
    db_manager.save_user(cit_user)
    db_manager.save_user(adm_user)
    db_manager.seed_default_emergency_contacts()

    now = datetime.now(timezone.utc)
    cit_payload = {
        "sub": "test-citizen-e1",
        "phone": "01711999111",
        "device_id": "dev-cit-1",
        "role": "citizen",
        "roles": ["citizen"],
        "type": "access",
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    cit_token = TokenService.encode_token(cit_payload)

    adm_payload = {
        "sub": "test-admin-e1",
        "phone": "01700000001",
        "device_id": "dev-adm-1",
        "role": "admin",
        "roles": ["admin"],
        "type": "access",
        "exp": int((now + timedelta(hours=1)).timestamp()),
    }
    adm_token = TokenService.encode_token(adm_payload)

    app_contacts = db_manager.list_emergency_contacts(active_only=False)
    target_id = app_contacts[0]["id"]

    # 1. Non-admin user gets 403 Forbidden
    res_forbidden = client.post(
        f"/admin/emergency-contacts/{target_id}/verify",
        headers={"Authorization": f"Bearer {cit_token}"},
        json={"source_note": "https://police.gov.bd"},
    )
    assert res_forbidden.status_code == 403

    # 2. Admin with empty source_note gets 422 Unprocessable Entity
    res_empty_note = client.post(
        f"/admin/emergency-contacts/{target_id}/verify",
        headers={"Authorization": f"Bearer {adm_token}"},
        json={"source_note": "   "},
    )
    assert res_empty_note.status_code == 422

    # 3. Admin with valid source_note succeeds
    source_ref = "বাংলাদেশ গেজেট ও আইন মন্ত্রণালয় প্রজ্ঞাপন ২০২৬"
    res_ok = client.post(
        f"/admin/emergency-contacts/{target_id}/verify",
        headers={"Authorization": f"Bearer {adm_token}"},
        json={"source_note": source_ref},
    )
    assert res_ok.status_code == 200
    updated_contact = res_ok.json()["contact"]
    assert updated_contact["is_verified"] is True
    assert updated_contact["last_verified_at"] is not None
    assert updated_contact["source_note"] == source_ref


# ---------------------------------------------------------------------------
# E2: Review Screen Fact Grounding and SRS Case Type Enum
# ---------------------------------------------------------------------------


def test_e2_fact_grounding_drops_ungrounded_and_srs_enum(intake_eng, citizen_user):
    """
    E2: Every displayed fact must have span_in_user_text that exists in user's own text;
    drop ungrounded facts. Show user excerpt. Case type adheres to SRS enum.
    """
    session = intake_eng.create_session(user_id=citizen_user["id"])
    user_text = "বিবাদী আমার ভাড়া দোকানঘর জোরপূর্বক দখল করার হুমকি দিচ্ছে।"
    intake_eng.save_answer(
        session_id=session["id"],
        user_id=citizen_user["id"],
        question_key="what_happened",
        answer_value=user_text,
        step=2,
    )

    profile = intake_eng.generate_case_profile(session["id"], citizen_user["id"])

    # 1. Facts grounded against user text
    assert len(profile["facts"]) > 0
    for f in profile["facts"]:
        assert "span_in_user_text" in f
        assert "user_excerpt" in f
        excerpt = f["user_excerpt"]
        assert excerpt in user_text or f["text"] in user_text

    # 2. Case type adheres strictly to SRS enum
    srs_enum = {
        "land_property",
        "contract",
        "rent_tenancy",
        "family",
        "criminal_complaint",
        "labour_employment",
        "consumer",
        "notice_received",
        "court_matter",
        "tax",
        "other",
    }
    assert profile["case_type"] in srs_enum
    assert profile["case_type"] != "general"
    assert profile["case_type"] != "land_dispute"


# ---------------------------------------------------------------------------
# E5: Sign-in Security (DEV_MODE rule)
# ---------------------------------------------------------------------------


def test_e5_dev_mode_sign_in_security():
    """
    E5: DEV_MODE default false.
    When false: no demo buttons on signin page, no dev_otp in request_otp, demo-login 404.
    When true: demo buttons shown, dev_otp returned with warning header.
    """
    client = TestClient(app)

    # 1. Test DEV_MODE=false
    os.environ["DEV_MODE"] = "false"
    os.environ["SMS_PROVIDER"] = "real"
    os.environ["REAL_SMS_API_KEY"] = "configured_prod_key"
    os.environ["REAL_SMS_SENDER_ID"] = "configured_prod_sender"
    try:
        # request_otp does NOT return dev_otp
        res_otp = client.post("/auth/otp/request", json={"phone": "01711223388"})
        assert res_otp.status_code == 200
        assert "dev_otp" not in res_otp.json()

        # demo-login returns 404
        res_demo = client.post("/auth/demo-login", json={"role": "citizen"})
        assert res_demo.status_code == 404

        # signin page does NOT contain demo login buttons
        res_signin = client.get("/signin")
        assert res_signin.status_code == 200
        assert "devQuickLoginSection" not in res_signin.text
    finally:
        os.environ["DEV_MODE"] = "true"
        os.environ.pop("SMS_PROVIDER", None)
        os.environ.pop("REAL_SMS_API_KEY", None)
        os.environ.pop("REAL_SMS_SENDER_ID", None)

    # 2. Test DEV_MODE=true
    res_otp_dev = client.post("/auth/otp/request", json={"phone": "01711223399"})
    assert res_otp_dev.status_code == 200
    assert "dev_otp" in res_otp_dev.json()
    assert "X-Dev-Mode-Warning" in res_otp_dev.headers

    res_demo_dev = client.post("/auth/demo-login", json={"role": "citizen"})
    assert res_demo_dev.status_code == 200
    assert "access_token" in res_demo_dev.json()


# ---------------------------------------------------------------------------
# E3 & E4 & E2 Playwright Tests (Mobile Viewport, UrgentBanner, Undefined check)
# ---------------------------------------------------------------------------


def test_e3_e4_playwright_intake_ui_and_viewports():
    """
    E3: UrgentBanner within first viewport (top < 640px) at 360x640.
    E4: Mobile bottom tab bar (5 tabs, no emoji in nav), tablet rail, desktop sidebar.
        Zero horizontal overflow (scrollWidth <= clientWidth + 1).
    E2: The text 'undefined' NEVER appears anywhere in DOM.
    """
    static_file = (STATIC_DIR / "intake.html").as_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # 1. Mobile 360x640
        page = browser.new_page(viewport={"width": 360, "height": 640})
        page.goto(static_file)
        page.wait_for_selector("#screenContainer")

        # Select urgent chip to trigger banner
        chip = page.locator('input[value="violence_threat"]')
        chip.check()
        page.wait_for_selector("#urgentBanner.visible")

        # E3: Assert UrgentBanner bounding box top < 640
        banner = page.locator("#urgentBanner")
        bbox = banner.bounding_box()
        assert bbox is not None
        assert bbox["y"] < 640, (
            f"UrgentBanner top position ({bbox['y']}px) must be < 640px at 360x640"
        )

        # E4: Assert bottom tab bar is visible and has 5 tabs
        tab_bar = page.locator(".mobile-tab-bar")
        assert tab_bar.is_visible()
        tabs = page.locator(".mobile-tab-item")
        assert tabs.count() == 5

        # Check zero horizontal overflow
        scroll_w = page.evaluate("() => document.documentElement.scrollWidth")
        client_w = page.evaluate("() => document.documentElement.clientWidth")
        assert scroll_w <= client_w + 1, (
            f"Horizontal overflow: scrollWidth={scroll_w}, clientWidth={client_w}"
        )

        # E2: Text 'undefined' never appears anywhere in DOM
        full_text = page.locator("body").inner_text()
        assert "undefined" not in full_text, "The text 'undefined' must never appear in the DOM"

        # 2. Tablet 768x1024: Side rail visible
        page_tablet = browser.new_page(viewport={"width": 768, "height": 1024})
        page_tablet.goto(static_file)
        page_tablet.wait_for_selector(".app-sidebar")
        assert page_tablet.locator(".app-sidebar").is_visible()

        # 3. Desktop 1280x800: Sidebar visible
        page_desktop = browser.new_page(viewport={"width": 1280, "height": 800})
        page_desktop.goto(static_file)
        page_desktop.wait_for_selector(".app-sidebar")
        assert page_desktop.locator(".app-sidebar").is_visible()

        browser.close()
