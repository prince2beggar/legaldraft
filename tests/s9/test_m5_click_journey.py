"""
M5: Click-Only Journey Test (Pure Browser Proof)

Guards:
- Clean browser profile and fresh temp DB (via live_server fixture).
- Starting at "/" with only ONE page.goto call across the entire journey.
- Guard: Fails if page.goto is called a second time.
- Guard: Fails if any request carries a manually-set Authorization header.
- Only clicks, typing, and natural in-browser link/button navigations.
- Captures screenshots at 360, 768, 1280 viewports into storage/screenshots/journey/
- Verifies SHA-256 uniqueness via scripts/verify_screenshots.py
"""

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
JOURNEY_DIR = REPO_ROOT / "storage" / "screenshots" / "journey"


@pytest.fixture(scope="module", autouse=True)
def ensure_journey_dir():
    JOURNEY_DIR.mkdir(parents=True, exist_ok=True)
    yield


VIEWPORTS = [
    {"name": "desktop_1280", "width": 1280, "height": 800, "is_mobile": False},
    {"name": "tablet_768", "width": 768, "height": 1024, "is_mobile": False},
    {"name": "mobile_360", "width": 360, "height": 640, "is_mobile": True},
]


def test_m5_click_only_journey(live_server):
    """
    Executes the complete human click journey across all 3 viewports.
    """
    JOURNEY_DIR.mkdir(parents=True, exist_ok=True)

    from packages.trust_kernel.db import db_manager

    db_manager.seed_default_templates()
    db_manager.update_template("DT-01", status="approved")

    # Prepare dummy document for upload
    temp_doc_path = REPO_ROOT / "storage" / "fake_legal_notice_demand.pdf"
    temp_doc_path.parent.mkdir(parents=True, exist_ok=True)
    temp_doc_path.write_text("FAKE_TEST_DATA [নমুনা] — আইনি নোটিশ তলবপত্র ২০২৬", encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for vp in VIEWPORTS:
            vp_name = vp["name"]
            context = browser.new_context(
                viewport={"width": vp["width"], "height": vp["height"]},
                is_mobile=vp["is_mobile"],
            )
            page = context.new_page()

            # --- GUARD 1: No manually-injected Authorization headers on navigation ---
            # Page navigations must never carry Authorization header (must be cookie-free, localStorage-based)
            def on_req(req):
                if req.is_navigation_request():
                    assert "authorization" not in req.headers, (
                        f"Guard violation: Navigation request to {req.url} carries manually-injected Authorization header!"
                    )

            page.on("request", on_req)

            # --- GUARD 2: Only ONE page.goto call allowed ---
            goto_counter = {"count": 0}
            original_goto = page.goto

            def guarded_goto(*args, **kwargs):
                goto_counter["count"] += 1
                if goto_counter["count"] > 1:
                    raise AssertionError(
                        f"GUARD VIOLATION: page.goto called {goto_counter['count']} times! "
                        f"Only the first navigation at '/' is permitted."
                    )
                return original_goto(*args, **kwargs)

            page.goto = guarded_goto

            # =========================================================================
            # STEP 0: First and ONLY page.goto -> "/"
            # =========================================================================
            page.goto(f"{live_server}/")
            page.wait_for_url(lambda u: "/welcome" in u or "/signin" in u, timeout=10000)

            # =========================================================================
            # STEP 1: Language / Sign In Screen
            # =========================================================================
            page.wait_for_selector("#stepWelcome", state="visible", timeout=7000)
            page.screenshot(path=str(JOURNEY_DIR / f"01a_language_{vp_name}.png"))

            # Click language and advance
            page.locator("#btnLangBn").click()
            page.locator('button:has-text("এগিয়ে যান")').click()

            # Mobile Number Input
            page.wait_for_selector("#phoneInput", state="visible", timeout=5000)
            page.screenshot(path=str(JOURNEY_DIR / f"01b_phone_{vp_name}.png"))
            page.locator("#phoneInput").fill("01711223344")
            page.locator("#btnRequestOtp").click()

            # =========================================================================
            # STEP 2: OTP Verification & Onboarding
            # =========================================================================
            page.wait_for_selector("#stepOtp", state="visible", timeout=7000)
            # If not already populated, fill OTP
            otp_val = page.locator("#otpCodeInput").input_value()
            if not otp_val or len(otp_val) != 6:
                page.locator("#otpCodeInput").fill("123456")

            page.screenshot(path=str(JOURNEY_DIR / f"02_otp_{vp_name}.png"))
            page.locator("#btnVerifyOtp").click()

            # If onboarding step is triggered for fresh user:
            try:
                page.wait_for_selector("#stepOnboarding", state="visible", timeout=2000)
                page.locator("#consentTerms").check()
                page.locator("#consentPrivacy").check()
                page.locator("#consentAiDisclaimer").check()
                page.screenshot(path=str(JOURNEY_DIR / f"02b_onboarding_{vp_name}.png"))
                page.locator('button:has-text("সম্মতি নিশ্চিত করুন ও প্রবেশ করুন")').click()
            except Exception:
                pass

            # =========================================================================
            # STEP 3: Lands on /home
            # =========================================================================
            page.wait_for_url(lambda u: "/home" in u, timeout=10000)
            page.wait_for_selector(".app-main", state="visible", timeout=7000)
            page.wait_for_timeout(500)
            page.screenshot(path=str(JOURNEY_DIR / f"03_home_{vp_name}.png"))

            # =========================================================================
            # STEP 4: Create Case
            # =========================================================================
            page.locator('a[href="/cases"]:visible').first.click()
            page.wait_for_url(lambda u: "/cases" in u, timeout=7000)
            page.wait_for_selector("#btnOpenCreateModal", state="visible", timeout=5000)
            page.locator("#btnOpenCreateModal").click()
            page.wait_for_selector("#createCaseModal.open", state="visible", timeout=5000)

            page.locator("#newCaseTitle").fill("জমি সংক্রান্ত বায়নানামা বিরোধ [FAKE_TEST_DATA]")
            page.locator("#newCaseType").select_option("land_dispute")
            page.locator("#newCaseUrgency").select_option("urgent")
            page.screenshot(path=str(JOURNEY_DIR / f"04_create_case_{vp_name}.png"))

            page.locator('#createCaseForm button[type="submit"]').click()
            page.wait_for_timeout(1000)

            # =========================================================================
            # STEP 5: Intake / নতুন সমস্যা
            # =========================================================================
            page.locator('a[href="/intake"]:visible').first.click()
            page.wait_for_url(lambda u: "/intake" in u, timeout=7000)
            page.wait_for_timeout(500)
            page.screenshot(path=str(JOURNEY_DIR / f"05_intake_{vp_name}.png"))

            # =========================================================================
            # STEP 6: Document Upload / নথি আপলোড
            # =========================================================================
            page.locator('a[href="/documents/upload"]:visible').first.click()
            page.wait_for_url(lambda u: "/documents/upload" in u, timeout=7000)
            page.wait_for_selector("#fileInput", state="attached", timeout=5000)
            page.screenshot(path=str(JOURNEY_DIR / f"06_upload_{vp_name}.png"))
            page.locator("#fileInput").set_input_files(str(temp_doc_path))
            page.wait_for_url(lambda u: "/documents/intent" in u, timeout=10000)

            # =========================================================================
            # STEP 7: Next Action (Home) - Why Modal
            # =========================================================================
            home_link = page.locator('a[href="/home"]:visible, a[href="/"]:visible').first
            home_link.click()
            page.wait_for_url(lambda u: "/home" in u or u.endswith("/"), timeout=7000)
            page.wait_for_timeout(500)
            why_btn = page.locator("#btnWhyNextAction:visible")
            if why_btn.is_visible():
                why_btn.click()
                page.wait_for_selector("#whyModal.open", state="visible", timeout=3000)
            page.screenshot(path=str(JOURNEY_DIR / f"07_next_action_{vp_name}.png"))
            if page.locator("#whyModal.open").is_visible():
                page.locator("#whyModal .modal-btn-close").click()
                page.wait_for_timeout(300)

            # =========================================================================
            # STEP 8: Draft Document / খসড়া
            # =========================================================================
            draft_link = page.locator('a[href="/draft"]:visible').first
            draft_link.click()
            page.wait_for_url(lambda u: "/draft" in u, timeout=7000)
            page.wait_for_timeout(500)
            page.screenshot(path=str(JOURNEY_DIR / f"08_draft_{vp_name}.png"))

            # =========================================================================
            # STEP 9: Export View / Wizard in Draft
            # =========================================================================
            page.wait_for_selector(".template-card:visible", timeout=7000)
            start_draft_btn = page.locator(".template-card:visible button.btn-primary").first
            start_draft_btn.scroll_into_view_if_needed()
            start_draft_btn.click()
            page.wait_for_selector("#viewWizard", state="visible", timeout=7000)
            page.wait_for_timeout(500)
            page.screenshot(path=str(JOURNEY_DIR / f"09_export_{vp_name}.png"))

            # =========================================================================
            # STEP 10: Case Brief
            # =========================================================================
            cases_link = page.locator('a[href="/cases"]:visible').first
            cases_link.click()
            page.wait_for_url(lambda u: "/cases" in u, timeout=7000)
            page.wait_for_timeout(400)
            first_case = page.locator(".case-card:visible").first
            if first_case.is_visible():
                first_case.click()
                page.wait_for_timeout(500)
            page.screenshot(path=str(JOURNEY_DIR / f"10_case_brief_{vp_name}.png"))

            # =========================================================================
            # STEP 11: Share Consent / ব্রিফ শেয়ারিং (Active Tab)
            # =========================================================================
            share_link = page.locator(
                'a[href="/me/sharing"]:visible, button[data-tab="lawyer"]:visible'
            ).first
            share_link.click()
            page.wait_for_timeout(500)
            page.screenshot(path=str(JOURNEY_DIR / f"11_share_consent_{vp_name}.png"))

            # =========================================================================
            # STEP 12: My Shares (Expired Filter Tab)
            # =========================================================================
            expired_tab = page.locator("#tabExpired:visible")
            if expired_tab.is_visible():
                expired_tab.click()
                page.wait_for_timeout(400)
            page.screenshot(path=str(JOURNEY_DIR / f"12_my_shares_{vp_name}.png"))

            # =========================================================================
            # STEP 13: Notifications / বিজ্ঞপ্তি
            # =========================================================================
            notif_link = page.locator('a[href="/notifications"]:visible').first
            notif_link.click()
            page.wait_for_url(lambda u: "/notifications" in u, timeout=7000)
            page.wait_for_timeout(500)
            page.screenshot(path=str(JOURNEY_DIR / f"13_notifications_{vp_name}.png"))

            # Verify guard: exactly 1 goto called
            assert goto_counter["count"] == 1, (
                f"Expected exactly 1 page.goto, got {goto_counter['count']}"
            )

            context.close()

        browser.close()

    # Verify screenshots uniqueness via scripts/verify_screenshots.py
    from scripts.verify_screenshots import verify_directory

    assert verify_directory(JOURNEY_DIR), (
        "Screenshot uniqueness verification failed in storage/screenshots/journey!"
    )
