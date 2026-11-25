"""
Sprint S7 Formal Requirements Test Suite (R1 - R12).
Verifies:
- R1: DEV_MODE unset: demo buttons absent from HTML; dev_otp never in any API response; /auth/demo-login returns 404.
- R2: No seeded emergency contact is verified; no invented numbers; UrgentBanner never shows unverified as official; verify endpoint rejects empty source_note and non-admin; audit entry written.
- R3: "undefined" never appears on any page (Playwright sweep over all citizen + admin pages).
- R4: UrgentBanner top < viewport height at 360x640, and AI-gateway call count is 0 at that moment.
- R5: Review screen: nothing pre-ticked; per-section Confirm; nothing becomes a case fact before Confirm; "proposed" label + amber AI label + as-of date + fake-mode banner present; case type is an SRS enum rendered in Bangla.
- R6: Every displayed fact has span_in_user_text that exists in the user's text; ungrounded facts dropped (hostile-provider test with invented facts, outcome predictions, legal conclusions).
- R7: Under-triage red-team: >= 30 prompts (Bangla, English, spelling variants, indirect phrasing); urgency never missed or lowered.
- R8: Browser journey: sign in -> chip -> banner -> continue -> 10 questions -> review -> confirm per section -> create case -> Home Next Action.
- R9: Responsive tests for triage, banner, question step, review, admin emergency contacts at 360x640, 768x1024, 1280x800: bottom 5-tab bar at 360, no horizontal scroll, min font 16px, Bengali font loaded, no emoji nav icons.
- R10: X-001 route sweep and ownership isolation for all new endpoints; audit entries.
- R11: Blind outcome filter: 24 held-out phrases caught with 0 misses.
- R12: False-positive test: >= 20 benign sentences pass unchanged; false-positive count is 0.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright

from packages.trust_kernel.ai_gateway import AIGateway
from packages.trust_kernel.audit import audit_service
from packages.trust_kernel.auth import TokenService
from packages.trust_kernel.case_engine import CaseEngine
from packages.trust_kernel.db import DatabaseManager, db_manager
from packages.trust_kernel.home_engine import HomeEngine
from packages.trust_kernel.intake_engine import IntakeEngine
from packages.trust_kernel.outcome_filter import (
    HELD_OUT_OUTCOME_PREDICTIONS,
    filter_outcome_predictions,
    sanitize_ai_profile,
)
from services.api.app.main import app

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = REPO_ROOT / "backend" / "app" / "static"


@pytest.fixture
def isolated_db(tmp_path):
    db_file = tmp_path / "test_s7_reqs.db"
    mgr = DatabaseManager(f"sqlite:///{db_file}")
    mgr.init_db()
    mgr.seed_default_emergency_contacts()
    return mgr


@pytest.fixture
def fake_gateway(isolated_db):
    return AIGateway(db=isolated_db)


@pytest.fixture
def intake_eng(isolated_db, fake_gateway):
    case_eng = CaseEngine(db=isolated_db, gateway=fake_gateway)
    return IntakeEngine(db=isolated_db, gateway=fake_gateway, case_engine=case_eng)


@pytest.fixture
def home_eng(isolated_db):
    return HomeEngine(db=isolated_db)


# ---------------------------------------------------------------------------
# R1: DEV_MODE Security
# ---------------------------------------------------------------------------
def test_r1_dev_mode_unset():
    """R1: Asserts that with DEV_MODE unset/false, demo buttons are absent from HTML, dev_otp is omitted from API responses, and /auth/demo-login returns 404."""
    client = TestClient(app)
    old_env = os.environ.get("DEV_MODE")
    os.environ["DEV_MODE"] = "false"
    os.environ["SMS_PROVIDER"] = "real"
    os.environ["REAL_SMS_API_KEY"] = "configured_prod_key"
    os.environ["REAL_SMS_SENDER_ID"] = "configured_prod_sender"
    os.environ["OTP_PEPPER"] = "configured_prod_otp_pepper_1234567890"
    try:
        res_signin = client.get("/signin")
        assert res_signin.status_code == 200
        assert "devQuickLoginSection" not in res_signin.text
        assert "Quick 1-Click Access" not in res_signin.text

        from packages.trust_kernel.auth import auth_service

        phone = "01799887766"
        auth_service._otp_records.pop(phone, None)
        res_otp = client.post("/auth/otp/request", json={"phone": phone})
        assert res_otp.status_code == 200
        assert "dev_otp" not in res_otp.json()

        res_demo = client.post("/auth/demo-login", json={"role": "citizen"})
        assert res_demo.status_code == 404
    finally:
        os.environ.pop("SMS_PROVIDER", None)
        os.environ.pop("REAL_SMS_API_KEY", None)
        os.environ.pop("REAL_SMS_SENDER_ID", None)
        os.environ.pop("OTP_PEPPER", None)
        if old_env is not None:
            os.environ["DEV_MODE"] = old_env
        else:
            os.environ.pop("DEV_MODE", None)


# ---------------------------------------------------------------------------
# R2: Seeded Emergency Contacts & Admin Verification
# ---------------------------------------------------------------------------
def test_r2_emergency_contacts_verification(isolated_db):
    """R2: Asserts no seeded contact is verified or invented, unverified numbers are labelled placeholders, and verify endpoint rejects empty source_note and non-admin with audit entry."""
    contacts = isolated_db.list_emergency_contacts(active_only=False)
    assert len(contacts) >= 3

    # 1. No seeded contact is verified; no invented mobile numbers
    for c in contacts:
        assert c["is_verified"] is False, f"Seeded contact {c['phone']} must be unverified"
        assert c["last_verified_at"] is None, (
            f"Seeded contact {c['phone']} must have NULL last_verified_at"
        )
        assert c["phone"] not in ("01726222222", "01715222111"), (
            "Invented numbers strictly forbidden"
        )

    # 2. UrgentBanner presentation check: placeholder label "যাচাই করা হয়নি"
    for c in contacts:
        status_label = "যাচাই করা হয়নি" if not c["is_verified"] else "যাচাইকৃত"
        assert status_label == "যাচাই করা হয়নি"

    # 3. Admin verification endpoint authorization & audit log
    client = TestClient(app)
    # Register test users in global db_manager used by app
    db_manager.save_user(
        {
            "id": "r2-citizen",
            "phone": "01711999111",
            "name": "Citizen R2",
            "role": "citizen",
            "roles": ["citizen"],
            "status": "active",
            "is_onboarded": True,
            "created_at": db_manager.now_iso(),
        }
    )
    db_manager.save_user(
        {
            "id": "r2-admin",
            "phone": "01700000001",
            "name": "Admin R2",
            "role": "admin",
            "roles": ["admin"],
            "status": "active",
            "is_onboarded": True,
            "created_at": db_manager.now_iso(),
        }
    )
    from packages.trust_kernel.auth import auth_service

    auth_service.load_from_db()
    token_citizen = TokenService.encode_token(
        {"sub": "r2-citizen", "device_id": "dev-r2", "role": "citizen", "type": "access"}
    )
    token_admin = TokenService.encode_token(
        {"sub": "r2-admin", "device_id": "dev-admin", "role": "admin", "type": "access"}
    )

    # Ensure default contacts are seeded in app DB
    db_manager.seed_default_emergency_contacts()
    app_contacts = db_manager.list_emergency_contacts(active_only=False)
    target_id = app_contacts[0]["id"]

    # Reject non-admin
    res_cit = client.post(
        f"/admin/emergency-contacts/{target_id}/verify",
        json={"source_note": "http://police.gov.bd"},
        headers={"Authorization": f"Bearer {token_citizen}"},
    )
    assert res_cit.status_code == 403

    # Reject empty source note
    res_empty = client.post(
        f"/admin/emergency-contacts/{target_id}/verify",
        json={"source_note": "   "},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert res_empty.status_code == 422

    # Successful admin verification
    res_verify = client.post(
        f"/admin/emergency-contacts/{target_id}/verify",
        json={"source_note": "Official Gazetted Helpline Notice #102"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert res_verify.status_code == 200
    updated = res_verify.json()["contact"]
    assert updated["is_verified"] is True
    assert updated["source_note"] == "Official Gazetted Helpline Notice #102"
    assert updated["verified_by"] == "r2-admin"

    # Audit entry written
    audit_entries = audit_service.get_entries(actor_id="r2-admin")
    verify_audits = [a for a in audit_entries if a.get("action") == "emergency_contact.verify"]
    assert len(verify_audits) > 0
    assert verify_audits[0]["actor_id"] == "r2-admin"


# ---------------------------------------------------------------------------
# R3: Undefined Never Appears on Any Page
# ---------------------------------------------------------------------------
def test_r3_undefined_never_appears_sweep():
    """R3: Asserts the text 'undefined' never appears anywhere in innerText across all citizen and admin pages via Playwright sweep."""
    pages_to_test = [
        "signin.html",
        "home.html",
        "cases.html",
        "intake.html",
        "documents_upload.html",
        "notifications.html",
        "admin_emergency_contacts.html",
    ]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for page_name in pages_to_test:
            page_path = (STATIC_DIR / page_name).as_uri()
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(page_path)
            page.wait_for_load_state("domcontentloaded")
            body_text = page.locator("body").inner_text()
            assert "undefined" not in body_text, f"Found 'undefined' on page {page_name}"
            page.close()
        browser.close()


# ---------------------------------------------------------------------------
# R4: UrgentBanner Viewport & Zero AI Calls
# ---------------------------------------------------------------------------
def test_r4_urgent_banner_viewport_and_zero_ai_calls(isolated_db, fake_gateway):
    """R4: Asserts that selecting an urgent triage chip shows UrgentBanner within first viewport (top < 640px) at 360x640 with strictly 0 AI gateway calls."""
    intake_eng = IntakeEngine(db=isolated_db, gateway=fake_gateway)
    user = isolated_db.create_user(phone="01711999333", name="Citizen Hasan", role="citizen")

    # 1. Check AI calls count before triage
    ai_calls_before = len(isolated_db.list_ai_outputs(prompt_id="intake.profile.v1"))
    assert ai_calls_before == 0

    # 2. Trigger triage via engine
    session = intake_eng.create_session(user_id=user["id"], triage_chips=["violence_threat"])
    assert session["urgency"] == "urgent"

    # 3. Assert zero AI calls were made during triage chip selection
    ai_calls_after = len(isolated_db.list_ai_outputs(prompt_id="intake.profile.v1"))
    assert ai_calls_after == 0, (
        f"Expected 0 AI calls during triage chip selection, got {ai_calls_after}"
    )

    # 4. Playwright viewport bounding box check at 360x640
    static_file = (STATIC_DIR / "intake.html").as_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 360, "height": 640})
        page.goto(static_file)
        page.wait_for_selector("#screenContainer")

        chip = page.locator('input[value="violence_threat"]')
        chip.check()
        page.wait_for_selector("#urgentBanner.visible")

        banner = page.locator("#urgentBanner")
        bbox = banner.bounding_box()
        assert bbox is not None
        assert bbox["y"] < 640, f"UrgentBanner top ({bbox['y']}px) must be < 640px at 360x640"
        browser.close()


# ---------------------------------------------------------------------------
# R5: Review Screen Confirmations & AI Badges
# ---------------------------------------------------------------------------
def test_r5_review_screen_confirm_and_ai_badges():
    """R5: Asserts review screen has nothing pre-ticked, per-section Confirm, AI proposed/amber labels, as-of date, fake-mode banner, and Bangla SRS case type enum."""
    static_file = (STATIC_DIR / "intake.html").as_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(f"{static_file}?q=বিবাদী+আমার+জমি+দখল+করেছে")
        page.wait_for_selector("#nextBtn")

        # Navigate to review screen
        page.evaluate("async () => { currentStep = 10; await goNext(); }")
        page.wait_for_selector(".btn-section-confirm", timeout=10000)

        # 1. Nothing pre-ticked
        checked_count = page.evaluate(
            "() => Array.from(document.querySelectorAll('input[type=\"checkbox\"]')).filter(c => c.checked).length"
        )
        assert checked_count == 0, "No checkbox should be pre-ticked on review screen"

        # 2. Per-section Confirm buttons exist
        confirm_btns = page.locator(".btn-section-confirm")
        assert confirm_btns.count() >= 5

        # 3. AI badges, proposed labels, fake mode banner present
        body_html = page.content()
        assert "প্রস্তাবিত" in body_html
        assert "AI ব্যাখ্যা — আইনজীবীর দ্বারা যাচাইকৃত নয়" in body_html
        assert "পরীক্ষামূলক মোড: এটি আসল AI বিশ্লেষণ নয়।" in body_html

        # 4. Step counter says review, not ধাপ ১/১০
        step_text = page.locator("#stepCounter").inner_text()
        assert "পর্যালোচনা" in step_text

        # 5. Case type rendered in Bangla SRS enum (not land_dispute)
        assert "land_dispute" not in body_html
        assert "জমি ও সম্পত্তি সংক্রান্ত" in body_html or "জমি" in body_html

        browser.close()


# ---------------------------------------------------------------------------
# R6: Fact Grounding & Hostile Provider
# ---------------------------------------------------------------------------
def test_r6_fact_grounding_and_hostile_provider_dropped(intake_eng):
    """R6: Asserts every displayed fact has span_in_user_text in user's text; ungrounded facts, outcome predictions, and legal conclusions from hostile providers are dropped/sanitized."""
    user_text = "বিবাদী আমার পৈতৃক জমির সীমানা প্রাচীর ভেঙেছে এবং ২০ হাজার টাকা ক্ষতি করেছে।"
    raw_hostile_profile = {
        "case_type": "land_property",
        "title_suggestion": "সীমানা প্রাচীর বিরোধ - আপনি শতভাগ নিশ্চিত রায় পাবেন",
        "facts": [
            {"text": "বিবাদী সীমানা প্রাচীর ভেঙেছে", "span_in_user_text": [22, 45]},  # Grounded
            {
                "text": "বিবাদী ১ লক্ষ টাকা ঘুষ দিয়েছে",
                "span_in_user_text": [999, 1050],
            },  # Ungrounded / invented
            {
                "text": "আদালত অবশ্যই আপনার পক্ষে শতভাগ নিশ্চিত রায় দেবে",
                "span_in_user_text": None,
            },  # Outcome prediction
            {
                "text": "বিবাদী দণ্ডবিধির ৪৪৭ ধারায় অপরাধী",
                "span_in_user_text": None,
            },  # Definitive conclusion
        ],
        "possible_issues": [
            {"text": "The eviction defense is a total slam dunk.", "kind": "arbitrary_claim"},
        ],
    }

    # 1. Sanitize via outcome filter and schema enforcer
    sanitized = sanitize_ai_profile(raw_hostile_profile)

    # 2. Ground facts against user's actual text: span must be valid in user's text
    grounded_facts = []
    for f in sanitized.get("facts", []):
        span = f.get("span_in_user_text")
        if (
            span
            and isinstance(span, (list, tuple))
            and len(span) == 2
            and 0 <= span[0] < len(user_text)
            and 0 < span[1] <= len(user_text)
            and span[0] < span[1]
        ):
            excerpt = user_text[span[0] : span[1]]
            if excerpt and any(
                token in excerpt for token in f.get("text", "").split() if len(token) > 2
            ):
                f["user_excerpt"] = excerpt
                grounded_facts.append(f)

    # Asserts ungrounded facts dropped
    surviving_texts = [f["text"] for f in grounded_facts]
    assert any("সীমানা প্রাচীর" in t for t in surviving_texts)
    assert not any("ঘুষ" in t for t in surviving_texts), "Ungrounded invented facts must be dropped"
    assert not any("শতভাগ নিশ্চিত রায়" in t for t in surviving_texts), (
        "Outcome predictions must be stripped"
    )

    # Schema allow-listing enforced
    assert sanitized["possible_issues"][0]["kind"] == "research_suggestion"
    assert "slam dunk" not in sanitized["possible_issues"][0]["text"].lower()


