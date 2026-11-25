"""
Script to ensure build stamp 'id="buildStamp"' and '/static/sw-register.js' exist in footer of all static pages
(Directives P2 & M2)
"""

from pathlib import Path

STATIC_DIR = Path("backend/app/static")
BUILD_STAMP_HTML = '<div class="build-stamp" id="buildStamp" style="font-size:11px; color:#94a3b8; text-align:center; padding:12px 0;">build: truthful-id</div>'
SW_SCRIPT_HTML = '<script src="/static/sw-register.js"></script>'


def stamp_pages():
    updated = []
    skipped = []
    for html_file in STATIC_DIR.glob("*.html"):
        content = html_file.read_text(encoding="utf-8")
        dirty = False
        if 'id="buildStamp"' not in content and "</body>" in content:
            content = content.replace("</body>", f"  {BUILD_STAMP_HTML}\n</body>")
            dirty = True
        if "sw-register.js" not in content and "</body>" in content:
            content = content.replace("</body>", f"  {SW_SCRIPT_HTML}\n</body>")
            dirty = True

        if dirty:
            html_file.write_text(content, encoding="utf-8")
            updated.append(html_file.name)
        else:
            skipped.append(html_file.name)

    print(f"Stamped {len(updated)} files:")
    for f in updated:
        print(f"  + {f}")
    print(f"Already stamped {len(skipped)} files:")
    for f in skipped:
        print(f"  - {f}")


if __name__ == "__main__":
    stamp_pages()
