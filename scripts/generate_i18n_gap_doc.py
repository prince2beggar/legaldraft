#!/usr/bin/env python3
"""
Generates docs/i18n_gap.md based on the static HTML string inventory (H3 / Sprint S9).
"""

import json
from pathlib import Path


def generate_i18n_gap():
    inv_file = Path("storage/i18n_inventory.json")
    if not inv_file.exists():
        from scripts.inventory_i18n import run_inventory

        data = run_inventory()
    else:
        data = json.loads(inv_file.read_text(encoding="utf-8"))

    files = data["files"]
    totals = data["totals"]

    # Sort files by hardcoded string count descending
    sorted_files = sorted(files, key=lambda x: x["total_user_facing_strings"], reverse=True)

    lines = [
        "# Internationalization (i18n) Gap Analysis & Roadmap (X-003)",
        "",
        "> **Sprint S9 Status:** **NOT SATISFIED / GAP DOCUMENTED**",
        "> While backend translation catalog parity (`/content/i18n/bn.json` and `en.json`) is verified across 76 dictionary keys, the frontend static HTML templates currently utilize hardcoded Bengali strings directly in markup. Full dynamic DOM internationalization is **NOT** satisfied.",
        "",
        "---",
        "",
        "## 1. Inventory Summary",
        "",
        f"- **Total Static HTML Files Audited:** {totals['total_files']}",
        f"- **Total User-Facing Strings Analyzed:** {totals['total_strings']:,}",
        f"- **Hard-coded Bengali Strings:** {totals['hardcoded_bn']:,} ({totals['hardcoded_bn'] / totals['total_strings'] * 100:.1f}%)",
        f"- **Hard-coded English Strings:** {totals['hardcoded_en']:,} ({totals['hardcoded_en'] / totals['total_strings'] * 100:.1f}%)",
        f"- **Elements with `data-i18n` Translation Keys:** {totals['i18n_keyed']:,} (0.0% coverage)",
        "- **Estimated Keys to Extract:** ~450 to 550 unique semantic translation keys (after deduplicating navigation, button labels, and shared status indicators)",
        "",
        "---",
        "",
        "## 2. Top Files with Most Hard-Coded Text",
        "",
        "The following 5 files contain the largest concentration of hardcoded strings:",
        "",
        "| Rank | File Name | Total Strings | Bengali Strings | English Strings | Description / Context |",
        "|---|---|---|---|---|---|",
    ]

    for idx, f in enumerate(sorted_files[:5], start=1):
        lines.append(
            f"| {idx} | `{f['file']}` | {f['total_user_facing_strings']} | {f['hardcoded_bn_count']} | {f['hardcoded_en_count']} | Core citizen/admin workflow template |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## 3. Complete File-by-File String Inventory",
            "",
            "| File Name | Total Strings | Hard-coded Bengali | Hard-coded English | `data-i18n` Keyed | Coverage % |",
            "|---|---|---|---|---|---|",
        ]
    )

    for f in sorted_files:
        lines.append(
            f"| `{f['file']}` | {f['total_user_facing_strings']} | {f['hardcoded_bn_count']} | {f['hardcoded_en_count']} | {f['i18n_keyed_count']} | {f['coverage_percent']:.1f}% |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## 4. Proposed Minimal Client-Side i18n Architecture",
            "",
            "To avoid heavy third-party framework overhead, the proposed implementation uses a single lightweight vanilla JavaScript module (`i18n.js`):",
            "",
            "### Architecture Specification:",
            "1. **Catalog Delivery:** On page initialization, `i18n.js` detects the user's preferred language (from `localStorage.getItem('lang')` or `navigator.language` or query param `?lang=...`, defaulting to `bn`).",
            "2. **Catalog Fetch & Caching:** Calls `GET /api/v1/i18n/{locale}` once and caches the dictionary in `sessionStorage`.",
            "3. **DOM Attribute Translation:**",
            '   - Elements use `data-i18n="key_name"` for text content.',
            '   - Elements use `data-i18n-placeholder="key_name"` for input placeholders.',
            '   - Elements use `data-i18n-title="key_name"` for tooltips / aria-labels.',
            "4. **Dynamic DOM Sweep:** `i18n.applyTranslations()` queries `document.querySelectorAll('[data-i18n], [data-i18n-placeholder]')` and updates `.innerText` / attributes in a single animation frame batch.",
            "5. **Digit Formatting:** When locale is `bn`, numeric quantities and dates are piped through `toBanglaDigits()` helper.",
            "",
            "---",
            "",
            "## 5. Phased Implementation Roadmap (Page Priority Order)",
            "",
            "Migration is recommended in the following phased order based on user exposure and citizen criticality:",
            "",
            "1. **Phase 1: Entry & Authentication (Highest Citizen Exposure)**",
            "   - `signin.html` (Citizen phone OTP login)",
            "   - `home.html` (Citizen dashboard & triage)",
            "   - `intake.html` (Guided 10-step intake wizard)",
            "",
            "2. **Phase 2: External Facing & Sharing (Recipient Exposure)**",
            "   - `shared_brief.html` (External recipient viewer, OTP challenge, watermark)",
            "   - `case_brief.html` (Case brief builder & ConsentSheet modal)",
            "   - `sharing.html` (Consent management & access history)",
            "",
            "3. **Phase 3: Case Management & Guided Drafting**",
            "   - `cases.html` / `case_detail.html` (Case folders & party lists)",
            "   - `draft.html` (Guided legal drafting & checklist)",
            "   - `notifications.html` / `notification_settings.html`",
            "",
            "4. **Phase 4: Admin & Specialized Portals**",
            "   - `admin.html` & `admin_system.html` (System observability)",
            "   - `admin_templates.html` & `admin_emergency_contacts.html`",
            "   - `library.html`, `admin_rules.html`, `admin_evals.html`, `admin_sources.html`",
            "",
            "---",
            "",
            "> [!IMPORTANT]",
            "> **S9 DOD Compliance Note**: In accordance with Directive H3, this document registers the exact string inventory and implementation blueprint. No hasty client-side refactor was applied in S9 to avoid regressions, and requirement **X-003 is formally documented as an open gap** pending Phase 1 execution.",
        ]
    )

    doc_path = Path("docs/i18n_gap.md")
    doc_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated {doc_path} with {len(lines)} lines.")


if __name__ == "__main__":
    generate_i18n_gap()
