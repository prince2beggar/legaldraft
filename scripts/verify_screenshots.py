"""
Screenshot Uniqueness Verification Script (Sprint S9-I Addendum Directive H1 / M4)
Computes SHA-256 hash of every screenshot file in a directory and confirms
no two screenshots are byte-identical.
Fails loudly (sys.exit(1)) if any duplicates are detected.
"""

import hashlib
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
        print(f"Directory {target_dir} does not exist.")
        return True

    files = list(target_dir.glob("*.png")) + list(target_dir.glob("*.jpg"))
    if not files:
        print(f"No screenshots found in {target_dir}.")
        return True

    print(f"Verifying {len(files)} screenshot(s) in {target_dir}...")
    hashes = defaultdict(list)
    has_duplicates = False

    for f in sorted(files):
        h = hash_file(f)
        size = f.stat().st_size
        hashes[h].append((f, size))
        print(f"  {f.name} ({size:,} bytes) -> {h[:16]}...")

    for h, duplicates in hashes.items():
        if len(duplicates) > 1:
            has_duplicates = True
            names = [d[0].name for d in duplicates]
            size = duplicates[0][1]
            print(f"\n[FAIL] DUPLICATE DETECTED: Files {names} have identical SHA-256 ({h}) and size ({size} bytes)!")

    if has_duplicates:
        print("\n[FAIL] Verification FAILED: Duplicate screenshots detected.")
        return False

    print(f"\n[PASS] Verification PASSED: All {len(files)} screenshot(s) are strictly distinct and unique.")
    return True


def main():
    target_path = Path("storage/screenshots/walkthrough")
    if len(sys.argv) > 1:
        target_path = Path(sys.argv[1])

    success = verify_directory(target_path)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