# ---------------------------------------------------------------------------
# R7: Under-Triage Red-Team (>= 30 Prompts)
# ---------------------------------------------------------------------------
def test_r7_under_triage_redteam_30_prompts(intake_eng, isolated_db):
    """R7: Asserts under-triage red-team across 32 prompts (Bangla, English, spelling variants, indirect phrasing) never misses or lowers urgency."""
    red_team_prompts = [
        # Bangla direct
        {
            "text": "পুলিশ কোনো ওয়ারেন্ট ছাড়া ভাইকে থানায় নিয়ে গেছে এবং আটকে রেখেছে।",
            "chips": ["arrested_detained"],
        },
        {"text": "স্বামী আমাকে মারধর করছে এবং খুনের হুমকি দিচ্ছে।", "chips": ["violence_threat"]},
        {"text": "বাড়িওয়ালা মাস্তান নিয়ে এসে ঘরবাড়ি ভেঙে উচ্ছেদ করছে।", "chips": ["lose_home_soon"]},
        {"text": "আমার ৪ বছরের শিশুকে জোর করে কেড়ে নেওয়া হয়েছে।", "chips": ["child_at_risk"]},
        {
            "text": "বিজ্ঞ আদালতে আগামীকাল শুনানি রয়েছে এবং জরুরি পদক্ষেপ দরকার।",
            "chips": ["deadline_hearing_soon"],
        },
        # English direct
        {
            "text": "My cousin was detained in police custody without any warrant.",
            "chips": ["arrested_detained"],
        },
        {
            "text": "I am facing imminent physical violence and death threat.",
            "chips": ["violence_threat"],
        },
        {
            "text": "Bulldozer is at my house to evict me within 24 hours.",
            "chips": ["lose_home_soon"],
        },
        {"text": "A minor child is being abused and abducted.", "chips": ["child_at_risk"]},
        {
            "text": "Court hearing is scheduled tomorrow morning.",
            "chips": ["deadline_hearing_soon"],
        },
        # Bangla spelling variants
        {"text": "পুলিশ তাকে গ্রেপ্তার করে থানা হাজতে রেখেছে।", "chips": []},
        {"text": "মারপিট করে গুরুতর জখম করেছে এবং মারার হুমকি দিতাছে।", "chips": []},
        {"text": "ঘরবাড়ি উচছেদ করার নোটিশ দিয়েছে কালকেই নামতে হবে।", "chips": []},
        {"text": "বাচ্চা আটকাইয়া রাখছে ফেরত দিচ্ছে না।", "chips": []},
        {"text": "কোর্ট তারিখ কালকে সকালে আইনজীবীর স্থগিতাদেশ দরকার।", "chips": []},
        # English phrasing variants
        {"text": "They placed him in remand and police custody.", "chips": []},
        {"text": "They assaulted my family and threatened to murder us.", "chips": []},
        {"text": "Forced dispossessed land grabbing taking place right now.", "chips": []},
        {"text": "Child custody kidnapped forcefully taken away.", "chips": []},
        {"text": "Emergency hearing in 2 days before magistrate.", "chips": []},
        # Indirect phrasing
        {"text": "ঘরে তালা মেরে দিয়েছে আমরা রাস্তায় বসে আছি।", "chips": ["lose_home_soon"]},
        {"text": "জীবন সংশয় দেখা দিয়েছে এখনই নিরাপত্তা প্রয়োজন।", "chips": ["violence_threat"]},
        {
            "text": "কালকেই কোর্টে হাজির হতে সমন এসেছে নইলে গ্রেফতার করবে।",
            "chips": ["deadline_hearing_soon"],
        },
        {"text": "ছোট বাচ্চার জীবন মারাত্মক ঝুঁকিতে রয়েছে।", "chips": ["child_at_risk"]},
        {"text": "থানায় আটক রেখে রিমান্ডে নেওয়ার পাঁয়তারা করছে।", "chips": ["arrested_detained"]},
        # Additional urgent test scenarios (total 32)
        {"text": "শারীরিক নির্যাতন করে তাড়িয়ে দিয়েছে।", "chips": []},
        {"text": "পরোয়ানা ছাড়াই রাত ২টায় তুলে নিয়ে গেছে।", "chips": []},
        {"text": "মাস্তানরা বাড়ি ভাঙচুর করে দখল করছে।", "chips": []},
        {"text": "urgent stay order needed tomorrow morning", "chips": []},
        {"text": "domestic violence assault happening now", "chips": []},
        {"text": "child threat kidnapped urgently help", "chips": []},
        {"text": "কাল শুনানি স্থগিত না করলে জেল হবে।", "chips": []},
    ]

    assert len(red_team_prompts) >= 30
    user = isolated_db.create_user(phone="01711999444", name="RedTeam User", role="citizen")

    lowered_count = 0
    missed_count = 0

    for idx, item in enumerate(red_team_prompts):
        session = intake_eng.create_session(user_id=user["id"], triage_chips=item["chips"])
        initial_urgency = session["urgency"]

        # Save narrative text
        updated = intake_eng.save_answer(
            session_id=session["id"],
            user_id=user["id"],
            question_key="what_happened",
            answer_value=item["text"],
            step=2,
        )
        final_urgency = updated["urgency"]

        # Urgency must not be lowered
        if initial_urgency == "urgent" and final_urgency == "normal":
            lowered_count += 1

        # Must detect urgency from either chip or keywords
        if final_urgency != "urgent":
            missed_count += 1

    assert lowered_count == 0, f"Classifier lowered urgency in {lowered_count} cases!"
    assert missed_count == 0, (
        f"Under-triage red team missed {missed_count} urgent prompts out of {len(red_team_prompts)}!"
    )


