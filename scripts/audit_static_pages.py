import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

static_dir = Path("backend/app/static")

LATIN_ALLOW_LIST = {
    "AI", "PDF", "OTP", "SMS", "NID", "AIN-AI", "Ain-AI", "AinAI",
    "Gov", "BD", "DEV_MODE", "DEMO_MODE", "Demo", "Mode", "build:",
    "static:", "id:", "http://127.0.0.1", "http://localhost", "v1", "v2"
}

ISO_DATE_REGEX = re.compile(r"\b\d{4}-\d{2}-\d{2}(?:[T\s]\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?)?\b")
SNAKE_CASE_REGEX = re.compile(r"\b[a-z]{2,}_[a-z0-9_]{2,}\b")
RAW_NULL_REGEX = re.compile(r"\b(undefined|null|None|NaN)\b")
LATIN_WORD_REGEX = re.compile(r"\b[A-Za-z][A-Za-z0-9_\-./:]*\b")
DIGIT_REGEX = re.compile(r"[0-9]+")

def audit_single_file(f: Path):
    soup = BeautifulSoup(f.read_text(encoding="utf-8"), "html.parser")
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()
    for stamp in soup.find_all(id=["buildStamp", "demoModeBanner"]):
        stamp.decompose()

    texts = [t.strip() for t in soup.stripped_strings if t.strip()]
    page_violations = []

    for t in texts:
        # ISO
        for m in ISO_DATE_REGEX.findall(t):
            page_violations.append(("ISO_TIMESTAMP", m, t[:60]))
        # snake
        for m in SNAKE_CASE_REGEX.findall(t):
            page_violations.append(("SNAKE_CASE_ENUM", m, t[:60]))
        # null
        for m in RAW_NULL_REGEX.findall(t):
            page_violations.append(("RAW_NULL", m, t[:60]))
        # latin
        for word in LATIN_WORD_REGEX.findall(t):
            cw = word.strip(".,;:()[]{}\'\"")
            if not cw or cw in LATIN_ALLOW_LIST or cw.upper() in LATIN_ALLOW_LIST:
                continue
            if any(cw == item or cw.upper() == item.upper() for item in LATIN_ALLOW_LIST):
                continue
            page_violations.append(("UNAUTHORIZED_LATIN", cw, t[:60]))
        # western digit
        for m in DIGIT_REGEX.findall(t):
            if any(m in item for item in LATIN_ALLOW_LIST):
                continue
            if m in ("123456",):  # allowed OTP placeholder
                continue
            page_violations.append(("WESTERN_DIGIT", m, t[:60]))

    return page_violations

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    files = [static_dir / target] if target else sorted(static_dir.glob("*.html"))
    total_violations = 0
    for f in files:
        if not f.exists():
            continue
        pvs = audit_single_file(f)
        total_violations += len(pvs)
        if pvs:
            print(f"{f.name}: {len(pvs)} violation(s)")
            for v in pvs[:15]:
                print(f"   [{v[0]}] '{v[1]}' in \"{v[2]}\"")
        else:
            print(f"{f.name}: CLEAN (0 violations)")
    if not target:
        print("=" * 60)
        print(f"TOTAL STATIC VIOLATIONS FOUND: {total_violations}")
