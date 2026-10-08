"""
Playwright E2E UI Coverage & Script Purity Tests for Notice Interpreter Screen (SRS M04, Sprint S5).

Tests:
1. Real Playwright tests rendering all 7 outcomes:
   - normal
   - certainty not_sure
   - explain simpler
   - could-not-read-clearly
   - non-notice document
   - English notice
   - blurry scan
2. In all 7 outcomes, asserts DOM presence of:
   - AI disclaimer label: "AI ব্যাখ্যা — আইনজীবীর দ্বারা যাচাইকৃত নয়"
   - As-of date display: non-empty "হালনাগাদ: ..."
   - Certainty label: one of ("স্পষ্ট", "যাচাই করুন", "নিশ্চিত নই"), never "পরিष्कार"
   - Experimental fake provider banner: "পরীক্ষামূলক মোড: এটি আসল AI বিশ্লেষণ নয়।"
3. Ticking a checklist item creates a task (data-task-id, data-task-status="created", .done class).
4. DeadlineCard displays Bangla digits and "দিন বাকি".
5. Script purity test: Scans backend/app/static/*.html to ensure no Devanagari character contamination
   and zero occurrences of legacy word "পরিष्कार".
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright

STATIC_HTML_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "backend"
    / "app"
    / "static"
    / "document_notice.html"
)
STATIC_DIR = STATIC_HTML_PATH.parent

OUTCOMES = [
    "normal",
    "not_sure",
    "explain_simpler",
    "could_not_read_clearly",
    "non_notice",
    "english",
    "blurry",
]


@pytest.fixture(scope="module")
def browser_instance():
    """Module-scoped headless chromium browser instance."""
    p = sync_playwright().start()
    browser = p.chromium.launch(headless=True)
    yield browser
    browser.close()
    p.stop()


@pytest.mark.parametrize("outcome", OUTCOMES)
def test_ui_playwright_renders_seven_outcomes_with_exact_labels(browser_instance, outcome: str):
    """
    Renders 7 outcomes in real Playwright browser and asserts in DOM:
    - AI label is present: 'AI ব্যাখ্যা — আইনজীবীর দ্বারা যাচাইকৃত নয়'
    - As-of date is present and non-empty
    - Certainty label is present (one of: 'স্পষ্ট', 'যাচাই করুন', 'নিশ্চিত নই'; never 'পরিष्कार')
    - Fake provider banner is visible: 'পরীক্ষামূলক মোড: এটি আসল AI বিশ্লেষণ নয়।'
    """
    page = browser_instance.new_page()
    uri = STATIC_HTML_PATH.as_uri() + f"?variant={outcome}"
    page.goto(uri)

    # 1. AI label check
    disclaimer = page.locator("#disclaimerText")
    assert disclaimer.is_visible()
    assert disclaimer.inner_text().strip() == "AI ব্যাখ্যা — আইনজীবীর দ্বারা যাচাইকৃত নয়"

    # 2. As-of date check
    as_of = page.locator("#asOfDateDisplay")
    assert as_of.is_visible()
    as_of_text = as_of.inner_text().strip()
    assert "হালনাগাদ:" in as_of_text
    assert len(as_of_text) > 10

    # 3. Certainty label check
    certainty = page.locator("#certaintyBadge")
    assert certainty.is_visible()
    certainty_text = certainty.inner_text().strip()
    assert certainty_text in ("স্পষ্ট", "যাচাই করুন", "নিশ্চিত নই")
    assert "পরিষ্কার" not in certainty_text

    # 4. Fake provider banner check
    banner = page.locator("#fakeProviderBanner")
    assert banner.is_visible()
    assert "পরীক্ষামূলক মোড: এটি আসল AI বিশ্লেষণ নয়।" in banner.inner_text()

    page.close()


def test_ui_playwright_ticking_checklist_creates_task(browser_instance):
    """
    Asserts that ticking a checklist item creates a task:
    - data-task-id is present on the checklist item
    - DOM state updates: .done class and data-task-status="created"
    - Toast feedback appears: 'টাস্ক তালিকায় যুক্ত হয়েছে'
    """
    page = browser_instance.new_page()
    page.goto(STATIC_HTML_PATH.as_uri() + "?variant=normal")

    first_item = page.locator("#actionsChecklist li").first
    assert first_item.is_visible()
    task_id = first_item.get_attribute("data-task-id")
    assert task_id is not None and len(task_id) > 0

    # Before ticking
    checkbox = first_item.locator("input[type='checkbox']")
    assert not checkbox.is_checked()
    assert "done" not in (first_item.get_attribute("class") or "")

    # Tick checkbox
    checkbox.check()

    # After ticking: DOM state updated
    assert "done" in (first_item.get_attribute("class") or "")
    assert first_item.get_attribute("data-task-status") == "created"

    # Toast displayed
    toast = page.locator("#toastMessage")
    assert toast.is_visible()
    assert "টাস্ক তালিকায় যুক্ত হয়েছে" in toast.inner_text()

    page.close()


def test_ui_playwright_deadline_card_renders_bangla_digits_and_days_left(browser_instance):
    """
    Asserts that DeadlineCard displays:
    - Bangla digits in the due date
    - 'দিন বাকি' in days left badge
    - Confirm and manual date buttons
    """
    page = browser_instance.new_page()
    page.goto(STATIC_HTML_PATH.as_uri() + "?variant=normal")

    deadline_section = page.locator("#deadlineCardSection")
    assert deadline_section.is_visible()

    # Bangla digits in due date display
    date_display = page.locator("#deadlineDateDisplay")
    assert date_display.is_visible()
    date_text = date_display.inner_text()
    bangla_digits = ["০", "১", "২", "৩", "৪", "৫", "৬", "৭", "৮", "৯"]
    assert any(d in date_text for d in bangla_digits), (
        f"No Bangla digits found in date: {date_text}"
    )

    # Days left badge contains 'দিন বাকি'
    days_badge = page.locator("#daysLeftBadge")
    assert days_badge.is_visible()
    badge_text = days_badge.inner_text()
    assert "দিন বাকি" in badge_text
    assert any(d in badge_text for d in bangla_digits)

    # Actions buttons
    btn_confirm = page.locator("#btnConfirmDeadline")
    assert btn_confirm.is_visible()
    assert "নিশ্চিত করুন" in btn_confirm.inner_text()

    btn_own_date = page.locator("#btnSetOwnDate")
    assert btn_own_date.is_visible()

    page.close()


def test_script_purity_no_devanagari_characters_in_static_html():
    """
    Script Purity & Devanagari Prevention Test:
    Ensures no HTML file in backend/app/static contains Devanagari letter characters
    (range U+0900 to U+0963, U+0966 to U+097F) or the legacy word 'পরিষ্কার'.
    Only canonical Bengali script (U+0980-U+09FF) and standard shared Indic danda (U+0964, U+0965)
    are permitted.
    """
    devanagari_letter_pattern = re.compile(r"[\u0900-\u0963\u0966-\u097F]")

    for html_file in STATIC_DIR.glob("*.html"):
        content = html_file.read_text(encoding="utf-8")

        # 1. No legacy word 'পরিষ্কার'
        assert "পরিষ্কার" not in content, (
            f"Found forbidden word 'পরিষ্কার' in {html_file.name}. Use 'স্পষ্ট' instead."
        )

        # 2. No Devanagari script letters
        matches = devanagari_letter_pattern.findall(content)
        assert len(matches) == 0, (
            f"Found {len(matches)} Devanagari characters in {html_file.name}: "
            f"{[f'U+{ord(c):04X}' for c in set(matches)]}"
        )