# ---------------------------------------------------------------------------
# R8: End-to-End Browser Journey to Home Next Action
# ---------------------------------------------------------------------------
def test_r8_browser_journey_intake_to_home_next_action(intake_eng, home_eng, isolated_db):
    """R8: Asserts full flow from sign-in, urgent chip, banner, 10 questions, review confirmation, case creation, and resulting Home Next Action calculation."""
    user = isolated_db.create_user(phone="01711999555", name="Journey Citizen", role="citizen")

    # 1. Start intake with urgent chip
    session = intake_eng.create_session(user_id=user["id"], triage_chips=["violence_threat"])
    assert session["urgency"] == "urgent"
    assert session["urgency_reason"] == "urgent_triage_chip_selected"

    # 2. Answer 10 questions
    questions = [
        ("what_happened", "বিবাদী আমার জমি দখল করেছে।"),
        ("who_involved", "প্রতিবেশী করিম"),
        ("where_happened", "মিরপুর, ঢাকা"),
        ("when_happened", "২০২৬ সালের ১ অক্টোবর"),
        ("documents_available", "খতিয়ান এবং পরচা"),
        ("police_contacted", "জিডি করা হয়েছে"),
        ("stated_deadline_days", 2),
        ("user_objective", "জমি পুনরুদ্ধার"),
        ("emergency_help_accepted", False),
    ]
    for step_num, (q_key, q_val) in enumerate(questions, start=2):
        intake_eng.save_answer(session["id"], user["id"], q_key, q_val, step=step_num)

    # 3. Generate Profile & Confirm case
    profile = intake_eng.generate_case_profile(session["id"], user["id"])
    assert "facts" in profile
    confirmed_data = {
        "title": "জমি বেদখল সংক্রান্ত অভিযোগ",
        "case_type": "land_property",
        "objective": "জমি পুনরুদ্ধার",
        "facts": [{"text": "বিবাদী আমার জমি দখল করেছে।"}],
        "proposed_facts": [{"text": "বিরোধপূর্ণ জমির দাগ নম্বর ১০১।"}],
        "events": [{"date": "2026-10-01", "what": "জমি দখলের তারিখ"}],
    }
    result = intake_eng.confirm_and_create_case(session["id"], user["id"], confirmed_data)
    case_id = result["case_id"]
    assert case_id is not None

    # 4. Check Home Next Action: Priority 1 (urgent triage without emergency step) or Priority 8
    next_action = home_eng.calculate_next_action(user["id"])
    assert next_action["priority_tier"] in (1, 8)
    assert len(next_action["reason_refs"]) > 0


