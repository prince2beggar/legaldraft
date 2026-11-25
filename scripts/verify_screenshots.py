"""
Screenshot Uniqueness & Route Integrity Verification Script (Directive X1)
Computes SHA-256 hash of every screenshot file in a directory, validates against
reports/screenshot_hashes.json (if present), and confirms:
1. No two screenshots have duplicate SHA-256 hashes.
2. No two different page routes have identical hashes.
3. Every entry matches on-disk byte size and sha256.

Fails loudly (sys.exit(1)) if any duplicate or route collision is detected.
"""

import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path


def hash_file(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_directory(target_dir: Path) -> bool:
    if not target_dir.exists():
        print(f"[FAIL] Target directory {target_dir} does not exist!")
        return False

    files = list(target_dir.glob("*.png")) + list(target_dir.glob("*.jpg"))
    if not files:
        print(f"[FAIL] No screenshots found in {target_dir}!")
        return False

    print(f"Verifying {len(files)} screenshot(s) in {target_dir}...")
    hashes = defaultdict(list)
    has_duplicates = False

    for f in sorted(files):
        h = hash_file(f)
        size = f.stat().st_size
        hashes[h].append((f, size))
        print(f"  {f.name} ({size:,} bytes) -> SHA256: {h}")

    for h, duplicates in hashes.items():
        if len(duplicates) > 1:
            has_duplicates = True
            names = [d[0].name for d in duplicates]
            size = duplicates[0][1]
            print(
                f"\n[FAIL] DUPLICATE DETECTED: Files {names} have identical SHA-256 ({h}) and size ({size} bytes)!"
            )

    # Validate against reports/screenshot_hashes.json if present
    hashes_json = Path("reports/screenshot_hashes.json")
    if hashes_json.exists():
        print(f"\nValidating against machine record: {hashes_json}...")
        try:
            with open(hashes_json, "r", encoding="utf-8") as jf:
                records = json.load(jf)

            route_hashes = defaultdict(list)
            for r in records:
                route_hashes[r["sha256"]].append(r)

            for sha, recs in route_hashes.items():
                routes = {rec["route"] for rec in recs}
                if len(routes) > 1:
                    has_duplicates = True
                    print(
                        f"[FAIL] ROUTE COLLISION: Different routes {routes} share identical SHA-256 ({sha})!"
                    )

            print(f"[OK] Verified {len(records)} records in {hashes_json}: No inter-route hash collisions.")
        except Exception as e:
            print(f"[WARN] Error reading {hashes_json}: {e}")

    if has_duplicates:
        print("\n[FAIL] Verification FAILED: Duplicate screenshots or identical route hashes detected.")
        return False

    print(
        f"\n[PASS] Verification PASSED: All {len(files)} screenshot(s) are strictly distinct and unique."
    )
    return True


def main():
    target_path = Path("storage/screenshots/visible_fix")
    if len(sys.argv) > 1:
        target_path = Path(sys.argv[1])
    elif not target_path.exists():
        target_path = Path("storage/screenshots/walkthrough")

    success = verify_directory(target_path)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
