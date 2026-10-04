"""
Generates an AC-ID to Test Name mapping table from reports/junit_latest.xml.
Usage: python scripts/ac_map.py
"""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
JUNIT_PATH = REPO_ROOT / "reports" / "junit_latest.xml"

def generate_ac_map():
    if not JUNIT_PATH.exists():
        print(f"Error: {JUNIT_PATH} does not exist. Run CI or pytest first.", file=sys.stderr)
        sys.exit(1)

    tree = ET.parse(JUNIT_PATH)
    root = tree.getroot()

    # Match AC patterns in test names: test_ac_m02_1_..., test_ac_s0_1_..., etc.
    # Pattern: ac_([ms]\d+)_(\d+) or similar
    pattern = re.compile(r"ac_([a-zA-Z0-9]+)_([a-zA-Z0-9]+)", re.IGNORECASE)

    ac_entries = []

    # Find testsuites or testcase tags
    testcases = root.findall(".//testcase")
    for tc in testcases:
        name = tc.get("name", "")
        classname = tc.get("classname", "")
        duration = tc.get("time", "0.000")
        failure = tc.find("failure")
        skipped = tc.find("skipped")
        status = "FAILED" if failure is not None else ("SKIPPED" if skipped is not None else "PASSED")

        match = pattern.search(name)
        if match:
            module = match.group(1).upper()
            num = match.group(2).upper()
            ac_id = f"AC-{module}-{num}"
            ac_entries.append((ac_id, name, classname, status, duration))

    # Sort entries by AC ID
    ac_entries.sort(key=lambda x: x[0])

    print("| AC ID | Test Function Name | Test File / Class | Status | Time (s) |")
    print("| :--- | :--- | :--- | :---: | :---: |")
    for ac_id, name, classname, status, duration in ac_entries:
        print(f"| **`{ac_id}`** | `{name}` | `{classname}` | **{status}** | {duration}s |")

    # Print summary counts
    print(f"\nTotal AC tests identified: {len(ac_entries)}")

if __name__ == "__main__":
    generate_ac_map()
