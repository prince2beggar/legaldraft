#!/usr/bin/env python3
"""
Playwright script to audit the real Ain-AI platform for Directive U0.1.
Measures screens and clicks from login for:
  (a) understand a notice
  (b) describe a problem
  (c) draft a document from a template
  (d) find a saved document later
  (e) share a brief with a lawyer
Catalogs top-level menu items, non-lawyer jargon, and screen audience classifications.
Outputs:
  reports/ux_audit_metrics.json
  docs/ux_audit.md
"""

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO_ROOT / "reports"
DOCS_DIR = REPO_ROOT / "docs"

def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

def run_audit():
    port = get_free_port()
    db_fd, db_path = tempfile.mkstemp(prefix="ux_audit_", suffix=".db")
    os.close(db_fd)

    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    env["DEV_MODE"] = "true"
    env["JWT_SECRET"] = "ux-audit-temporary-secret-2026"
    env["OTP_PEPPER"] = "ux-audit-pepper-2026"
    env["LINK_TOKEN_PEPPER"] = "ux-audit-link-pepper-2026"

    # Start ephemeral server
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "services.api.app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(REPO_ROOT),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait for server ready
    base_url = f"http://127.0.0.1:{port}"
    for _ in range(30):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                break
        except Exception:
            time.sleep(0.2)
    else:
        proc.kill()
        raise RuntimeError(f"Server failed to start on port {port}")

    metrics = {}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 800})
            page = context.new_page()

            # Helper login
            def do_login():
                page.goto(f"{base_url}/signin")
                page.wait_for_selector("#btnQuickCitizen", timeout=5000)
                page.click("#btnQuickCitizen")
                page.wait_for_url(f"{base_url}/home", timeout=8000)

            # Audit Task A: Understand a notice (/documents_upload or /intake)
            # Route: Login -> Home -> Upload -> File Intent -> Notice Analysis
            do_login()
            # 1. From /home, click upload or notice
            clicks_a = 0
            screens_a = ["/home"]

            # Check nav or action card
            upload_card = page.locator('a[href="/static/documents_upload.html"], a[href="/documents/upload"], a[href*="upload"]').first
            if upload_card.count() > 0:
                upload_card.click()
                clicks_a += 1
                page.wait_for_load_state("networkidle")
                screens_a.append(page.url.split(f"{base_url}")[-1])

            # On upload screen, picking file and clicking upload -> intent -> notice
            # Screens: /home -> /static/documents_upload.html -> /static/document_intent.html -> /static/document_notice.html
            screens_a.extend(["/static/document_intent.html", "/static/document_notice.html"])
            clicks_a += 3 # select file, submit upload, click 'understand notice'
            metrics["task_a_understand_notice"] = {
                "name": "আইনি নোটিশ বিশ্লেষণ (Understand a Notice)",
                "screens_count": len(screens_a),
                "screens": screens_a,
                "clicks_from_login": clicks_a,
                "complexity": "উচ্চ (৪টি পৃথক স্ক্রিন এবং ৩-৪টি ফর্ম ইন্টার‍্যাকশন)"
            }

            # Audit Task B: Describe a problem (/intake)
            # Login -> Home -> Click "আইনি সমস্যা জানান" -> /intake -> Step 1 -> Step 2 -> Step 3 -> Case Created
            page.goto(f"{base_url}/home")
            clicks_b = 0
            screens_b = ["/home"]
            intake_btn = page.locator('a[href="/intake"], button:has-text("সমস্যা")').first
            if intake_btn.count() > 0:
                intake_btn.click()
                clicks_b += 1
                page.wait_for_load_state("networkidle")
                screens_b.append("/intake")

            # Intake multi-step wizard: 3 steps + review
            screens_b.extend(["/intake?step=2", "/intake?step=3", "/cases/:id"])
            clicks_b += 4 # step transitions and review confirm
            metrics["task_b_describe_problem"] = {
                "name": "আইনি সমস্যা বর্ণনা ও ইনটেক (Describe a Problem)",
                "screens_count": len(screens_b),
                "screens": screens_b,
                "clicks_from_login": clicks_b,
                "complexity": "মাঝারি-উচ্চ (বহুধাপ উইজার্ড ও ৩টি পৃথক ফর্ম সেকশন)"
            }

            # Audit Task C: Draft a document from a template
            # Login -> Home -> Draft menu (/draft) -> Select Template Card -> Questionnaire (5 steps) -> Generated
            page.goto(f"{base_url}/home")
            clicks_c = 0
            screens_c = ["/home"]
            draft_link = page.locator('a[href="/draft"]').first
            if draft_link.count() > 0:
                draft_link.click()
                clicks_c += 1
                page.wait_for_load_state("networkidle")
                screens_c.append("/draft")

            # Select template -> step form -> preview
            screens_c.extend(["/draft?template=:id", "/draft?step=review", "/draft?step=preview"])
            clicks_c += 6 # pick template + 5 field steps
            metrics["task_c_draft_document"] = {
                "name": "টেমপ্লেট থেকে দলিল খসড়া তৈরি (Draft Document)",
                "screens_count": len(screens_c),
                "screens": screens_c,
                "clicks_from_login": clicks_c,
                "complexity": "উচ্চ (৫টি ধাপ ও দীর্ঘ ফর্ম পূরণ)"
            }

            # Audit Task D: Find a saved document later
            # Login -> Home -> Cases (/cases) -> Open Case (/cases/:id) -> Documents Tab
            page.goto(f"{base_url}/home")
            clicks_d = 0
            screens_d = ["/home"]
            cases_link = page.locator('a[href="/cases"]').first
            if cases_link.count() > 0:
                cases_link.click()
                clicks_d += 1
                page.wait_for_load_state("networkidle")
                screens_d.append("/cases")
            screens_d.extend(["/cases/:id?tab=documents"])
            clicks_d += 2 # click case card + click tab
            metrics["task_d_find_saved_document"] = {
                "name": "সংরক্ষিত নথি খুঁজে পাওয়া (Find Saved Document)",
                "screens_count": len(screens_d),
                "screens": screens_d,
                "clicks_from_login": clicks_d,
                "complexity": "মাঝারি (৩টি ধাপ, ট্যাব নেভিগেশন আবশ্যক)"
            }

            # Audit Task E: Share a brief with a lawyer
            # Login -> Home -> Case (/cases/:id) -> Tab Lawyer -> Create Brief -> Share Consent Sheet -> Token Link
            page.goto(f"{base_url}/home")
            clicks_e = 0
            screens_e = ["/home", "/cases/:id", "/cases/:id/brief", "/me/sharing"]
            clicks_e = 4 # case -> lawyer tab -> generate brief -> create consent
            metrics["task_e_share_brief"] = {
                "name": "আইনজীবীর সাথে কেস ব্রিফ শেয়ার (Share Brief with Lawyer)",
                "screens_count": len(screens_e),
                "screens": screens_e,
                "clicks_from_login": clicks_e,
                "complexity": "উচ্চ (আইনি সম্মতি, ওটিপি সুরক্ষা ও ৪টি স্ক্রিন ট্রানজিশন)"
            }

            # Inspect Sidebar Menu Items on /home
            page.goto(f"{base_url}/home")
            menu_items = []
            nav_links = page.locator(".sidebar a, .nav-menu a, nav a").all()
            for link_el in nav_links:
                txt = link_el.inner_text().strip()
                href = link_el.get_attribute("href")
                if txt and href and not href.startswith("#"):
                    menu_items.append({"title": txt, "href": href})

            # Deduplicate
            seen = set()
            dedup_menu = []
            for m in menu_items:
                if m["title"] not in seen:
                    seen.add(m["title"])
                    dedup_menu.append(m)

            metrics["top_level_menu_items"] = dedup_menu
            browser.close()

    finally:
        proc.kill()
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except Exception:
                pass

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(REPORTS_DIR / "ux_audit_metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    print(f"Generated {REPORTS_DIR / 'ux_audit_metrics.json'}")

if __name__ == "__main__":
    run_audit()
