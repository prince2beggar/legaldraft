"""
Directive Z7 (J5): ADR Uniqueness, Sequentiality, and Cross-Reference Integrity Test Suite.

Requirements:
1. ADR numbers in docs/decisions.md are unique and sequential (1..N with zero gaps or duplicates).
2. Every ADR reference (ADR-XXX) anywhere in code, docs, UI, and reports points to an existing ADR.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_z7_adr_numbers_unique_and_sequential():
    """Asserts ADR numbers in docs/decisions.md are unique and strictly sequential."""
    decisions_path = REPO_ROOT / "docs" / "decisions.md"
    assert decisions_path.exists(), f"Missing {decisions_path}"

    content = decisions_path.read_text(encoding="utf-8")

    # Extract all ADR numbers defined in Section 1 (Approved Decisions table)
    sec1 = content.split("## 2.")[0]
    defined_matches = re.findall(r"\|\s*\*\*ADR-(\d+)\*\*", sec1)
    assert defined_matches, "No ADR entries found in docs/decisions.md Section 1"

    adr_numbers = [int(m) for m in defined_matches]

    # 1. Uniqueness
    duplicates = [num for num in adr_numbers if adr_numbers.count(num) > 1]
    assert not duplicates, f"Duplicate ADR numbers found in docs/decisions.md: {set(duplicates)}"

    # 2. Sequentiality
    expected_sequence = list(range(1, len(adr_numbers) + 1))
    assert adr_numbers == expected_sequence, (
        f"ADR numbers are not strictly sequential!\n"
        f"Expected: 1 to {len(adr_numbers)}\n"
        f"Found: {adr_numbers}\n"
        f"Missing: {set(expected_sequence) - set(adr_numbers)}"
    )


def test_z7_every_adr_reference_points_to_existing_adr():
    """Asserts every ADR-XXX reference across code, docs, and reports points to an existing ADR."""
    decisions_path = REPO_ROOT / "docs" / "decisions.md"
    content = decisions_path.read_text(encoding="utf-8")
    defined_adrs = set(int(m) for m in re.findall(r"ADR-(\d+)", content))
    assert defined_adrs, "No ADRs found defined in docs/decisions.md"

    invalid_refs = {}
    pattern = re.compile(r"\bADR-(\d+)\b")

    for ext in ["*.py", "*.md", "*.json", "*.html", "*.js"]:
        for file_path in REPO_ROOT.rglob(ext):
            parts = file_path.parts
            if any(skip in parts for skip in [".git", ".pytest_cache", "node_modules", ".next", "_next", "out"]):
                continue

            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
                for line_idx, line in enumerate(text.splitlines(), 1):
                    for m in pattern.findall(line):
                        num = int(m)
                        if num not in defined_adrs:
                            rel_path = str(file_path.relative_to(REPO_ROOT))
                            invalid_refs.setdefault(num, []).append(f"{rel_path}:{line_idx}")
            except Exception:
                pass

    assert not invalid_refs, (
        "Found invalid ADR references pointing to non-existent ADRs:\n"
        + "\n".join(f"ADR-{k}: {v}" for k, v in invalid_refs.items())
    )
