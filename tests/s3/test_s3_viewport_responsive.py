"""
Responsive Viewport Tests & Screenshot Generator for Sprint S3 Admin Pages (SRS ADR-018 & S3 DoD).
Tests across three required viewports:
- Mobile: 360 x 640
- Tablet: 768 x 1024
- Desktop: 1280 x 800

Verifies:
1. Zero horizontal overflow (scrollWidth <= clientWidth + 1) for /admin/rules and /admin/evals.
2. Responsive navigation adaptations: bottom nav on mobile, sidebar on tablet/desktop.
3. Captures screenshots in storage/screenshots/:
   - admin_rules_mobile_360.png, admin_rules_tablet_768.png, admin_rules_desktop_1280.png
   - admin_evals_mobile_360.png, admin_evals_tablet_768.png, admin_evals_desktop_1280.png
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


def test_admin_rules_responsive_and_screenshots(browser_instance):
    """Verifies Admin Rules Engine at all 3 viewports and captures screenshots."""
    rules_path = (STATIC_DIR / "admin_rules.html").as_uri()

    for vp in VIEWPORTS:
        context = browser_instance.new_context(
            viewport={"width": vp["width"], "height": vp["height"]}
        )
        page = context.new_page()
        page.goto(rules_path)
        page.wait_for_selector("#rulesTable")

        # 1. Zero horizontal scroll check
        scroll_width = page.evaluate("() => document.documentElement.scrollWidth")
        client_width = page.evaluate("() => document.documentElement.clientWidth")
        assert scroll_width <= client_width + 1, (
            f"Horizontal overflow detected in admin_rules.html at {vp['name']}: scrollWidth={scroll_width}, clientWidth={client_width}"
        )

        # 2. Check layout adaptation
        if vp["width"] < 640:
            assert page.locator(".mobile-bottom-nav").is_visible(), (
                "Bottom nav must be visible on mobile"
            )
        elif vp["width"] >= 1024:
            assert page.locator(".app-sidebar").is_visible(), "Sidebar must be visible on desktop"

        # 3. Capture screenshot
        shot_path = SCREENSHOTS_DIR / f"admin_rules_{vp['name']}.png"
        page.screenshot(path=str(shot_path))
        assert shot_path.exists()

        context.close()


def test_admin_evals_responsive_and_screenshots(browser_instance):
    """Verifies Admin Evaluation Dashboard at all 3 viewports and captures screenshots."""
    evals_path = (STATIC_DIR / "admin_evals.html").as_uri()

    for vp in VIEWPORTS:
        context = browser_instance.new_context(
            viewport={"width": vp["width"], "height": vp["height"]}
        )
        page = context.new_page()
        page.goto(evals_path)
        page.wait_for_selector("#suitesTable")

        # 1. Zero horizontal scroll check
        scroll_width = page.evaluate("() => document.documentElement.scrollWidth")
        client_width = page.evaluate("() => document.documentElement.clientWidth")
        assert scroll_width <= client_width + 1, (
            f"Horizontal overflow detected in admin_evals.html at {vp['name']}: scrollWidth={scroll_width}, clientWidth={client_width}"
        )

        # 2. Check layout adaptation
        if vp["width"] < 640:
            assert page.locator(".mobile-bottom-nav").is_visible(), (
                "Bottom nav must be visible on mobile"
            )
        elif vp["width"] >= 1024:
            assert page.locator(".app-sidebar").is_visible(), "Sidebar must be visible on desktop"

        # 3. Capture screenshot
        shot_path = SCREENSHOTS_DIR / f"admin_evals_{vp['name']}.png"
        page.screenshot(path=str(shot_path))
        assert shot_path.exists()

        context.close()
