"""
Generates the REQUIREMENT -> TEST table from reports/junit_latest.xml.
Columns: Requirement, Test Node ID, What It Asserts, Status, Duration.
Usage: python scripts/req_map.py
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
JUNIT_PATH = REPO_ROOT / "reports" / "junit_latest.xml"

# Requirements R1-R12 definitions and assertion summaries
REQ_METADATA = {
    "R1": {
        "test_suffix": "test_r1_dev_mode_unset",
        "description": "Asserts DEV_MODE unset: demo buttons absent from HTML, dev_otp never in API responses, /auth/demo-login returns 404.",
    },
    "R2": {
        "test_suffix": "test_r2_emergency_contacts_verification",
        "description": "Asserts no seeded contact verified/invented; unverified labelled placeholders; verify rejects non-admin and empty note; writes audit.",
    },
    "R3": {
        "test_suffix": "test_r3_undefined_never_appears_sweep",
        "description": "Asserts the text 'undefined' never appears anywhere in innerText across all citizen and admin pages via Playwright sweep.",
    },
    "R4": {
        "test_suffix": "test_r4_urgent_banner_viewport_and_zero_ai_calls",
        "description": "Asserts selecting urgent chip shows UrgentBanner within first viewport (top < 640px) at 360x640 with strictly 0 AI gateway calls.",
    },
    "R5": {
        "test_suffix": "test_r5_review_screen_confirm_and_ai_badges",
        "description": "Asserts review screen has nothing pre-ticked, per-section Confirm, AI proposed/amber labels, as-of date, fake-mode banner, and Bangla SRS enum.",
    },
    "R6": {
        "test_suffix": "test_r6_fact_grounding_and_hostile_provider_dropped",
        "description": "Asserts every displayed fact has span_in_user_text; ungrounded facts, outcome predictions, and conclusions from hostile provider dropped/sanitized.",
    },
    "R7": {
        "test_suffix": "test_r7_under_triage_redteam_30_prompts",
        "description": "Asserts under-triage red-team across >= 30 prompts (Bangla, English, spelling variants, indirect phrasing) never misses or lowers urgency.",
    },
    "R8": {
        "test_suffix": "test_r8_browser_journey_intake_to_home_next_action",
        "description": "Asserts browser journey: sign in -> chip -> banner -> 10 questions -> review -> confirm per section -> create case -> Home Next Action (P1/P8).",
    },
    "R9": {
        "test_suffix": "test_r9_responsive_all_viewports_and_shell",
        "description": "Asserts 5-tab bottom bar at 360 (rail at 768, sidebar at 1280), no horizontal scroll, min font 16px, Bengali font loaded, no emoji nav icons.",
    },
    "R10": {
        "test_suffix": "test_r10_intake_ownership_isolation_and_audit",
        "description": "Asserts User A's intake session cannot be read/modified by User B across all endpoints, and audit entries are recorded.",
    },
    "R11": {
        "test_suffix": "test_r11_blind_outcome_filter_regression",
        "description": "Asserts 24 held-out paraphrased outcome predictions (Bangla and English) are caught with 0 misses.",
    },
    "R12": {
        "test_suffix": "test_r12_false_positive_benign_sentences",
        "description": "Asserts >= 20 benign factual legal sentences pass through outcome filter completely unchanged (false positive count == 0).",
    },
}


def generate_req_map():
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

    print("| Requirement | Test Node ID | What It Asserts | Status | Duration |")
    print("| :--- | :--- | :--- | :---: | :---: |")

    for req_id, meta in REQ_METADATA.items():
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
    generate_req_map()
