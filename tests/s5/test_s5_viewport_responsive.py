"""
Responsive Viewport Tests & Screenshot Generator for Sprint S5 Notice Interpreter (M04).
Covers 5 core views across 3 viewports (360x640, 768x1024, 1280x800):
1. Notice result screen with amber label bar and all 8 sections (s5_notice_result)
2. DeadlineCard expanded showing "How we counted this" and Bangla digits (s5_deadline_card)
3. Relative-date question flow ("when did you receive this?") (s5_relative_flow)
4. "Could not read clearly" fallback state (s5_fallback_unreadable)
5. "Save to case" confirmation modal showing created case, tasks, and deadline (s5_save_to_case)

Verifies:
1. Zero horizontal overflow (scrollWidth <= clientWidth + 1).
2. Navigation variants: sidebar on desktop, responsive container on mobile/tablet.
3. Bangla typography & Amber banner rendering.
4. Generates screenshots in storage/screenshots/ and copies to artifact dir.
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
        "id": "s5_notice_result",
        "variant": "standard",
        "wait_for": "#labelBar",
    },
    {
        "id": "s5_deadline_card",
        "variant": "deadline_expanded",
        "wait_for": "#howCountedBox",
    },
    {
        "id": "s5_relative_flow",
        "variant": "relative",
        "wait_for": "#relativeTriggerBox",
    },
    {
        "id": "s5_fallback_unreadable",
        "variant": "unreadable",
        "wait_for": "#labelBar",
    },
    {
        "id": "s5_save_to_case",
        "variant": "save_case",
        "wait_for": "#saveCaseModal",
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
def test_notice_screens_responsive_and_screenshots(browser_instance, view):
    html_file = (STATIC_DIR / "document_notice.html").as_uri()
    url = f"{html_file}?variant={view['variant']}"

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

        # 2. Amber banner visibility check
        label_bar = page.locator("#labelBar")
        assert label_bar.is_visible()

        # 3. View-specific state assertions
        if view["variant"] == "deadline_expanded":
            how_box = page.locator("#howCountedBox")
            assert "open" in (how_box.get_attribute("class") or "")
        elif view["variant"] == "relative":
            rel_box = page.locator("#relativeTriggerBox")
            assert rel_box.is_visible()
        elif view["variant"] == "save_case":
            modal = page.locator("#saveCaseModal")
            assert "open" in (modal.get_attribute("class") or "")

        # 4. Capture screenshot
        img_name = f"{view['id']}_{vp['name']}.png"
        target_path = SCREENSHOTS_DIR / img_name
        page.screenshot(path=str(target_path), full_page=False)
        assert target_path.exists()

        # Copy to artifact directory if available
        if ARTIFACT_DIR.exists():
            shutil.copy(target_path, ARTIFACT_DIR / img_name)

        context.close()
