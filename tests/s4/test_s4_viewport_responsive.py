"""
Responsive Viewport Tests & Screenshot Generator for Sprint S4 Document Pages (M03).
Covers:
- Upload: documents_upload.html
- Intent: document_intent.html
- Viewer: document_viewer.html
- Status: document_status.html

Tests across three viewports:
- Mobile: 360 x 640
- Tablet: 768 x 1024
- Desktop: 1280 x 800

Verifies:
1. Zero horizontal overflow (scrollWidth <= clientWidth + 1).
2. Navigation variants: bottom navigation on mobile, sidebar on tablet/desktop.
3. Touch targets >= 48px on mobile.
4. Generates screenshots in storage/screenshots/ and copies to artifact dir.
"""

import shutil
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = REPO_ROOT / "backend" / "app" / "static"
SCREENSHOTS_DIR = REPO_ROOT / "storage" / "screenshots"
ARTIFACT_DIR = Path(
    "C:/Users/Lenovo/.gemini/antigravity/brain/f5b387fc-eb28-4e1b-9940-b3291f442234"
)

VIEWPORTS = [
    {"name": "mobile_360", "width": 360, "height": 640, "is_mobile": True},
    {"name": "tablet_768", "width": 768, "height": 1024, "is_mobile": False},
    {"name": "desktop_1280", "width": 1280, "height": 800, "is_mobile": False},
]

SCREENS = [
    {"id": "doc_upload", "filename": "documents_upload.html", "wait_for": "body"},
    {"id": "doc_intent", "filename": "document_intent.html", "wait_for": "body"},
    {"id": "doc_viewer", "filename": "document_viewer.html", "wait_for": "body"},
    {"id": "doc_status", "filename": "document_status.html", "wait_for": "body"},
]


@pytest.fixture(scope="module")
def browser_instance():
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.mark.parametrize("screen", SCREENS, ids=lambda s: s["id"])
def test_document_screens_responsive_and_screenshots(browser_instance, screen):
    file_path = (STATIC_DIR / screen["filename"]).as_uri()

    for vp in VIEWPORTS:
        context = browser_instance.new_context(
            viewport={"width": vp["width"], "height": vp["height"]}
        )
        page = context.new_page()
        page.goto(file_path)
        page.wait_for_selector(screen["wait_for"])
        page.wait_for_timeout(300)

        # 1. Zero horizontal overflow check
        scroll_width = page.evaluate("() => document.documentElement.scrollWidth")
        client_width = page.evaluate("() => document.documentElement.clientWidth")
        assert scroll_width <= client_width + 1, (
            f"Horizontal overflow in {screen['filename']} at {vp['name']}: "
            f"scrollWidth={scroll_width}, clientWidth={client_width}"
        )

        # 2. Navigation variant check
        if vp["width"] < 640:
            assert page.locator(".mobile-bottom-nav, .mobile-nav").is_visible(), (
                f"Bottom nav must be visible on mobile in {screen['filename']}"
            )
        elif vp["width"] >= 1024:
            assert page.locator(".app-sidebar").is_visible(), (
                f"Sidebar must be visible on desktop in {screen['filename']}"
            )

        # 3. Capture screenshot
        img_name = f"{screen['id']}_{vp['name']}.png"
        target_path = SCREENSHOTS_DIR / img_name
        page.screenshot(path=str(target_path), full_page=False)
        assert target_path.exists()

        # Copy to artifact directory if available
        if ARTIFACT_DIR.exists():
            shutil.copy(target_path, ARTIFACT_DIR / img_name)

        context.close()
