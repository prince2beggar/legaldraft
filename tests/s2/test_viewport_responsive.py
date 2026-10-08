"""
Automated Responsive Viewport Test Suite and Screenshot Generator (SRS ADR-018 & S2 DoD).
Tests across three required viewports:
- Mobile: 360 x 640
- Tablet: 768 x 1024
- Desktop: 1280 x 800

Verifies:
1. Zero horizontal overflow (scrollWidth <= clientWidth + 1) at all viewports for:
   - Citizen Library (library.html)
   - Admin Knowledge Center (admin_sources.html)
   - Auth & Onboarding Flow (signin.html: Welcome, Signin, OTP, Onboarding)
   - Advocate Dashboard (index.html)
   - Admin Console (admin.html)
2. Responsive navigation adaptations: bottom nav on mobile, sidebar/rail on tablet/desktop.
3. Role-based navigation: Citizens must NEVER see Admin/Knowledge Center items in any navigation.
4. Pure language enforcement: Zero mixed English/Bangla titles in citizen UI.
5. Captures 12 verified screenshots in storage/screenshots/.
"""

from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = REPO_ROOT / "backend" / "app" / "static"
SCREENSHOTS_DIR = REPO_ROOT / "storage" / "screenshots"

VIEWPORTS = [
    {"name": "mobile_360", "width": 360, "height": 640, "is_mobile": True},
    {"name": "tablet_768", "width": 768, "height": 1024, "is_mobile": False},
    {"name": "desktop_1280", "width": 1280, "height": 800, "is_mobile": False},
]


@pytest.fixture(scope="module")
def browser_instance():
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


def test_citizen_library_responsive_and_screenshots(browser_instance):
    """Verifies Citizen Library at all 3 viewports and captures screenshots."""
    library_path = (STATIC_DIR / "library.html").as_uri()

    for vp in VIEWPORTS:
        context = browser_instance.new_context(
            viewport={"width": vp["width"], "height": vp["height"]}
        )
        page = context.new_page()
        page.goto(library_path)
        page.wait_for_selector("#resultsGrid")

        # 1. Zero horizontal scroll check
        scroll_width = page.evaluate("() => document.documentElement.scrollWidth")
        client_width = page.evaluate("() => document.documentElement.clientWidth")
        assert scroll_width <= client_width + 1, (
            f"Horizontal overflow detected in library.html at {vp['name']}: scrollWidth={scroll_width}, clientWidth={client_width}"
        )

        # 2. Check layout variant
        if vp["width"] < 640:
            assert page.locator(".mobile-bottom-nav").is_visible(), (
                "Bottom nav must be visible on mobile"
            )
        elif vp["width"] >= 1024:
            assert page.locator(".app-sidebar").is_visible(), "Sidebar must be visible on desktop"

        # 3. Capture search view screenshot
        search_shot = SCREENSHOTS_DIR / f"citizen_library_search_{vp['name']}.png"
        page.screenshot(path=str(search_shot))
        assert search_shot.exists()

        # 4. Open modal for source viewer & capture viewer screenshot
        first_explain_btn = page.locator(".btn-view-explain").first
        first_explain_btn.click()
        page.wait_for_selector("#passageModal.show")

        viewer_shot = SCREENSHOTS_DIR / f"source_viewer_{vp['name']}.png"
        page.screenshot(path=str(viewer_shot))
        assert viewer_shot.exists()

        context.close()


def test_admin_knowledge_center_responsive_and_screenshots(browser_instance):
    """Verifies Admin Knowledge Center at all 3 viewports and captures screenshots."""
    admin_path = (STATIC_DIR / "admin_sources.html").as_uri()

    for vp in VIEWPORTS:
        context = browser_instance.new_context(
            viewport={"width": vp["width"], "height": vp["height"]}
        )
        page = context.new_page()
        page.goto(admin_path)
        page.wait_for_selector("#sourcesTable")

        # 1. Zero horizontal scroll check
        scroll_width = page.evaluate("() => document.documentElement.scrollWidth")
        client_width = page.evaluate("() => document.documentElement.clientWidth")
        assert scroll_width <= client_width + 1, (
            f"Horizontal overflow detected in admin_sources.html at {vp['name']}: scrollWidth={scroll_width}, clientWidth={client_width}"
        )

        # 2. Check layout adaptation
        if vp["width"] < 640:
            assert page.locator(".mobile-bottom-nav").is_visible(), (
                "Bottom nav must be visible on mobile"
            )
        elif vp["width"] >= 1024:
            assert page.locator(".app-sidebar").is_visible(), "Sidebar must be visible on desktop"

        # 3. Capture Admin Knowledge Center list screenshot
        list_shot = SCREENSHOTS_DIR / f"admin_knowledge_center_list_{vp['name']}.png"
        page.screenshot(path=str(list_shot))
        assert list_shot.exists()

        # 4. Scroll to Diff & Approval flow and capture screenshot
        page.locator("#approveCard").scroll_into_view_if_needed()
        approve_shot = SCREENSHOTS_DIR / f"approve_flow_{vp['name']}.png"
        page.screenshot(path=str(approve_shot))
        assert approve_shot.exists()

        context.close()


