"""
Inspects and outputs the 3 required S6 screenshots with full paths and exact byte sizes.
Usage: python scripts/check_screenshots.py
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_DIR = Path(
    "C:/Users/Lenovo/.gemini/antigravity/brain/f5b387fc-eb28-4e1b-9940-b3291f442234"
)
STORAGE_DIR = REPO_ROOT / "storage" / "screenshots"

REQUIRED_FILES = [
    ("s6_home_with_next_action (mobile 360)", "s6_home_with_next_action_mobile_360.png"),
    ("s6_case_detail_overview (desktop 1280)", "s6_case_detail_overview_desktop_1280.png"),
    ("s6_notifications_list (mobile 360)", "s6_notifications_list_mobile_360.png"),
]


def check_files():
    print("| Screen / Viewport | Full Artifact Path | File Size | Status |")
    print("| :--- | :--- | :---: | :---: |")
    all_exist = True
    for label, filename in REQUIRED_FILES:
        path = ARTIFACT_DIR / filename
        if not path.exists():
            # Check storage dir
            alt_path = STORAGE_DIR / filename
            if alt_path.exists():
                size = alt_path.stat().st_size
                print(
                    f"| {label} | `{alt_path.as_posix()}` | {size:,} bytes | **EXISTS (storage)** |"
                )
            else:
                print(f"| {label} | `{path.as_posix()}` | 0 bytes | **MISSING** |")
                all_exist = False
        else:
            size = path.stat().st_size
            print(f"| {label} | `{path.as_posix()}` | {size:,} bytes | **EXISTS** |")
    return all_exist


if __name__ == "__main__":
    ok = check_files()
    if not ok:
        exit(1)