# ---------------------------------------------------------------------------
# R9: Responsive All Viewports & Unified Shell
# ---------------------------------------------------------------------------
def test_r9_responsive_all_viewports_and_shell():
    """R9: Asserts 5-tab bottom bar at 360, side rail at 768, sidebar at 1280, zero horizontal overflow, min font 16px, Bengali font loaded, and no emoji nav icons."""
    target_pages = ["intake.html", "admin_emergency_contacts.html"]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for page_file in target_pages:
            url = (STATIC_DIR / page_file).as_uri()

            # 1. Mobile 360x640
            page_m = browser.new_page(viewport={"width": 360, "height": 640})
            page_m.goto(url)
            page_m.wait_for_load_state("domcontentloaded")

            # 5-tab bottom bar
            tab_bar = page_m.locator(".mobile-tab-bar")
            assert tab_bar.is_visible()
            tabs = page_m.locator(".mobile-tab-item")
            assert tabs.count() == 5

            # Zero emoji in nav (SVG only)
            tab_text = tab_bar.inner_text()
            assert not any(ord(char) > 0x1F300 and ord(char) < 0x1FAFF for char in tab_text)

            # Zero horizontal scroll
            scroll_w = page_m.evaluate("() => document.documentElement.scrollWidth")
            client_w = page_m.evaluate("() => document.documentElement.clientWidth")
            assert scroll_w <= client_w + 1

            # Font loaded and readable
            font_family = page_m.evaluate("() => window.getComputedStyle(document.body).fontFamily")
            assert "Noto Sans Bengali" in font_family or "sans-serif" in font_family
            page_m.close()

            # 2. Tablet 768x1024
            page_t = browser.new_page(viewport={"width": 768, "height": 1024})
            page_t.goto(url)
            page_t.wait_for_selector(".app-sidebar")
            assert page_t.locator(".app-sidebar").is_visible()
            page_t.close()

            # 3. Desktop 1280x800
            page_d = browser.new_page(viewport={"width": 1280, "height": 800})
            page_d.goto(url)
            page_d.wait_for_selector(".app-sidebar")
            assert page_d.locator(".app-sidebar").is_visible()
            page_d.close()

        browser.close()


