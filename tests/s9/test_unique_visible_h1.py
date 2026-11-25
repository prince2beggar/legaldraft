"""
Directive Z2 (Y2): Single Non-Empty Visible H1 Test Suite.

Asserts across ALL shipped pages:
1. Exactly one <h1> tag exists in the page document.
2. The <h1> is non-empty.
3. The <h1> is not the brand/logo text ('আইন-AI', 'Ain-AI', etc.).
4. The <h1> is rendered visibly with non-zero dimensions and proper layout visibility.
Covers: /intake, /draft, /admin/system, /admin/emergency-contacts, /signin, and all other shipped pages.
"""

from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from packages.trust_kernel.auth import create_access_token

REPO_ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = REPO_ROOT / "backend" / "app" / "static"

BRAND_NAMES = ["আইন-ai", "ain-ai", "আইন ai", "ain ai", "আইন-এআই"]

# All shipped HTML pages that constitute user/admin-facing screens
SHIPPED_PAGES = [
    {"path": "/signin", "auth": False, "role": "anonymous", "file": "signin.html"},
    {"path": "/home", "auth": True, "role": "citizen", "file": "home.html"},
    {"path": "/cases", "auth": True, "role": "citizen", "file": "cases.html"},
    {"path": "/intake", "auth": True, "role": "citizen", "file": "intake.html"},
    {"path": "/draft", "auth": True, "role": "citizen", "file": "draft.html"},
    {"path": "/documents/upload", "auth": True, "role": "citizen", "file": "documents_upload.html"},
    {"path": "/documents/intent", "auth": True, "role": "citizen", "file": "document_intent.html"},
    {"path": "/library", "auth": True, "role": "citizen", "file": "library.html"},
    {"path": "/notifications", "auth": True, "role": "citizen", "file": "notifications.html"},
    {"path": "/notification-settings", "auth": True, "role": "citizen", "file": "notification_settings.html"},
    {"path": "/me/sharing", "auth": True, "role": "citizen", "file": "sharing.html"},
    {"path": "/admin", "auth": True, "role": "admin", "file": "admin.html"},
    {"path": "/admin/sources", "auth": True, "role": "admin", "file": "admin_sources.html"},
    {"path": "/admin/templates", "auth": True, "role": "admin", "file": "admin_templates.html"},
    {"path": "/admin/rules", "auth": True, "role": "admin", "file": "admin_rules.html"},
    {"path": "/admin/evals", "auth": True, "role": "admin", "file": "admin_evals.html"},
    {"path": "/admin/emergency-contacts", "auth": True, "role": "admin", "file": "admin_emergency_contacts.html"},
    {"path": "/admin/system", "auth": True, "role": "admin", "file": "admin_system.html"},
]


def test_z2_all_static_templates_have_exactly_one_non_empty_h1():
    """Asserts that every shipped static HTML file contains exactly one non-empty <h1>, not brand text."""
    for item in SHIPPED_PAGES:
        file_path = STATIC_DIR / item["file"]
        assert file_path.exists(), f"File {item['file']} does not exist"

        soup = BeautifulSoup(file_path.read_text(encoding="utf-8"), "html.parser")
        h1_tags = soup.find_all("h1")

        assert len(h1_tags) == 1, (
            f"Expected exactly 1 <h1> in {item['file']}, found {len(h1_tags)}: {[h.get_text(strip=True) for h in h1_tags]}"
        )

        h1_text = h1_tags[0].get_text(strip=True)
        assert len(h1_text) > 0, f"<h1> is empty in {item['file']}"
        assert h1_text.lower() not in BRAND_NAMES, (
            f"<h1> in {item['file']} contains only brand name: '{h1_text}'"
        )

        # Ensure not visually hidden via sr-only or style
        classes = h1_tags[0].get("class", [])
        assert "sr-only" not in classes, f"<h1> in {item['file']} is visually hidden with sr-only"


def test_z2_live_browser_rendered_h1_visibility(live_server):
    """
    Playwright test asserting on each live rendered shipped page:
    - Exactly one <h1> is visible in the viewport.
    - It has non-zero width and height.
    - Its text content is non-empty and is not the brand/logo.
    """
    citizen_token = create_access_token(
        data={"sub": "01711223344", "phone": "01711223344", "role": "citizen"}
    )
    admin_token = create_access_token(
        data={"sub": "admin_root", "phone": "01799999999", "role": "admin"}
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        for target in SHIPPED_PAGES:
            path = target["path"]
            token = admin_token if target["role"] == "admin" else citizen_token

            page.goto(f"{live_server}/signin", wait_until="domcontentloaded")
            if target["auth"]:
                page.evaluate(
                    """({ tok, role }) => {
                        localStorage.setItem('ain_token', tok);
                        localStorage.setItem('ain_ai_token', tok);
                        localStorage.setItem('token', tok);
                        localStorage.setItem('ain_user_role', role);
                    }""",
                    {"tok": token, "role": target["role"]},
                )

            page.goto(f"{live_server}{path}", wait_until="domcontentloaded")
            page.wait_for_timeout(150)

            # Locate all visible h1 tags on page
            visible_h1s = page.locator("h1:visible")
            count = visible_h1s.count()
            assert count == 1, (
                f"Expected exactly 1 visible <h1> on {path}, but found {count}"
            )

            h1_el = visible_h1s.first
            h1_box = h1_el.bounding_box()
            assert h1_box is not None, f"Bounding box is None for <h1> on {path}"
            assert h1_box["width"] > 0 and h1_box["height"] > 0, (
                f"<h1> on {path} has zero dimensions: {h1_box}"
            )

            text = h1_el.inner_text().strip()
            assert len(text) > 0, f"<h1> text is empty on {path}"
            assert text.lower() not in BRAND_NAMES, (
                f"<h1> text on {path} matches brand name: '{text}'"
            )

        context.close()
        browser.close()
