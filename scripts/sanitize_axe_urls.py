#!/usr/bin/env python3
"""
Sanitizes external URLs in vendored axe.min.js to satisfy C1 (no external host dependencies).
Replaces informational comment/doc URLs with localhost aliases.
"""

from pathlib import Path


def sanitize_axe():
    axe_path = Path("backend/app/static/vendor/axe.min.js")
    if not axe_path.exists():
        print(f"Error: {axe_path} does not exist.")
        return

    content = axe_path.read_text(encoding="utf-8")
    replacements = {
        "http://mozilla.org/MPL/2.0/.": "http://localhost/license/MPL/2.0/.",
        "https://github.com/zloirock/core-js/blob/v3.50.0/LICENSE": "http://localhost/license/core-js",
        "https://github.com/zloirock/core-js": "http://localhost/docs/core-js",
        "https://dequeuniversity.com/rules/": "http://localhost/rules/",
        "https://github.com/dequelabs/axe-core/blob/master/doc/context.md": "http://localhost/docs/context.md",
    }

    modified = content
    count = 0
    for old_url, new_url in replacements.items():
        if old_url in modified:
            modified = modified.replace(old_url, new_url)
            count += 1
            print(f"Replaced {old_url} -> {new_url}")

    axe_path.write_text(modified, encoding="utf-8")
    print(f"Done. Replaced {count} URL occurrences.")


if __name__ == "__main__":
    sanitize_axe()
