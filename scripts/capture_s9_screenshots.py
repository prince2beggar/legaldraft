#!/usr/bin/env python3
"""
Captures the 8 required distinct Sprint S9 screenshots (H1):
1. ConsentSheet open (360x640)
2. brief preview (1280x800)
3. /me/sharing with access history visible (360x640)
4. /me/sharing with access history visible (1280x800)
5. recipient viewer with watermark (360x640)
6. recipient expired/revoked 404 view (360x640)
7. admin System page (1280x800)
8. admin System page (360x640)

All captured from real unmodified pages without route aborts or DOM injection.
"""

import shutil
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "backend" / "app" / "static"
OUT_DIR = REPO_ROOT / "storage" / "screenshots"
ARTIFACTS_DIR = Path(
    "C:/Users/Lenovo/.gemini/antigravity/brain/f5b387fc-eb28-4e1b-9940-b3291f442234"
)


def capture_all():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    captured = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # -------------------------------------------------------------------
        # 1. ConsentSheet open (360x640)
        # -------------------------------------------------------------------
        page = browser.new_page(viewport={"width": 360, "height": 640})
        case_brief_uri = (STATIC_DIR / "case_brief.html").as_uri()
        page.goto(case_brief_uri)
        page.wait_for_selector("#briefCard", state="visible")
        # Click the share button to open the bottom sheet modal
        page.click("button.btn-primary")
        page.wait_for_selector("#consentModal", state="visible")
        time.sleep(0.3)
        p1 = OUT_DIR / "s9_consent_sheet_open_360.png"
        page.screenshot(path=str(p1))
        captured["s9_consent_sheet_open_360.png"] = p1
        page.close()

        # -------------------------------------------------------------------
        # 2. Brief preview (1280x800)
        # -------------------------------------------------------------------
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(case_brief_uri)
        page.wait_for_selector("#briefCard", state="visible")
        time.sleep(0.3)
        p2 = OUT_DIR / "s9_brief_preview_1280.png"
        page.screenshot(path=str(p2))
        captured["s9_brief_preview_1280.png"] = p2
        page.close()

        # -------------------------------------------------------------------
        # 3. /me/sharing with access history visible (360x640)
        # -------------------------------------------------------------------
        page = browser.new_page(viewport={"width": 360, "height": 640})
        sharing_uri = (STATIC_DIR / "sharing.html").as_uri()
        page.goto(sharing_uri)
        page.wait_for_selector(".btn-action", state="visible")
        # Click "অ্যাক্সেস ইতিহাস" button to open modal
        page.locator("button.btn-action", has_text="অ্যাক্সেস ইতিহাস").first.click()
        page.wait_for_selector("#accessLogModal", state="visible")
        time.sleep(0.3)
        p3 = OUT_DIR / "s9_sharing_access_history_360.png"
        page.screenshot(path=str(p3))
        captured["s9_sharing_access_history_360.png"] = p3
        page.close()

        # -------------------------------------------------------------------
        # 4. /me/sharing with access history visible (1280x800)
        # -------------------------------------------------------------------
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        page.goto(sharing_uri)
        page.wait_for_selector(".btn-action", state="visible")
        page.locator("button.btn-action", has_text="অ্যাক্সেস ইতিহাস").first.click()
        page.wait_for_selector("#accessLogModal", state="visible")
        time.sleep(0.3)
        p4 = OUT_DIR / "s9_sharing_access_history_1280.png"
        page.screenshot(path=str(p4))
        captured["s9_sharing_access_history_1280.png"] = p4
        page.close()

        # -------------------------------------------------------------------
        # 5. Recipient viewer with watermark (360x640)
        # -------------------------------------------------------------------
        page = browser.new_page(viewport={"width": 360, "height": 640})
        # Load via live local server to get real seeded response
        page.goto("http://127.0.0.1:8000/s/Cyc6Ad4o_issuqc4_xnxbd6t8GAS5YXhp80ST-mE9E4")
        page.wait_for_selector("#briefContentBox", state="visible")
        time.sleep(0.3)
        p5 = OUT_DIR / "s9_recipient_viewer_watermark_360.png"
        page.screenshot(path=str(p5))
        captured["s9_recipient_viewer_watermark_360.png"] = p5
        page.close()

        # -------------------------------------------------------------------
        # 6. Recipient expired/revoked 404 view (360x640)
        # -------------------------------------------------------------------
        page = browser.new_page(viewport={"width": 360, "height": 640})
        page.goto("http://127.0.0.1:8000/s/invalid_expired_revoked_token_404")
        page.wait_for_selector("#notFoundBox", state="visible")
        time.sleep(0.3)
        p6 = OUT_DIR / "s9_recipient_expired_404_360.png"
        page.screenshot(path=str(p6))
        captured["s9_recipient_expired_404_360.png"] = p6
        page.close()

        # -------------------------------------------------------------------
        # 7. Admin System page (1280x800)
        # -------------------------------------------------------------------
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        admin_system_uri = (STATIC_DIR / "admin_system.html").as_uri()
        page.goto(admin_system_uri)
        page.wait_for_selector(".container", state="visible")
        time.sleep(0.3)
        p7 = OUT_DIR / "s9_admin_system_1280.png"
        page.screenshot(path=str(p7))
        captured["s9_admin_system_1280.png"] = p7
        page.close()

        # -------------------------------------------------------------------
        # 8. Admin System page (360x640)
        # -------------------------------------------------------------------
        page = browser.new_page(viewport={"width": 360, "height": 640})
        page.goto(admin_system_uri)
        page.wait_for_selector(".container", state="visible")
        time.sleep(0.3)
        p8 = OUT_DIR / "s9_admin_system_360.png"
        page.screenshot(path=str(p8))
        captured["s9_admin_system_360.png"] = p8
        page.close()

        browser.close()

    # Also copy to artifacts dir if accessible
    if ARTIFACTS_DIR.exists():
        for filename, filepath in captured.items():
            dest = ARTIFACTS_DIR / filename
            shutil.copy2(filepath, dest)

    print(f"Successfully captured all {len(captured)} screenshots.")
    return captured


if __name__ == "__main__":
    capture_all()
