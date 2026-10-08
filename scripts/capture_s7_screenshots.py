"""
Capture 5 real unmodified S7 screenshots for Intake & Triage (Module M11).
Complies with Owner's Addendum (E3, E4, E6):
- NO route aborts, NO font blocking, NO DOM injection, NO route fulfill mocking.
- Real backend API on local server.
- Saved directly to storage/screenshots/ and copied to Antigravity brain directory.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

OUTPUT_DIR = REPO_ROOT / "storage" / "screenshots"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

BRAIN_DIR = Path("C:/Users/Lenovo/.gemini/antigravity/brain/f5b387fc-eb28-4e1b-9940-b3291f442234")
PORT = 8089


def wait_for_port(port: int, timeout: int = 25) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except (ConnectionRefusedError, OSError):
            time.sleep(0.5)
    return False


def main():
    # Ensure DEV_MODE=true for server
    env = os.environ.copy()
    env["DEV_MODE"] = "true"

    print("Starting FastAPI server as subprocess...")
    log_file = open(REPO_ROOT / "server_screenshot.log", "w", encoding="utf-8")
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "services.api.app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(PORT),
        ],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=log_file,
        stderr=log_file,
    )

    print("Waiting for server on port", PORT, "...")
    if not wait_for_port(PORT, timeout=25):
        print("Server failed to start! Check server_screenshot.log")
        proc.terminate()
        log_file.close()
        return

    print("Server is listening! Proceeding with Playwright capture...")
    base_url = f"http://127.0.0.1:{PORT}"

    from datetime import datetime, timedelta, timezone

    from packages.trust_kernel.auth import TokenService
    from packages.trust_kernel.db import db_manager

    now = datetime.now(timezone.utc)
    cit_user = {
        "id": "citizen-screenshot-user",
        "phone": "01711888999",
        "name": "নাগরিক ব্যবহারকারী",
        "role": "citizen",
        "roles": ["citizen"],
        "status": "active",
        "is_onboarded": True,
        "created_at": now.isoformat(),
    }
    db_manager.save_user(cit_user)
    auth_token = TokenService.encode_token(
        {
            "sub": "citizen-screenshot-user",
            "phone": "01711888999",
            "device_id": "dev-screenshot",
            "role": "citizen",
            "roles": ["citizen"],
            "type": "access",
            "exp": int((now + timedelta(hours=1)).timestamp()),
        }
    )

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            # ---------------------------------------------------------------
            # 1. s7_intake_triage_urgent_banner.png (Mobile 360x640)
            # Ticked urgent chip, UrgentBanner VISIBLE on screen, bottom tab bar
            # ---------------------------------------------------------------
            print("Capturing 1. s7_intake_triage_urgent_banner.png (Mobile 360x640)...")
            ctx_mobile1 = browser.new_context(viewport={"width": 360, "height": 640})
            ctx_mobile1.add_cookies(
                [{"name": "ain_ai_token", "value": auth_token, "domain": "127.0.0.1", "path": "/"}]
            )
            page1 = ctx_mobile1.new_page()
            page1.goto(f"{base_url}/static/intake.html", wait_until="domcontentloaded")
            time.sleep(0.5)

            # Select urgent chip
            chip = page1.locator("input[value='violence_threat']")
            chip.check()
            page1.wait_for_selector("#urgentBanner.visible", state="visible")
            # Scroll banner into view so it is clearly visible in the 360x640 viewport
            page1.locator("#urgentBanner").scroll_into_view_if_needed()
            time.sleep(0.5)

            path1 = OUTPUT_DIR / "s7_intake_triage_urgent_banner.png"
            page1.screenshot(path=str(path1), full_page=False)
            ctx_mobile1.close()

            # ---------------------------------------------------------------
            # 2. s7_intake_triage_chips.png (Desktop 1280x800)
            # Step 1 triage chips, desktop sidebar navigation visible
            # ---------------------------------------------------------------
            print("Capturing 2. s7_intake_triage_chips.png (Desktop 1280x800)...")
            ctx_desktop = browser.new_context(viewport={"width": 1280, "height": 800})
            ctx_desktop.add_cookies(
                [{"name": "ain_ai_token", "value": auth_token, "domain": "127.0.0.1", "path": "/"}]
            )
            page2 = ctx_desktop.new_page()
            page2.goto(f"{base_url}/static/intake.html", wait_until="domcontentloaded")
            page2.wait_for_selector(".chips-group", state="visible")
            page2.wait_for_selector(".app-sidebar", state="visible")
            time.sleep(0.5)

            path2 = OUTPUT_DIR / "s7_intake_triage_chips.png"
            page2.screenshot(path=str(path2), full_page=False)
            ctx_desktop.close()

            # ---------------------------------------------------------------
            # 3. s7_intake_question_step.png (Mobile 360x640)
            # Step 2 narrative input with bottom tab bar
            # ---------------------------------------------------------------
            print("Capturing 3. s7_intake_question_step.png (Mobile 360x640)...")
            ctx_mobile2 = browser.new_context(viewport={"width": 360, "height": 640})
            ctx_mobile2.add_cookies(
                [{"name": "ain_ai_token", "value": auth_token, "domain": "127.0.0.1", "path": "/"}]
            )
            page3 = ctx_mobile2.new_page()
            page3.goto(f"{base_url}/static/intake.html", wait_until="domcontentloaded")
            page3.wait_for_selector("#nextBtn", state="visible")
            page3.locator("#nextBtn").click()
            page3.wait_for_selector("#answerInput", state="visible")
            page3.locator("#answerInput").fill(
                "বিবাদী আমার পৈতৃক জমি জবরদখল করার চেষ্টা করছে এবং সীমানা প্রাচীর ভেঙেছে।"
            )
            time.sleep(0.5)

            path3 = OUTPUT_DIR / "s7_intake_question_step.png"
            page3.screenshot(path=str(path3), full_page=False)
            ctx_mobile2.close()

            # ---------------------------------------------------------------
            # 4. s7_intake_review_confirm.png (Desktop 1280x800)
            # Step 11 review screen with sections, badges, amber AI warning, no 'undefined'
            # ---------------------------------------------------------------
            print("Capturing 4. s7_intake_review_confirm.png (Desktop 1280x800)...")
            ctx_desktop2 = browser.new_context(viewport={"width": 1280, "height": 800})
            ctx_desktop2.add_cookies(
                [{"name": "ain_ai_token", "value": auth_token, "domain": "127.0.0.1", "path": "/"}]
            )
            page4 = ctx_desktop2.new_page()
            page4.on("console", lambda msg: print("PAGE4 LOG:", msg.text))
            page4.on("pageerror", lambda err: print("PAGE4 ERR:", err))
            page4.goto(
                f"{base_url}/static/intake.html?q=বিবাদী+আমার+জমি+দখল+করার+চেষ্টা+করছে",
                wait_until="domcontentloaded",
            )
            page4.wait_for_selector("#nextBtn", state="visible")
            time.sleep(0.5)

            # Navigate to review step directly using page async function
            page4.evaluate("async () => { currentStep = 10; await goNext(); }")
            page4.wait_for_selector(".btn-section-confirm", state="visible", timeout=20000)
            time.sleep(1.0)

            path4 = OUTPUT_DIR / "s7_intake_review_confirm.png"
            page4.screenshot(path=str(path4), full_page=False)
            ctx_desktop2.close()

            # ---------------------------------------------------------------
            # 5. s7_emergency_contacts_admin.png (Desktop 1280x800)
            # Admin emergency contacts management with Bangla badges and verification actions
            # ---------------------------------------------------------------
            print("Capturing 5. s7_emergency_contacts_admin.png (Desktop 1280x800)...")
            ctx_admin = browser.new_context(viewport={"width": 1280, "height": 800})
            page5 = ctx_admin.new_page()
            page5.goto(
                f"{base_url}/static/admin_emergency_contacts.html", wait_until="domcontentloaded"
            )
            page5.wait_for_selector("#contactsBody tr", state="visible")
            time.sleep(0.5)

            path5 = OUTPUT_DIR / "s7_emergency_contacts_admin.png"
            page5.screenshot(path=str(path5), full_page=False)
            ctx_admin.close()

            browser.close()

        # Copy to Antigravity brain directory for UI inspection artifacts
        if BRAIN_DIR.exists():
            for p in [path1, path2, path3, path4, path5]:
                dest = BRAIN_DIR / p.name
                shutil.copyfile(p, dest)
                print(f"Copied {p.name} -> {dest}")

        print("\nAll 5 S7 screenshots captured successfully:")
        for p in [path1, path2, path3, path4, path5]:
            size = p.stat().st_size
            print(f"- {p} ({size:,} bytes)")

    finally:
        print("Terminating server...")
        proc.terminate()
        proc.wait()
        log_file.close()


if __name__ == "__main__":
    main()
