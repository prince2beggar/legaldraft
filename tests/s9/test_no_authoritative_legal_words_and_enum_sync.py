"""
Directive Z8 (b and c): Scan for Prohibited Authoritative Words & Canonical Enum Sync.

Requirements:
1. Scans all static HTML pages and formatters.js for authoritative legal wording
   that must not appear without lawyer approval ("সংবিধিবদ্ধ", "আইনত বাধ্যতামূলক",
   "বাধ্যতামূলক বিধান", "চূড়ান্ত আইনি সিদ্ধান্ত", "আইনজীবীর বিকল্প" as listed in docs/copy_review.md).
2. Fails on any hit.
3. Enforces that ui_copy/enums.json is the ONE canonical source from which both
   backend/app/static/formatters.js ENUM_MAPS and docs/copy_review.md are generated;
   fails on any diff (via scripts/generate_enum_artifacts.py --check).
4. Verifies admin_rules.html uses neutral wording with [নমুনা] / 'যাচাই বাকি'.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = REPO_ROOT / "backend" / "app" / "static"
COPY_REVIEW_DOC = REPO_ROOT / "docs" / "copy_review.md"

PROHIBITED_WORDS = [
    "সংবিধিবদ্ধ",
    "আইনত বাধ্যতামূলক",
    "বাধ্যতামূলক বিধান",
    "চূড়ান্ত আইনি সিদ্ধান্ত",
    "আইনজীবীর বিকল্প",
]


def test_z8_no_authoritative_words_in_static_pages_and_formatters():
    """Scans all static HTML templates and formatters.js for prohibited authoritative words."""
    assert STATIC_DIR.exists(), f"Static directory not found: {STATIC_DIR}"

    violations = []

    # Check all static HTML files and formatters.js
    targets = list(STATIC_DIR.glob("*.html")) + [STATIC_DIR / "formatters.js"]

    for file_path in targets:
        if not file_path.exists():
            continue
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            for line_idx, line in enumerate(content.splitlines(), 1):
                for word in PROHIBITED_WORDS:
                    if word in line:
                        violations.append(
                            f"{file_path.name}:{line_idx} contains prohibited word '{word}': {line.strip()}"
                        )
        except Exception as e:
            pytest.fail(f"Failed to read {file_path}: {e}")

    assert not violations, (
        f"Found {len(violations)} prohibited authoritative word violation(s) in static UI:\n"
        + "\n".join(violations)
    )


def test_z8_admin_rules_neutral_wording_and_sample_tags():
    """Verifies admin_rules.html has neutral wording with [নমুনা] / 'যাচাই বাকি'."""
    rules_page = STATIC_DIR / "admin_rules.html"
    assert rules_page.exists(), "admin_rules.html not found"
    content = rules_page.read_text(encoding="utf-8")

    assert "সংবিধিবদ্ধ" not in content, (
        "admin_rules.html still contains 'সংবিধিবদ্ধ'! Must be neutral wording."
    )
    assert "[নমুনা]" in content or "যাচাই বাকি" in content, (
        "admin_rules.html missing '[নমুনা]' or 'যাচাই বাকি' markers for sample rules!"
    )


def test_z8_canonical_enums_sync_check():
    """Verifies formatters.js and docs/copy_review.md are strictly in sync with ui_copy/enums.json."""
    script_path = REPO_ROOT / "scripts" / "generate_enum_artifacts.py"
    assert script_path.exists(), f"Missing generator script: {script_path}"

    result = subprocess.run(
        [sys.executable, str(script_path), "--check"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        f"Canonical enum artifacts are out of sync with ui_copy/enums.json!\n"
        f"Stdout: {result.stdout}\n"
        f"Stderr: {result.stderr}\n"
        f"Run 'python scripts/generate_enum_artifacts.py' to regenerate."
    )


def test_zw5_single_canonical_sample_limit_tag_invariance():
    """Directive ZW5: Enforce single canonical sample-limit tag across static pages, docs/ux_*, and mock-ups.

    Single canonical string defined in ui_copy/enums.json: '[নমুনা - যাচাই বাকি]'.
    Fails if any other variant (e.g. '[নমুনা] — যাচাই বাকি', '[নমুনা — যাচাই বাকি]',
    '[নমুনা] - যাচাই বাকি', etc.) appears in static pages, docs/ux_* or mock-ups.
    """
    import json
    import re

    enums_path = REPO_ROOT / "ui_copy" / "enums.json"
    assert enums_path.exists(), f"Missing enums.json at {enums_path}"
    enums_data = json.loads(enums_path.read_text(encoding="utf-8"))

    canonical_tag = enums_data.get("system_tags", {}).get("sample_limit", {}).get("bn")
    assert canonical_tag == "[নমুনা - যাচাই বাকি]", (
        f"Expected '[নমুনা - যাচাই বাকি]' as canonical tag in enums.json, got: {canonical_tag}"
    )

    targets = (
        list(STATIC_DIR.glob("*.html"))
        + [STATIC_DIR / "formatters.js"]
        + list((REPO_ROOT / "docs" / "ux_mockups").glob("*.html"))
        + list((REPO_ROOT / "docs").glob("ux_*.md"))
    )

    # Regex matching any variant combining 'নমুনা' and 'যাচাই বাকি'
    variant_regex = re.compile(
        r"\[\s*নমুনা\s*[\-\—\–\:\/]\s*যাচাই\s*বাকি\s*\]|"
        r"\[\s*নমুনা\s*\]\s*[\-\—\–\:\/]?\s*\(?যাচাই\s*বাকি\)?|"
        r"\[\s*নমুনা\s*\]\s*—\s*যাচাই\s*বাকি|"
        r"\[\s*নমুনা\s*\]\s*-\s*যাচাই\s*বাকি"
    )

    violations = []
    canonical_occurrences = 0

    for target in targets:
        if not target.exists():
            continue
        text = target.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(text.splitlines(), start=1):
            if canonical_tag in line:
                canonical_occurrences += 1
            for match in variant_regex.finditer(line):
                matched = match.group(0)
                if matched != canonical_tag:
                    violations.append(
                        f"{target.relative_to(REPO_ROOT)}:{line_no} "
                        f"Non-canonical variant '{matched}' (expected '{canonical_tag}'): {line.strip()}"
                    )

    assert canonical_occurrences > 0, f"Canonical tag '{canonical_tag}' was not found in any target file!"
    assert not violations, (
        f"Found {len(violations)} non-canonical sample-limit tag variant(s):\n"
        + "\n".join(violations)
    )

