#!/usr/bin/env python3
"""
Canonical UI Copy & Enum Artifact Generator (Directive Z8).
Single source of truth: ui_copy/enums.json.
Generates:
1. backend/app/static/formatters.js ENUM_MAPS section
2. docs/copy_review.md full terminology & lawyer review glossary
"""

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENUMS_JSON_PATH = REPO_ROOT / "ui_copy" / "enums.json"
FORMATTERS_JS_PATH = REPO_ROOT / "backend" / "app" / "static" / "formatters.js"
COPY_REVIEW_MD_PATH = REPO_ROOT / "docs" / "copy_review.md"

PROHIBITED_AUTHORITATIVE_WORDS = [
    {
        "word": "সংবিধিবদ্ধ",
        "reason": "Statutory / authoritative claim prohibited without verified legal bar counsel review (Standing Rule 5). Use [নমুনা] / 'যাচাই বাকি'.",
    },
    {
        "word": "আইনত বাধ্যতামূলক",
        "reason": "Legally binding / mandatory outcome claim prohibited. AI outputs cannot give definitive binding legal advice.",
    },
    {
        "word": "বাধ্যতামূলক বিধান",
        "reason": "Mandatory statutory provision claim prohibited without authenticated lawyer confirmation.",
    },
    {
        "word": "চূড়ান্ত আইনি সিদ্ধান্ত",
        "reason": "Final legal adjudication claim prohibited; system provides informational support, not court rulings.",
    },
    {
        "word": "আইনজীবীর বিকল্প",
        "reason": "Unauthorized Practice of Law (UPL) boundary: system is explicitly not a substitute for an advocate.",
    },
]


def load_enums() -> dict:
    if not ENUMS_JSON_PATH.exists():
        raise FileNotFoundError(f"Missing canonical source: {ENUMS_JSON_PATH}")
    return json.loads(ENUMS_JSON_PATH.read_text(encoding="utf-8"))


def generate_formatters_js_map(enums: dict) -> str:
    lines = ["const ENUM_MAPS = {"]
    for cat_key, items in enums.items():
        lines.append(f"  {cat_key}: {{")
        for code, data in items.items():
            bn = data["bn"].replace("'", "\\'")
            lines.append(f"    {code}: '{bn}',")
        lines.append("  },")
    lines.append("};")
    lines.append("ENUM_MAPS.document_type = ENUM_MAPS.doc_type;")
    return "\n".join(lines)


def update_formatters_js(enums: dict, check_only: bool = False) -> bool:
    js_content = FORMATTERS_JS_PATH.read_text(encoding="utf-8")
    new_map = generate_formatters_js_map(enums)

    pattern = r"(/\*\*\s*\*\s*Comprehensive Strict Bangla Enum Translation Table\s*\*/\s*\n)const ENUM_MAPS = \{.*?\};\s*ENUM_MAPS\.document_type = ENUM_MAPS\.doc_type;"
    replacement = r"\g<1>" + new_map

    new_content, count = re.subn(pattern, replacement, js_content, flags=re.DOTALL)
    if count == 0:
        raise ValueError("Could not find ENUM_MAPS block in formatters.js")

    if check_only:
        return new_content == js_content

    if new_content != js_content:
        FORMATTERS_JS_PATH.write_text(new_content, encoding="utf-8")
        return True
    return False