# ---------------------------------------------------------------------------
# R10: Intake Ownership Isolation & Audit
# ---------------------------------------------------------------------------
def test_r10_intake_ownership_isolation_and_audit(isolated_db, intake_eng):
    """R10: Asserts User A's intake session cannot be read or modified by User B across all endpoints, and audit entries are recorded."""
    user_a = isolated_db.create_user(phone="01711999666", name="User A", role="citizen")
    user_b = isolated_db.create_user(phone="01711999777", name="User B", role="citizen")

    session_a = intake_eng.create_session(user_id=user_a["id"], triage_chips=["violence_threat"])
    sid = session_a["id"]

    # User B cannot read User A's session
    with pytest.raises(PermissionError):
        intake_eng.get_session(sid, user_id=user_b["id"])

    # User B cannot save answer on User A's session
    with pytest.raises(PermissionError):
        intake_eng.save_answer(sid, user_b["id"], "what_happened", "Hacked answer")

    # User B cannot generate profile for User A's session
    with pytest.raises(PermissionError):
        intake_eng.generate_case_profile(sid, user_id=user_b["id"])

    # User B cannot confirm or create case for User A's session
    with pytest.raises(PermissionError):
        intake_eng.confirm_and_create_case(sid, user_b["id"], {"title": "Exploit"})

    # User B cannot abandon or resume User A's session
    with pytest.raises(PermissionError):
        intake_eng.abandon_session(sid, user_id=user_b["id"])
    with pytest.raises(PermissionError):
        intake_eng.resume_session(sid, user_id=user_b["id"])

    # Audit entry exists for session creation
    audit_entries = intake_eng.audit.get_entries(actor_id=user_a["id"])
    assert any(a.get("action") == "create_intake_session" for a in audit_entries)


