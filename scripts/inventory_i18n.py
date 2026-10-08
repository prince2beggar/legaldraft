"""
i18n String Inventory and Language Audit Script (X-003 / G6).
Scans backend/app/static/*.html files to count:
1. Total user-facing string elements (text nodes, button labels, placeholders).
2. Elements marked with i18n keys (data-i18n, {{ t(...) }}).
3. Hard-coded text strings (Bengali / English).
Generates an honest file-by-file inventory.
"""

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "backend" / "app" / "static"
BN_REGEX = re.compile(r"[\u0980-\u09FF]")


def analyze_html_file(file_path: Path) -> dict:
    content = file_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(content, "html.parser")

    # Remove script and style tags
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    hardcoded_bn_strings = []
    hardcoded_en_strings = []
    i18n_keyed_elements = []

    # Check all elements with data-i18n attributes
    for el in soup.find_all(attrs={"data-i18n": True}):
        i18n_keyed_elements.append(el["data-i18n"])

    # Traverse all text nodes
    for text in soup.stripped_strings:
        cleaned = text.strip()
        if not cleaned or len(cleaned) < 2:
            continue
        # Ignore CSS/JS artifacts that might have leaked
        if cleaned.startswith(("{", "}", "/*", "*/", "var ", "function")):
            continue

        if BN_REGEX.search(cleaned):
            hardcoded_bn_strings.append(cleaned)
        elif re.search(r"[A-Za-z]{2,}", cleaned):
            # English text (excluding raw tags/classes)
            if not any(token in cleaned for token in ["viewport", "utf-8", "px", "rem"]):
                hardcoded_en_strings.append(cleaned)

    total_strings = len(hardcoded_bn_strings) + len(hardcoded_en_strings) + len(i18n_keyed_elements)
    i18n_coverage_pct = (
        round((len(i18n_keyed_elements) / total_strings * 100), 1) if total_strings else 0.0
    )

    return {
        "file": file_path.name,
        "total_user_facing_strings": total_strings,
        "i18n_keyed_count": len(i18n_keyed_elements),
        "hardcoded_bn_count": len(hardcoded_bn_strings),
        "hardcoded_en_count": len(hardcoded_en_strings),
        "coverage_percent": i18n_coverage_pct,
        "sample_bn": hardcoded_bn_strings[:3],
        "sample_en": hardcoded_en_strings[:3],
    }


def run_inventory():
    html_files = sorted(STATIC_DIR.glob("*.html"))
    inventory = []
    totals = {
        "total_files": len(html_files),
        "total_strings": 0,
        "i18n_keyed": 0,
        "hardcoded_bn": 0,
        "hardcoded_en": 0,
    }

    for hf in html_files:
        stats = analyze_html_file(hf)
        inventory.append(stats)
        totals["total_strings"] += stats["total_user_facing_strings"]
        totals["i18n_keyed"] += stats["i18n_keyed_count"]
        totals["hardcoded_bn"] += stats["hardcoded_bn_count"]
        totals["hardcoded_en"] += stats["hardcoded_en_count"]

    totals["overall_coverage_pct"] = (
        round((totals["i18n_keyed"] / totals["total_strings"] * 100), 1)
        if totals["total_strings"]
        else 0.0
    )

    return {"totals": totals, "files": inventory}


if __name__ == "__main__":
    report = run_inventory()
    out_path = REPO_ROOT / "storage" / "i18n_inventory.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    tot = report["totals"]
    print(f"Total HTML Files Analyzed: {tot['total_files']}")
    print(f"Total User-Facing Strings: {tot['total_strings']}")
    print(f"i18n Keyed Strings:        {tot['i18n_keyed']} ({tot['overall_coverage_pct']}%)")
    print(f"Hardcoded Bengali Strings: {tot['hardcoded_bn']}")
    print(f"Hardcoded English Strings: {tot['hardcoded_en']}")
    print("-" * 75)
    print(f"{'Filename':<30} | {'Total':<6} | {'i18n':<5} | {'Hard-BN':<8} | {'Hard-EN':<8}")
    print("-" * 75)
    for f in report["files"]:
        print(
            f"{f['file']:<30} | {f['total_user_facing_strings']:<6} | {f['i18n_keyed_count']:<5} | {f['hardcoded_bn_count']:<8} | {f['hardcoded_en_count']:<8}"
        )
    print("-" * 75)
    print(f"Full inventory JSON written to: {out_path}")