def test_signin_flow_responsive(browser_instance):
    """Verifies sign-in, OTP, onboarding and welcome steps at 360, 768, 1280 viewports."""
    signin_path = (STATIC_DIR / "signin.html").as_uri()

    for vp in VIEWPORTS:
        context = browser_instance.new_context(
            viewport={"width": vp["width"], "height": vp["height"]}
        )
        page = context.new_page()
        page.goto(signin_path)
        page.wait_for_selector("#stepWelcome")

        # Check Step 1: Welcome
        scroll_w = page.evaluate("() => document.documentElement.scrollWidth")
        client_w = page.evaluate("() => document.documentElement.clientWidth")
        assert scroll_w <= client_w + 1, f"Overflow on welcome step at {vp['name']}"

        # Transition to Step 2: Signin
        page.evaluate("goToStep('Signin')")
        page.wait_for_selector("#stepSignin:not(.hidden)")
        scroll_w = page.evaluate("() => document.documentElement.scrollWidth")
        client_w = page.evaluate("() => document.documentElement.clientWidth")
        assert scroll_w <= client_w + 1, f"Overflow on signin step at {vp['name']}"

        # Transition to Step 3: OTP
        page.evaluate("goToStep('Otp')")
        page.wait_for_selector("#stepOtp:not(.hidden)")
        scroll_w = page.evaluate("() => document.documentElement.scrollWidth")
        client_w = page.evaluate("() => document.documentElement.clientWidth")
        assert scroll_w <= client_w + 1, f"Overflow on OTP step at {vp['name']}"

        # Transition to Step 4: Onboarding
        page.evaluate("goToStep('Onboarding')")
        page.wait_for_selector("#stepOnboarding:not(.hidden)")
        scroll_w = page.evaluate("() => document.documentElement.scrollWidth")
        client_w = page.evaluate("() => document.documentElement.clientWidth")
        assert scroll_w <= client_w + 1, f"Overflow on onboarding step at {vp['name']}"

        context.close()


def test_advocate_dashboard_responsive(browser_instance):
    """Verifies legacy Advocate dashboard (index.html) at 360, 768, 1280."""
    index_path = (STATIC_DIR / "index.html").as_uri()

    for vp in VIEWPORTS:
        context = browser_instance.new_context(
            viewport={"width": vp["width"], "height": vp["height"]}
        )
        page = context.new_page()
        page.goto(index_path)
        page.wait_for_selector("header")

        scroll_w = page.evaluate("() => document.documentElement.scrollWidth")
        client_w = page.evaluate("() => document.documentElement.clientWidth")
        # index.html has an overflow-x tabs nav; page body itself must remain contained
        assert scroll_w <= client_w + 1, (
            f"Horizontal overflow in advocate dashboard at {vp['name']}"
        )

        context.close()


def test_admin_portal_responsive(browser_instance):
    """Verifies Admin portal (admin.html) at 360, 768, 1280."""
    admin_path = (STATIC_DIR / "admin.html").as_uri()

    for vp in VIEWPORTS:
        context = browser_instance.new_context(
            viewport={"width": vp["width"], "height": vp["height"]}
        )
        page = context.new_page()
        page.goto(admin_path)
        page.wait_for_selector("body")

        scroll_w = page.evaluate("() => document.documentElement.scrollWidth")
        client_w = page.evaluate("() => document.documentElement.clientWidth")
        assert scroll_w <= client_w + 1, f"Horizontal overflow in admin portal at {vp['name']}"

        context.close()


def test_citizen_role_navigation_isolation(browser_instance):
    """Verifies that citizens NEVER see Admin or Knowledge Center links in navigation."""
    library_path = (STATIC_DIR / "library.html").as_uri()
    index_path = (STATIC_DIR / "index.html").as_uri()

    # 1. Citizen in Library view
    context = browser_instance.new_context()
    page = context.new_page()
    page.goto(library_path)

    # Assert no /admin or /admin/sources links anywhere in library page
    admin_links = page.locator('a[href^="/admin"]').count()
    assert admin_links == 0, f"Citizen library must have 0 admin links, found {admin_links}"

    # 2. Citizen in Advocate Dashboard (with ain_user_role='citizen')
    page2 = context.new_page()
    page2.add_init_script("localStorage.setItem('ain_user_role', 'citizen');")
    page2.goto(index_path)
    page2.wait_for_selector("header")

    # In index.html, admin link should be hidden for citizen
    admin_link_vis = page2.locator("#adminPortalLink").is_visible()
    assert not admin_link_vis, "Admin portal link must be hidden for citizen role"
    context.close()


def test_pure_language_enforcement():
    """Verifies that citizen-facing templates do not contain mixed English in headings."""
    library_content = (STATIC_DIR / "library.html").read_text(encoding="utf-8")

    # Assert no mixed "(Citizen Legal Library)" or "(M10)"
    assert "(Citizen Legal Library)" not in library_content
    assert "(M10)" not in library_content
    assert "(AC-M" not in library_content
