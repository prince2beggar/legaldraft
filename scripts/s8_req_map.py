"""
Generates the Sprint S8 REQUIREMENT / AC -> TEST table from reports/junit_latest.xml or test results.
Columns: Requirement / AC, Test Node ID, What It Asserts, Status, Duration.
Usage: python scripts/s8_req_map.py
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
JUNIT_PATH = REPO_ROOT / "reports" / "junit_latest.xml"

S8_REQUIREMENTS = {
    "C1 (No External Hosts)": {
        "test_suffix": "test_c1_no_external_host_dependencies",
        "description": "Asserts zero external host URLs (CDNs, Google Fonts) in static HTML/CSS/JS files.",
    },
    "AC-M05-1 (Approved Template Only)": {
        "test_suffix": "test_ac_m05_1_citizen_blocked_from_unapproved_template",
        "description": "Citizen blocked from starting draft from non-approved template (HTTP 403 in prod config).",
    },
    "AC-M05-2 (Reviewed Prefill Only)": {
        "test_suffix": "test_ac_m05_2_prefill_only_from_reviewed_verified_fields",
        "description": "Prefill candidates drawn ONLY from reviewed/verified fields (extracted fields NEVER offered); citizen override works.",
    },
    "AC-M05-3 (Checklist Gate)": {
        "test_suffix": "test_ac_m05_3_finalize_rejected_until_every_checklist_item_confirmed",
        "description": "Finalize draft is strictly rejected until every execution-checklist item is confirmed.",
    },
    "AC-M05-4 / F2 (PDF Shaping & Watermark)": {
        "test_suffix": "test_ac_m05_4_bangla_conjuncts_shaping_and_watermark_in_pdf",
        "description": "Rasterizes PDF with pypdfium2 (scale 1.5), compares with reference PNG (ক্ষ, জ্ঞ, ন্দ, স্ত্র, ক্ত, ঙ্গ, শ্র; RMSE < 2.0); verifies NotoSansBengali font embed; watermark present in PDF before final and removed after.",
    },
    "AC-M05-5 (Numeral-Words & Party Names)": {
        "test_suffix": "test_ac_m05_5_consistency_checks_numeral_words_and_inconsistent_party_names",
        "description": "Deterministic check step catches numerals-vs-words mismatch (Bangla and English) AND catches inconsistent party names.",
    },
    "AC-M05-6 (Template Metadata & Footer)": {
        "test_suffix": "test_ac_m05_6_template_metadata_recorded_and_shown_in_export_footer",
        "description": "Template name, version, and effective date recorded on draft and rendered in DOCX & PDF export footers.",
    },
    "Dual Custody Enforcement": {
        "test_suffix": "test_template_dual_custody_enforcement",
        "description": "Dual custody: author cannot approve own template; reviewer cannot approve without approval note.",
    },
    "Staging Allow Draft Templates Flag": {
        "test_suffix": "test_staging_allow_draft_templates_flag",
        "description": "STAGING_ALLOW_DRAFT_TEMPLATES flag enables draft templates in dev/staging with prominent Bangla draft banner.",
    },
    "Checklist Persistence": {
        "test_suffix": "test_checklist_states_persistence",
        "description": "Checklist state transitions persist reliably across sessions.",
    },
    "F3 (Encryption At Rest)": {
        "test_suffix": "test_draft_files_encrypted_at_rest",
        "description": "Draft export files stored encrypted at rest with AES-256-GCM; ciphertext bytes verified; roundtrip decryption works; wrong key fails with InvalidTag.",
    },
    "F3 (Ownership Isolation & Audit)": {
        "test_suffix": "test_draft_ownership_isolation_and_audit",
        "description": "User A cannot read/modify/export User B's draft; audit entries emitted for create, answers, check, preview, checklist, finalize, export, delete.",
    },
    "F3 (Retired Template Immutability)": {
        "test_suffix": "test_retired_template_cannot_start_new_drafts",
        "description": "Retired template cannot start new drafts; existing drafts preserve their recorded template version.",
    },
    "F3 (AI Structural Bounds & Safety)": {
        "test_suffix": "test_draft_helper_hostile_provider_structural_bounds",
        "description": "draft.helper.v1 hostile provider: free clause text, outcome predictions, made-up clause IDs blocked; only template's approved optional clause IDs pass.",
    },
    "F3 (Question Type Number)": {
        "test_suffix": "test_question_type_number_with_min_max_validation",
        "description": "Question type 'number' supported with min_value and max_value schema validation.",
    },
    "F3 (Browser Journey E2E)": {
        "test_suffix": "test_browser_journey_drafting_end_to_end",
        "description": "Full citizen browser journey: sign in -> /draft -> DT-01 -> answer questions incl. prefill chip -> check -> preview -> checklist -> finalize -> export DOCX & PDF.",
    },
    "F3 (Undefined Sweep)": {
        "test_suffix": "test_undefined_never_appears_draft_sweep",
        "description": "Playwright sweep confirms the string 'undefined' never appears on citizen drafting or admin template screens.",
    },
    "F3 (X-001 Route Authorization)": {
        "test_suffix": "test_x001_route_sweep_and_role_restrictions_drafts",
        "description": "Route sweep confirms unauthenticated access blocked (HTTP 401) and citizen role blocked from admin template routes (HTTP 403).",
    },
    "F3 (Responsive All Viewports)": {
        "test_suffix": "test_responsive_draft_screens_all_viewports",
        "description": "Responsive verification at 360x640 (bottom 5-tab bar), 768x1024 (side rail), and 1280x800 (sidebar) with no horizontal scroll and min font 16px.",
    },
}


def generate_s8_req_map():
    if not JUNIT_PATH.exists():
        print(f"Error: {JUNIT_PATH} not found. Run CI first.", file=sys.stderr)
        sys.exit(1)

    tree = ET.parse(JUNIT_PATH)
    root = tree.getroot()

    testcases = root.findall(".//testcase")
    tc_lookup = {}
    for tc in testcases:
        name = tc.get("name", "")
        classname = tc.get("classname", "")
        file_path = tc.get("file", classname.replace(".", "/") + ".py")
        node_id = f"{file_path}::{name}"
        duration = tc.get("time", "0.000")
        failure = tc.find("failure")
        skipped = tc.find("skipped")
        status = (
            "FAILED" if failure is not None else ("SKIPPED" if skipped is not None else "PASSED")
        )
        tc_lookup[name] = (node_id, status, duration)

    print("| Requirement / AC | Test Node ID | What It Asserts | Status | Duration |")
    print("| :--- | :--- | :--- | :---: | :---: |")

    for req_id, meta in S8_REQUIREMENTS.items():
        test_func = meta["test_suffix"]
        info = tc_lookup.get(test_func)
        if info:
            node_id, status, duration = info
            print(
                f"| **`{req_id}`** | `{node_id}` | {meta['description']} | **{status}** | {duration}s |"
            )
        else:
            print(
                f"| **`{req_id}`** | *[Pending in test suite]* | {meta['description']} | **UNVERIFIED** | - |"
            )


if __name__ == "__main__":
    generate_s8_req_map()
