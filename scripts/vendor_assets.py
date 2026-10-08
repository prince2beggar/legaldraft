"""
Helper script to download CDN vendor assets locally to eliminate all external host dependencies.
"""

import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VENDOR_DIR = REPO_ROOT / "backend" / "app" / "static" / "vendor"
VENDOR_DIR.mkdir(parents=True, exist_ok=True)

ASSETS = {
    "tailwind.min.js": "https://cdn.tailwindcss.com",
    "lucide.min.js": "https://unpkg.com/lucide@latest",
}


def main():
    for filename, url in ASSETS.items():
        dest = VENDOR_DIR / filename
        print(f"Downloading {url} -> {dest}...")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                content = resp.read()
                dest.write_bytes(content)
                print(f"Saved {filename} ({len(content):,} bytes)")
        except Exception as e:
            print(f"Failed to download {url}: {e}")


if __name__ == "__main__":
    main()
