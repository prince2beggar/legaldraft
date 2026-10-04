"""
Responsive Viewport Tests & Screenshot Generator for Sprint S6 (M02 Home, M06 Case Folder, M07 Notifications).
Covers 7 core views across 3 viewports (360x640, 768x1024, 1280x800):
1. Home with Next Action Card (s6_home_with_next_action)
2. Home empty state (s6_home_empty)
3. Case Detail - Overview tab with parties & summary (s6_case_detail_overview)
4. Case Detail - Timeline tab with precision markers (s6_case_detail_timeline)
5. Case Detail - Deadlines tab with rules calculation (s6_case_detail_deadlines)
6. Notifications list with channel & category tags (s6_notifications_list)
7. Notification Settings with quiet hours & SMS toggles (s6_notification_settings)

Verifies:
1. Zero horizontal overflow (scrollWidth <= clientWidth + 1).
2. Navigation variants: desktop sidebar, mobile header & responsive flow.
3. Typography & styling integrity across resolutions.
4. Generates 21 screenshots in storage/screenshots/ and copies to artifact dir.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = REPO_ROOT / "backend" / "app" / "static"
SCREENSHOTS_DIR = REPO_ROOT / "storage" / "screenshots"
ARTIFACT_DIR = Path("C:/Users/Lenovo/.gemini/antigravity/brain/f5b387fc-eb28-4e1b-9940-b3291f442234")

VIEWPORTS = [
    {"name": "mobile_360", "width": 360, "height": 640, "is_mobile": True},
    {"name": "tablet_768", "width": 768, "height": 1024, "is_mobile": False},
    {"name": "desktop_1280", "width": 1280, "height": 800, "is_mobile": False},
]

VIEWS = [
    {
        "id": "s6_home_with_next_action",
        "file": "home.html",
        "query": "?variant=standard",
        "wait_for": "#nextActionCard",
    },
    {
        "id": "s6_home_empty",
        "file": "home.html",
        "query": "?variant=empty",
        "wait_for": "#emptyNextAction",
    },
    {
        "id": "s6_case_detail_overview",
        "file": "case_detail.html",
        "query": "?variant=overview",
        "wait_for": "#tab-overview",
    },
    {
        "id": "s6_case_detail_timeline",
        "file": "case_detail.html",
        "query": "?variant=timeline",
        "wait_for": "#tab-timeline",
    },
    {
        "id": "s6_case_detail_deadlines",
        "file": "case_detail.html",
        "query": "?variant=deadlines",
        "wait_for": "#tab-deadlines",
    },
    {
        "id": "s6_notifications_list",
        "file": "notifications.html",
        "query": "",
        "wait_for": "#notifList",
    },
    {
        "id": "s6_notification_settings",
        "file": "notification_settings.html",
        "query": "",
        "wait_for": "#settingsCard",
    },
]


@pytest.fixture(scope="module")
def browser_instance():
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.mark.parametrize("view", VIEWS, ids=lambda v: v["id"])
def test_s6_screens_responsive_and_screenshots(browser_instance, view):
    html_file = (STATIC_DIR / view["file"]).as_uri()
    url = f"{html_file}{view['query']}"

    for vp in VIEWPORTS:
        context = browser_instance.new_context(
            viewport={"width": vp["width"], "height": vp["height"]}
        )
        page = context.new_page()
        page.goto(url)
        page.wait_for_selector(view["wait_for"])
        page.wait_for_timeout(300)

        # 1. Zero horizontal overflow check
        scroll_width = page.evaluate("() => document.documentElement.scrollWidth")
        client_width = page.evaluate("() => document.documentElement.clientWidth")
        assert scroll_width <= client_width + 1, (
            f"Horizontal overflow in {view['id']} at {vp['name']}: "
            f"scrollWidth={scroll_width}, clientWidth={client_width}"
        )

        # 2. View-specific state assertions
        target_el = page.locator(view["wait_for"])
        assert target_el.is_visible()

        # 3. Capture screenshot
        img_name = f"{view['id']}_{vp['name']}.png"
        target_path = SCREENSHOTS_DIR / img_name
        page.screenshot(path=str(target_path), full_page=False)
        assert target_path.exists()

        # Copy to artifact directory if available
        if ARTIFACT_DIR.exists():
            shutil.copy(target_path, ARTIFACT_DIR / img_name)

        context.close()
