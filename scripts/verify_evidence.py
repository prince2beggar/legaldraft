"""
Verifies S8 evidence files in storage/screenshots/ and storage/ and prints sizes.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = REPO_ROOT / "storage" / "screenshots"
STORAGE_DIR = REPO_ROOT / "storage"


def verify_evidence():
    print("=" * 60)
    print(" SPRINT S8 EVIDENCE VERIFICATION")
    print("=" * 60)

    print("\n[Screenshots in storage/screenshots/]:")
    screenshots = sorted(SCREENSHOTS_DIR.glob("s8_*.png"))
    for s in screenshots:
        size_kb = s.stat().st_size / 1024
        print(f" - {s.name:<45} {size_kb:>8.1f} KB")

    print(f"\nTotal S8 screenshots: {len(screenshots)}")

    print("\n[Sample Exports in storage/]:")
    sample_pdf = STORAGE_DIR / "sample_draft_export_DT01.pdf"
    if sample_pdf.exists():
        size_kb = sample_pdf.stat().st_size / 1024
        print(f" - {sample_pdf.name:<45} {size_kb:>8.1f} KB [VERIFIED]")
    else:
        print(" - sample_draft_export_DT01.pdf NOT FOUND!")


if __name__ == "__main__":
    verify_evidence()
