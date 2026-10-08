import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = REPO_ROOT / "backend" / "app" / "static"


def find_api_calls():
    api_pattern = re.compile(
        r"""['"`](/api/[^'"`\s\?]+|/auth/[^'"`\s\?]+|/documents/[^'"`\s\?]+|/cases/[^'"`\s\?]+|/s/[^'"`\s\?]+|/drafts?/[^'"`\s\?]+|/templates/[^'"`\s\?]+|/me/[^'"`\s\?]+|/consents/[^'"`\s\?]+)['"`]"""
    )
    fetch_pattern = re.compile(r"""fetch\s*\(\s*['"`]([^'"`]+)['"`]""")

    calls_by_file = {}
    for f in sorted(STATIC_DIR.glob("**/*.html")):
        text = f.read_text(encoding="utf-8")
        matches = set(api_pattern.findall(text) + fetch_pattern.findall(text))
        cleaned = set()
        for m in matches:
            # strip query params or trailing template literals
            endpoint = m.split("?")[0].split("${")[0]
            if endpoint.startswith("/"):
                cleaned.add(endpoint)
        if cleaned:
            calls_by_file[f.name] = sorted(cleaned)

    for fname, endpoints in calls_by_file.items():
        print(f"\n--- {fname} ---")
        for ep in endpoints:
            print(f"  {ep}")


if __name__ == "__main__":
    find_api_calls()