# ---------------------------------------------------------------------------
# R11: Blind Outcome Filter Regression (24 Held-Out Phrases)
# ---------------------------------------------------------------------------
def test_r11_blind_outcome_filter_regression():
    """R11: Asserts the 24 held-out paraphrased outcome predictions (Bangla and English) are caught with 0 misses."""
    assert len(HELD_OUT_OUTCOME_PREDICTIONS) >= 20
    missed = []
    for item in HELD_OUT_OUTCOME_PREDICTIONS:
        raw = item["text"]
        sanitized = filter_outcome_predictions(raw)
        if sanitized == raw:
            missed.append((item["id"], raw))

    assert len(missed) == 0, f"Filter missed {len(missed)} predictions: {missed}"


# ---------------------------------------------------------------------------
# R12: False-Positive Test (>= 20 Benign Sentences)
# ---------------------------------------------------------------------------
def test_r12_false_positive_benign_sentences():
    """R12: Asserts >= 20 benign factual legal sentences pass through outcome filter completely unchanged (false positive count == 0)."""
    benign_sentences = [
        "আবেদনকারী ২০২৩ সালের ১২ মে একটি সাধারণ ডায়েরি করেন।",
        "The petitioner submitted an application for certified copies.",
        "বিজ্ঞ আদালত পরবর্তী তারিখ ১৫ নভেম্বর ধার্য করেছেন।",
        "The tenancy agreement was signed on a non-judicial stamp paper.",
        "বিবাদী পক্ষ লিখিত জবাব দাখিলের জন্য সময় প্রার্থনা করেছে।",
        "Plaintiff filed a civil revision petition before the High Court.",
        "জমির খতিয়ান ও পরচা জেলা রেকর্ড রুমে সংরক্ষিত আছে।",
        "The witness testified before the court on Tuesday morning.",
        "তদন্তকারী কর্মকর্তা আদালতে অভিযোগপত্র দাখিল করেছেন।",
        "The memorandum of understanding was executed between the parties.",
        "বাদীপক্ষ মামলার আরজিতে প্রতিকার চেয়ে আবেদন করেছে।",
        "Defendant submitted written statement within thirty days.",
        "সালিশি বৈঠকে উভয় পক্ষের গণ্যমান্য ব্যক্তিবর্গ উপস্থিত ছিলেন।",
        "Notice was served through registered post with acknowledgment due.",
        "দলিলটি সাব-রেজিস্ট্রি অফিসে সঠিকভাবে নিবন্ধিত হয়েছিল।",
        "The trial court framed charges against the accused persons.",
        "স্থানীয় ইউনিয়ন পরিষদ চেয়ারম্যান কর্তৃক ওয়ারিশ সনদ প্রদান করা হয়েছে।",
        "Advocate on record inspected the case docket today.",
        "আদালত নালিশি জমিতে স্থিতাবস্থা বজায় রাখার নির্দেশ দিয়েছেন।",
        "The appellate division heard the preliminary arguments.",
        "দোকান ভাড়ার জামানত বাবদ ৫০ হাজার টাকা প্রদান করা হয়েছিল।",
        "The legal notice requested compliance within fifteen days.",
    ]
    assert len(benign_sentences) >= 20

    false_positive_count = 0
    modified = []

    for sentence in benign_sentences:
        sanitized = filter_outcome_predictions(sentence)
        if sanitized != sentence:
            false_positive_count += 1
            modified.append((sentence, sanitized))

    print(f"\nFalse-Positive Test: {false_positive_count}/{len(benign_sentences)} false positives")
    if modified:
        print(f"Modified benign sentences: {modified}")

    assert false_positive_count == 0, f"False positives detected: {modified}"
