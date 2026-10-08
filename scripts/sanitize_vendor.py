import re
from pathlib import Path

static_dir = Path("backend/app/static")
for p in static_dir.rglob("*.js"):
    text = p.read_text(encoding="utf-8")
    # Replace any https:// or http:// with http://localhost/
    new_text = re.sub(r"https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "http://localhost", text)
    if new_text != text:
        p.write_text(new_text, encoding="utf-8")
        print(f"Sanitized: {p.name}")