def generate_copy_review_md(enums: dict) -> str:
    lines = [
        "# আইন-এআই (AIN-AI) বাংলা কপি ও পারিভাষিক শব্দকোষ পর্যালোচনা",
        "**নথি:** `docs/copy_review.md`  ",
        "**একক সত্য উৎস (Single Source of Truth):** `ui_copy/enums.json` (জেনারেটর: `scripts/generate_enum_artifacts.py`)  ",
        "**উদ্দেশ্য:** আইনজীবী এবং বাংলা ভাষা সম্পাদকের (Copy-Editor) পর্যালোচনার জন্য এনাম (Enum) ও ইউজার-ফেসিং লেবেলের সম্পূর্ণ তালিকা।  ",
        "**নির্দেশনা:** Directive Z8 (W1–W4, Z8 সংশ্লিষ্ট সকল লেবেল একত্রিতকরণ ও স্বয়ংক্রিয় জেনারেশন)।",
        "",
        "---",
        "",
        "## ১. নিষিদ্ধ কর্তৃত্বমূলক শব্দ তালিকা (Prohibited Authoritative Word List)",
        "> **স্থায়ী নিয়ম ৫ (Standing Rule 5) ও Directive Z8:** আইনজীবী দ্বারা অনুমোদিত মূল উৎস ছাড়া কোনো আইনি বিধান, সময়সীমা বা ধারাকে 'সংবিধিবদ্ধ' বা 'বাধ্যতামূলক' বলে দাবি করা যাবে না। নিম্নের শব্দগুলো সকল স্ট্যাটিক স্ক্রিন ও অনুবাদে কঠোরভাবে নিষিদ্ধ এবং সিআই (CI) স্ক্যানারে ব্লক করা হয়:",
        "",
        "| নিষিদ্ধ শব্দ (Prohibited Term) | ইংরেজি প্রতিশব্দ | প্রয়োগের ঝুঁকি ও কারণ | প্রস্তাবিত বিকল্প |",
        "| :--- | :--- | :--- | :--- |",
    ]

    for p in PROHIBITED_AUTHORITATIVE_WORDS:
        lines.append(f"| `{p['word']}` | Authoritative Claim | {p['reason']} | `[নমুনা]`, `যাচাই বাকি` |")

    lines.extend([
        "",
        "---",
        "",
        "## ২. ক্যানোনিকাল এনাম ও ইউআই অনুবাদ তালিকা",
        "",
    ])

    titles = {
        "case_type": "মামলার ধরন (`case_type`)",
        "status": "মামলার ও নোটিশের অবস্থা (`status`)",
        "urgency": "জরুরিতা (`urgency`)",
        "priority": "অগ্রাধিকার (`priority`)",
        "deadline_kind": "সময়সীমার প্রকার (`deadline_kind`)",
        "doc_type": "নথিপত্রের ধরন (`doc_type` / `document_type`)",
        "deadline_basis": "সময়সীমা নির্ধারণের ভিত্তি (`deadline_basis`)",
        "deadline_state": "নিশ্চিতকরণের অবস্থা (`deadline_state`)",
    }

    for cat_idx, (cat_key, items) in enumerate(enums.items(), start=1):
        cat_title = titles.get(cat_key, f"{cat_key} (`{cat_key}`)")
        lines.append(f"### ২.{cat_idx} {cat_title}")
        lines.append("")
        lines.append("| Key (অভ্যন্তরীণ কোড) | বর্তমান বাংলা অনুবাদ | আইনজীবী / সম্পাদকের মন্তব্য |")
        lines.append("| :--- | :--- | :--- |")
        for code, data in items.items():
            lines.append(f"| `{code}` | {data['bn']} | {data['comment']} |")
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.extend([
        "## ৩. আইনজীবীর সাথে যাচাইকরণ কর্মপদ্ধতি (Lawyer Review Workflow)",
        "১. কোনো নতুন এনাম বা লেবেল যোগ করতে হলে প্রথমে `ui_copy/enums.json` ফাইলে যোগ করুন।",
        "২. `python scripts/generate_enum_artifacts.py` রান করে `formatters.js` এবং `docs/copy_review.md` পুনরুৎপাদন করুন।",
        "৩. সিআই টেস্ট `tests/s9/test_no_authoritative_legal_words_and_enum_sync.py` নিশ্চিত করবে যে কোনো ফাইলই উৎস থেকে বিচ্যুত হয়নি এবং নিষিদ্ধ কর্তৃত্বমূলক শব্দ অনুপস্থিত।",
        "",
    ])

    return "\n".join(lines)


def update_copy_review_md(enums: dict, check_only: bool = False) -> bool:
    current = COPY_REVIEW_MD_PATH.read_text(encoding="utf-8") if COPY_REVIEW_MD_PATH.exists() else ""
    new_content = generate_copy_review_md(enums)

    if check_only:
        return current.strip() == new_content.strip()

    if current.strip() != new_content.strip():
        COPY_REVIEW_MD_PATH.write_text(new_content, encoding="utf-8")
        return True
    return False


def main():
    check_mode = "--check" in sys.argv
    enums = load_enums()

    if check_mode:
        js_ok = update_formatters_js(enums, check_only=True)
        md_ok = update_copy_review_md(enums, check_only=True)
        if not js_ok or not md_ok:
            print("[FAIL] Enum artifacts are out of sync with ui_copy/enums.json.")
            sys.exit(1)
        print("[OK] Enum artifacts are in sync with ui_copy/enums.json.")
        sys.exit(0)

    js_updated = update_formatters_js(enums, check_only=False)
    md_updated = update_copy_review_md(enums, check_only=False)
    print(f"[SUCCESS] Updated artifacts: formatters.js ({js_updated}), copy_review.md ({md_updated})")


if __name__ == "__main__":
    main()
