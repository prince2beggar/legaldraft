#!/usr/bin/env python3
"""
Audit script for ZW3: Analyzes git diff of all modified pre-existing test files.
Counts added vs removed lines containing:
  - assert
  - pytest.skip
  - xfail
  - timeout
  - def test
Lists each removed line with file:line.
"""

import re
import subprocess

TARGET_FILES = [
    "tests/conftest.py",
    "tests/s1/test_x001_route_authorisation_sweep.py",
    "tests/s3/test_s3_api_endpoints.py",
    "tests/s6/test_ac_m02_home.py",
    "tests/s6/test_s6_viewport_responsive.py",
    "tests/s7/test_ac_m11_intake.py",
    "tests/s7/test_s7_requirements.py",
    "tests/s8/test_ac_m05_drafting.py",
    "tests/s9/test_ac_m08_sharing.py",
    "tests/s9/test_m5_click_journey.py",
    "tests/s9/test_s9_hardening.py",
    "tests/s9/test_service_worker.py",
]

KEYWORDS = ["assert", "pytest.skip", "xfail", "timeout", "def test"]

def main():
    print("=" * 80)
    print("PRE-EXISTING TEST ASSERTION & TEST CASE AUDIT (ZW3)")
    print("=" * 80)

    total_added = {k: 0 for k in KEYWORDS}
    total_removed = {k: 0 for k in KEYWORDS}
    all_removed_lines = []

    for file_path in TARGET_FILES:
        res = subprocess.run(
            ["git", "diff", "-U0", "HEAD", "--", file_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True
        )
        diff_text = res.stdout

        current_old_line = 0
        file_removed = []
        file_added_counts = {k: 0 for k in KEYWORDS}
        file_removed_counts = {k: 0 for k in KEYWORDS}

        for line in diff_text.splitlines():
            hunk_match = re.match(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
            if hunk_match:
                current_old_line = int(hunk_match.group(1))
                continue

            if line.startswith("-") and not line.startswith("---"):
                content = line[1:].strip()
                for kw in KEYWORDS:
                    if kw in content:
                        file_removed_counts[kw] += 1
                        total_removed[kw] += 1
                        file_removed.append((f"{file_path}:{current_old_line}", kw, content))
                current_old_line += 1
            elif line.startswith("+") and not line.startswith("+++"):
                content = line[1:].strip()
                for kw in KEYWORDS:
                    if kw in content:
                        file_added_counts[kw] += 1
                        total_added[kw] += 1

        print(f"\nFile: {file_path}")
        print(f"  Added keywords:   {dict(file_added_counts)}")
        print(f"  Removed keywords: {dict(file_removed_counts)}")
        if file_removed:
            print("  Removed lines:")
            for loc, kw, text in file_removed:
                print(f"    - {loc} [{kw}]: {text}")
                all_removed_lines.append((loc, kw, text))
        else:
            print("  Removed lines: None")

    print("\n" + "=" * 80)
    print("AUDIT SUMMARY:")
    print("=" * 80)
    print(f"Total Added:   {total_added}")
    print(f"Total Removed: {total_removed}")
    print(f"Total Removed Lines Matching Keywords: {len(all_removed_lines)}")

    if not all_removed_lines:
        print("\nRESULT: no assertion removed or loosened")
    else:
        print(f"\nRESULT: {len(all_removed_lines)} line(s) removed; see detailed listing above.")

if __name__ == "__main__":
    main()
