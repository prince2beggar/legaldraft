"""
Directive Z5 (J2): Strict Order Verification for all 10 SRS M08 Case-Brief Elements.

Verifies the strict monotonic ordering of all 10 SRS M08 sections:
1. Client Name (১. ক্লায়েন্টের নাম)
2. Case Type (২. মামলার ধরন)
3. Background (৩. প্রেক্ষাপট)
4. Timeline (৪. ঘটনাক্রম)
5. Key Documents (৫. মূল নথিপত্র)
6. Important Facts (৬. গুরুত্বপূর্ণ তথ্য)
7. User Objective (৭. ব্যবহারকারীর উদ্দেশ্য)
8. Possible Legal Issues (৮. আইনি প্রশ্ন ও গবেষণা প্রস্তাবনা)
9. Missing Information (৯. অনুপস্থিত তথ্য)
10. Questions for Lawyer (১০. আইনজীবীর জন্য প্রশ্নাবলী)

Across:
A) In-app page DOM (/cases/:id/brief)
B) Recipient view DOM (/static/shared_brief.html or /s/:token)
C) Chromium PDF text extraction
"""

from __future__ import annotations

import io
import re
from pathlib import Path

from playwright.sync_api import sync_playwright
from pypdf import PdfReader

from packages.trust_kernel.auth import create_access_token

REPO_ROOT = Path(__file__).resolve().parents[2]

SRS_M08_ORDERED_SECTIONS = [
    {"num": "১", "key": "client_name", "keywords": ["ক্লায়েন্টের নাম", "১."]},
    {"num": "২", "key": "case_type", "keywords": ["মামলার ধরন", "২."]},
    {"num": "৩", "key": "background", "keywords": ["প্রেক্ষাপট", "৩."]},
    {"num": "৪", "key": "timeline", "keywords": ["ঘটনাক্রম", "৪."]},
    {"num": "৫", "key": "key_documents", "keywords": ["মূল নথিপত্র", "৫."]},
    {"num": "৬", "key": "important_facts", "keywords": ["গুরুত্বপূর্ণ তথ্য", "৬."]},
    {"num": "৭", "key": "user_objective", "keywords": ["ব্যবহারকারীর উদ্দেশ্য", "৭."]},
    {"num": "৮", "key": "legal_issues", "keywords": ["আইনি প্রশ্ন ও গবেষণা প্রস্তাবনা", "গবেষণা প্রস্তাবনা", "৮."]},
    {"num": "৯", "key": "missing_info", "keywords": ["অনুপস্থিত তথ্য", "৯."]},
    {"num": "১০", "key": "lawyer_questions", "keywords": ["আইনজীবীর জন্য প্রশ্নাবলী", "প্রশ্নাবলী", "১০."]},
]


def test_z5_strict_order_in_app_dom(live_server):
    """Asserts strict sequential order of all 10 elements in in-app /cases/:id/brief DOM."""
    token = create_access_token(
        data={"sub": "01711223344", "phone": "01711223344", "role": "citizen"}
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        page.goto(f"{live_server}/signin", wait_until="domcontentloaded")
        page.evaluate(
            """({ tok }) => {
                localStorage.setItem('ain_token', tok);
                localStorage.setItem('ain_ai_token', tok);
                localStorage.setItem('auth_token', tok);
                localStorage.setItem('token', tok);
                localStorage.setItem('ain_user_role', 'citizen');
            }""",
            {"tok": token},
        )

        page.goto(f"{live_server}/cases/demo_case_001/brief", wait_until="domcontentloaded")

        # Query all section-title elements in order
        titles = page.locator(".section-title").all_inner_texts()
        browser.close()

    assert len(titles) == 10, f"Expected 10 section titles in in-app DOM, found {len(titles)}: {titles}"

    # Verify strict order
    for idx, expected in enumerate(SRS_M08_ORDERED_SECTIONS):
        actual = titles[idx]
        assert expected["num"] in actual, (
            f"DOM element {idx+1} mismatch! Expected prefix '{expected['num']}', got '{actual}'"
        )
        assert any(kw in actual for kw in expected["keywords"]), (
            f"DOM element {idx+1} '{actual}' did not match keywords for {expected['key']}"
        )


def test_z5_strict_order_recipient_view_dom():
    """Asserts strict sequential order of all 10 elements in recipient view DOM template."""
    shared_html_path = REPO_ROOT / "backend" / "app" / "static" / "shared_brief.html"
    assert shared_html_path.exists(), "shared_brief.html not found"
    content = shared_html_path.read_text(encoding="utf-8")

    # Extract all h2.section-title headings in DOM occurrence order
    matches = re.findall(r'<h2\s+class="section-title">([^<]+)</h2>', content)
    assert len(matches) == 10, f"Expected 10 section titles in recipient DOM, found {len(matches)}: {matches}"

    for idx, expected in enumerate(SRS_M08_ORDERED_SECTIONS):
        actual = matches[idx].strip()
        assert expected["num"] in actual, (
            f"Recipient view DOM element {idx+1} mismatch! Expected prefix '{expected['num']}', got '{actual}'"
        )
        assert any(kw in actual for kw in expected["keywords"]), (
            f"Recipient view DOM element {idx+1} '{actual}' did not match keywords for {expected['key']}"
        )


def test_z5_strict_order_in_pdf_extraction(live_server):
    """Asserts strict sequential order of all 10 elements in extracted PDF text."""
    token = create_access_token(
        data={"sub": "01711223344", "phone": "01711223344", "role": "citizen"}
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        page.goto(f"{live_server}/signin", wait_until="domcontentloaded")
        page.evaluate(
            """({ tok }) => {
                localStorage.setItem('ain_token', tok);
                localStorage.setItem('ain_ai_token', tok);
                localStorage.setItem('auth_token', tok);
                localStorage.setItem('token', tok);
                localStorage.setItem('ain_user_role', 'citizen');
            }""",
            {"tok": token},
        )

        page.goto(f"{live_server}/cases/demo_case_001/brief", wait_until="domcontentloaded")
        pdf_bytes = page.pdf(format="A4", print_background=True)
        browser.close()

    reader = PdfReader(io.BytesIO(pdf_bytes))
    full_pdf_text = "\n".join(p.extract_text() or "" for p in reader.pages)

    # Clean multi-line wrapping and find position of each section heading in PDF
    positions = []
    last_pos = -1

    for item in SRS_M08_ORDERED_SECTIONS:
        num = item["num"]
        # Find prefix like "১." or "১ . " in PDF text
        pattern = re.compile(rf"{num}\s*\.\s*", re.MULTILINE)
        found = None
        for m in pattern.finditer(full_pdf_text):
            if m.start() > last_pos:
                found = m.start()
                break

        assert found is not None, (
            f"Section {num} ({item['key']}) not found in PDF extracted text after index {last_pos}!"
        )
        assert found > last_pos, (
            f"Section {num} ({item['key']}) position {found} is not strictly after previous position {last_pos}!"
        )
        positions.append(found)
        last_pos = found

    assert len(positions) == 10, f"Expected 10 strictly ordered positions in PDF, found {len(positions)}"
