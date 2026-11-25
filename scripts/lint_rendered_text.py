"""
Comprehensive Rendered Text & Bangla Digit Compliance Linter (Directives W1, X2, X3)

Audits visible rendered DOM text across ALL shipped pages (~30 pages/states):
1. ISO Timestamps and microseconds (e.g. 2026-10-09, 2026-10-09T11:00:00)
2. snake_case tokens / raw enum leaks (e.g. land_dispute, action_required)
3. "undefined", "null", "None", "NaN"
4. Unauthorized Latin words outside the explicit allow-list.
5. Western digits [0-9] on Bangla pages (<html lang="bn">) outside the allow-list:
   - OTP placeholder (123456)
   - Dev build stamp (#buildStamp)

Mandatory Directive X2:
- Never use port 8000.
- Run on an ephemeral free port with an isolated temporary SQLite DB.
- CI fails immediately if the target port is 8000.

Mandatory Directive X3:
- Exercise genuine empty and error states:
  * Freshly created user with zero cases/notifications for empty states.
  * Non-existent case id for 404 state (/cases/case-nonexistent-404).
  * Valid, expired, and revoked share tokens for recipient viewer.
- Print <h1> or first heading and short SHA of visible text content for every state.
"""

import hashlib
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import jwt
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Base Explicit Allow-Lists
LATIN_ALLOW_LIST = {
    "AI", "PDF", "OTP", "SMS", "NID", "AIN-AI", "Ain-AI", "AinAI",
    "Gov", "BD", "DEV_MODE", "DEMO_MODE", "Demo", "Mode", "build:",
    "static:", "id:", "http://127.0.0.1", "http://localhost", "v1", "v2"
}

ALLOWED_WESTERN_DIGITS = {
    "123456", "1234"
}

# Regex defect patterns
ISO_DATE_REGEX = re.compile(r"(?a)\b\d{4}-\d{2}-\d{2}(?:[T\s]\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?)?\b")
SNAKE_CASE_REGEX = re.compile(r"\b[a-z]{2,}_[a-z0-9_]{2,}\b")
RAW_NULL_REGEX = re.compile(r"\b(undefined|null|None|NaN)\b")
LATIN_WORD_REGEX = re.compile(r"\b[A-Za-z][A-Za-z0-9_\-./:]*\b")
WESTERN_DIGIT_REGEX = re.compile(r"[0-9]+")

ALL_SHIPPED_PAGES = [
    # Citizen Core Pages
    {"route": "/home", "role": "citizen", "name": "Citizen Home"},
    {"route": "/cases", "role": "citizen", "name": "Case Folders"},
    {"route": "/cases/case-demo-01", "role": "citizen", "name": "Case Detail 1 (Active Notice)"},
    {"route": "/cases/case-demo-02", "role": "citizen", "name": "Case Detail 2 (Court Matter)"},
    {"route": "/cases/case-demo-01/lawyer", "role": "citizen", "name": "Lawyer Brief Builder"},
    {"route": "/intake", "role": "citizen", "name": "Problem Intake Flow"},
    {"route": "/draft", "role": "citizen", "name": "Document Drafting Studio"},
    {"route": "/notifications", "role": "citizen", "name": "In-App Notifications"},
    {"route": "/notification-settings", "role": "citizen", "name": "Notification Preferences"},
    {"route": "/me/sharing", "role": "citizen", "name": "Sharing & Grant Management"},
    {"route": "/library", "role": "citizen", "name": "Citizen Legal Library"},
    {"route": "/static/documents_upload.html", "role": "citizen", "name": "Resumable Upload"},
    {"route": "/static/document_viewer.html", "role": "citizen", "name": "Document Extracted Viewer"},
    {"route": "/static/document_status.html", "role": "citizen", "name": "Document Pipeline Status"},
    {"route": "/static/document_intent.html", "role": "citizen", "name": "Document Intent Clarifier"},
    {"route": "/static/document_notice.html", "role": "citizen", "name": "Notice Intelligence & Relative Date"},
    {"route": "/signin", "role": "anonymous", "name": "Citizen / Admin Sign In"},

    # Recipient Viewer Pages (Valid, Expired, Revoked, Static)
    {"route": "/s/share-valid-token", "role": "anonymous", "name": "Recipient Brief (Valid Token)"},
    {"route": "/s/share-expired-token", "role": "anonymous", "name": "Recipient Brief (Expired Token State)"},
    {"route": "/s/share-revoked-token", "role": "anonymous", "name": "Recipient Brief (Revoked Token State)"},
    {"route": "/static/shared_brief.html", "role": "anonymous", "name": "Static Recipient Brief Template"},

    # Admin Console Pages
    {"route": "/admin", "role": "admin", "name": "Admin Dashboard"},
    {"route": "/admin/sources", "role": "admin", "name": "Admin Knowledge Sources Registry"},
    {"route": "/admin/templates", "role": "admin", "name": "Admin Template Registry & Dual Custody"},
    {"route": "/admin/rules", "role": "admin", "name": "Admin Rules Engine & Calculator"},
    {"route": "/admin/evals", "role": "admin", "name": "Admin Evaluation & Quality Gates"},
    {"route": "/admin/system", "role": "admin", "name": "Admin System Observability"},
    {"route": "/admin/emergency-contacts", "role": "admin", "name": "Admin Emergency Contacts"},

    # Empty & Error States (Reachable & Real)
    {"route": "/cases?filter=empty", "role": "empty_citizen", "name": "Cases Empty State (Zero Cases User)"},
    {"route": "/notifications?filter=empty", "role": "empty_citizen", "name": "Notifications Empty State (Zero Notifs User)"},
    {"route": "/cases/case-nonexistent-404", "role": "citizen", "name": "Case Detail 404 Error State"},
]


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = int(s.getsockname()[1])
    if port == 8000:
        raise RuntimeError("Ephemeral port allocated 8000 unexpectedly; must not use 8000.")
    return port


def extract_page_info(page) -> tuple[str, list[str]]:
    js_code = """
    () => {
        let heading = "";
        const h1 = document.querySelector('h1');
        if (h1 && h1.innerText && h1.innerText.trim()) {
            heading = h1.innerText.trim();
        } else {
            const anyH = document.querySelector('h2, h3, .top-bar-title, .brand-title');
            if (anyH && anyH.innerText && anyH.innerText.trim()) {
                heading = anyH.innerText.trim();
            }
        }

        const ignoreTags = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE']);
        const ignoreIds = new Set(['demoModeBanner', 'buildStamp', 'build-stamp']);
        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
            acceptNode: (node) => {
                let el = node.parentElement;
                while (el) {
                    if (ignoreTags.has(el.tagName) || ignoreIds.has(el.id)) {
                        return NodeFilter.FILTER_REJECT;
                    }
                    if (el.classList && (el.classList.contains('build-stamp') || el.classList.contains('demo-mode-banner'))) {
                        return NodeFilter.FILTER_REJECT;
                    }
                    const style = window.getComputedStyle(el);
                    if (style.display === 'none' || style.visibility === 'hidden') {
                        return NodeFilter.FILTER_REJECT;
                    }
                    el = el.parentElement;
                }
                return NodeFilter.FILTER_ACCEPT;
            }
        });
        const texts = [];
        while (walker.nextNode()) {
            const t = walker.currentNode.nodeValue.trim();
            if (t) texts.push(t);
        }
        return [heading || "—", texts];
    }
    """
    res = page.evaluate(js_code)
    return res[0], res[1]


def lint_text_items(page_url: str, texts: list[str], ephemeral_port: int) -> list[dict[str, Any]]:
    violations = []
    allowed_digits = set(ALLOWED_WESTERN_DIGITS)
    allowed_digits.add(str(ephemeral_port))

    latin_allow = set(LATIN_ALLOW_LIST)
    latin_allow.add(f"http://127.0.0.1:{ephemeral_port}")
    latin_allow.add(str(ephemeral_port))

    for t in texts:
        # 1. ISO timestamps
        for m in ISO_DATE_REGEX.findall(t):
            violations.append({"page": page_url, "type": "ISO_TIMESTAMP", "match": m, "snippet": t[:100]})

        # 2. snake_case enums
        for m in SNAKE_CASE_REGEX.findall(t):
            violations.append({"page": page_url, "type": "SNAKE_CASE_ENUM", "match": m, "snippet": t[:100]})

        # 3. raw undefined/null
        for m in RAW_NULL_REGEX.findall(t):
            violations.append({"page": page_url, "type": "RAW_NULL_OR_UNDEFINED", "match": m, "snippet": t[:100]})

        # 4. Unauthorized Latin words
        for word in LATIN_WORD_REGEX.findall(t):
            clean_w = word.strip(".,;:()[]{}'\"")
            if not clean_w:
                continue
            if clean_w in latin_allow or clean_w.upper() in latin_allow:
                continue
            if any(clean_w == item or clean_w.upper() == item.upper() for item in latin_allow):
                continue
            violations.append({"page": page_url, "type": "UNAUTHORIZED_LATIN_TEXT", "match": clean_w, "snippet": t[:100]})

        # 5. Western Digits [0-9] on Bangla pages (Directive W1)
        for m in WESTERN_DIGIT_REGEX.findall(t):
            if m in allowed_digits:
                continue
            if any(m in allowed for allowed in latin_allow):
                continue
            violations.append({"page": page_url, "type": "WESTERN_DIGIT", "match": m, "snippet": t[:100]})

    return violations


def is_server_alive(url: str) -> bool:
    import urllib.request
    try:
        with urllib.request.urlopen(f"{url}/health", timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def run_text_lint(base_url: str, ephemeral_port: int) -> tuple[bool, list[dict[str, Any]]]:
    # CI fails if target port is 8000 (Directive X2)
    if ephemeral_port == 8000 or ":8000" in base_url:
        print("[FAIL] CI Failure: Lint target port must not be 8000 (Directive X2).")
        sys.exit(1)

    print("=" * 95)
    print("RUNNING COMPREHENSIVE RENDERED TEXT & DIGIT LINT (Directives W1, X2, X3)")
    print(f"Target Server (Ephemeral Free Port): {base_url} (port {ephemeral_port})")
    print(f"Total Pages / States Audited: {len(ALL_SHIPPED_PAGES)}")
    print("=" * 95)

    now = datetime.now(timezone.utc)
    jwt_secret = os.environ.get("JWT_SECRET", "lint-secret-key-12345678901234567890123456789012")

    citizen_token = jwt.encode({
        "sub": "user-demo-citizen",
        "phone": "01711223344",
        "device_id": "dev-demo-lint",
        "role": "citizen",
        "roles": ["citizen"],
        "type": "access",
        "exp": int((now + timedelta(hours=2)).timestamp()),
    }, jwt_secret, algorithm="HS256")

    empty_citizen_token = jwt.encode({
        "sub": "user-empty-citizen",
        "phone": "01722334455",
        "device_id": "dev-empty-lint",
        "role": "citizen",
        "roles": ["citizen"],
        "type": "access",
        "exp": int((now + timedelta(hours=2)).timestamp()),
    }, jwt_secret, algorithm="HS256")

    admin_token = jwt.encode({
        "sub": "user-demo-admin",
        "phone": "01700000001",
        "device_id": "dev-admin-lint",
        "role": "admin",
        "roles": ["admin"],
        "type": "access",
        "exp": int((now + timedelta(hours=2)).timestamp()),
    }, jwt_secret, algorithm="HS256")

    all_violations = []
    page_audit_results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        for item in ALL_SHIPPED_PAGES:
            route = item["route"]
            role = item["role"]
            name = item["name"]
            url = f"{base_url}{route}"

            # Set auth credentials per state
            page.goto(f"{base_url}/signin", wait_until="commit")
            if role == "admin":
                page.evaluate(
                    "tok => { localStorage.setItem('ain_token', tok); localStorage.setItem('ain_user_role', 'admin'); }",
                    admin_token,
                )
            elif role == "citizen":
                page.evaluate(
                    "tok => { localStorage.setItem('ain_token', tok); localStorage.setItem('ain_user_role', 'citizen'); }",
                    citizen_token,
                )
            elif role == "empty_citizen":
                page.evaluate(
                    "tok => { localStorage.setItem('ain_token', tok); localStorage.setItem('ain_user_role', 'citizen'); }",
                    empty_citizen_token,
                )
            else:
                page.evaluate("() => { localStorage.removeItem('ain_token'); localStorage.removeItem('ain_user_role'); }")

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=12000)
                time.sleep(0.6)  # Let dynamic DOM settle
                heading, texts = extract_page_info(page)
                text_blob = " ".join(texts)
                short_sha = hashlib.sha256(text_blob.encode("utf-8")).hexdigest()[:8]
                v = lint_text_items(route, texts, ephemeral_port)

                page_audit_results.append({
                    "route": route,
                    "name": name,
                    "heading": heading,
                    "short_sha": short_sha,
                    "violations": len(v),
                    "text_nodes": len(texts),
                    "details": v,
                })
                if v:
                    print(f"❌ {route:<36} [{name}]: {len(v)} violation(s)")
                    for it in v[:5]:
                        print(f"     [{it['type']}] '{it['match']}' in \"{it['snippet']}\"")
                    all_violations.extend(v)
                else:
                    print(f"✅ {route:<36} [<h1>: {heading[:22]:<22}] [SHA: {short_sha}] ({len(texts)} nodes) CLEAN")
            except Exception as e:
                print(f"⚠️ {route:<36} [{name}]: Load exception ({e})")
                page_audit_results.append({
                    "route": route,
                    "name": name,
                    "heading": "LOAD_ERROR",
                    "short_sha": "ERROR",
                    "violations": 1,
                    "text_nodes": 0,
                    "details": [{"page": route, "type": "LOAD_ERROR", "match": str(e), "snippet": ""}],
                })
                all_violations.append({"page": route, "type": "LOAD_ERROR", "match": str(e), "snippet": ""})

        browser.close()

    print("\n" + "=" * 95)
    print("PAGE AUDIT SUMMARY TABLE (X3 PROOF OF DISTINCT DOM & HEADING STATES)")
    print("-" * 95)
    print(f"{'Page Route':<34} | {'<h1> or First Heading':<26} | {'Short SHA':<9} | {'Nodes':<5} | {'Status'}")
    print("-" * 95)
    for res in page_audit_results:
        st = "CLEAN" if res["violations"] == 0 else f"FAIL({res['violations']})"
        h_disp = (res["heading"][:24] + "..") if len(res["heading"]) > 26 else res["heading"]
        print(f"{res['route']:<34} | {h_disp:<26} | {res['short_sha']:<9} | {res['text_nodes']:<5} | {st}")
    print("=" * 95)

    if all_violations:
        print(f"\n[FAILED] Total {len(all_violations)} violation(s) across shipped pages.")
        return False, all_violations
    else:
        print(f"\n[PASSED] All {len(ALL_SHIPPED_PAGES)} pages & states 100% compliant with Bangla localization & digit rules.")
        return True, []


def main():
    # Directive X2: Ephemeral free port & isolated temp DB
    port = get_free_port()
    if port == 8000:
        print("[FAIL] CI Failure: Target port is 8000.")
        sys.exit(1)

    temp_dir = Path(tempfile.mkdtemp(prefix="ain_lint_db_"))
    temp_db_path = temp_dir / "isolated_temp_lint.db"

    # Isolate environment strictly away from legal_saas.db
    os.environ["DATABASE_URL"] = f"sqlite:///{temp_db_path}"
    os.environ["SQLITE_DB_PATH"] = str(temp_db_path)
    os.environ["DEMO_MODE"] = "true"
    os.environ["DEV_MODE"] = "true"
    os.environ["JWT_SECRET"] = "lint-secret-key-12345678901234567890123456789012"
    os.environ["OTP_PEPPER"] = "lint-pepper-12345678901234567890123456789012"
    os.environ["LINK_TOKEN_PEPPER"] = "lint-link-pepper-12345678901234567890123456789012"
    os.environ["DRAFT_STORAGE_KEY"] = "lint-draft-key-12345678901234567890123456789012"

    print(f"Creating isolated temporary DB at: {temp_db_path}")
    from scripts.seed_demo import build_and_seed_demo_db
    build_and_seed_demo_db(temp_db_path)

    base_url = f"http://127.0.0.1:{port}"
    print(f"Starting ephemeral uvicorn server on port {port}...")

    server_proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "services.api.app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=str(REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        ready = False
        for _ in range(40):
            time.sleep(0.4)
            if is_server_alive(base_url):
                ready = True
                print(f"Ephemeral test server is ready at {base_url}.")
                break
        if not ready:
            print(f"Failed to start ephemeral test server at {base_url}.")
            sys.exit(1)

        success, _ = run_text_lint(base_url, port)
        if not success:
            sys.exit(1)
    finally:
        print(f"Shutting down ephemeral server on port {port}...")
        if server_proc:
            server_proc.terminate()
            try:
                server_proc.wait(timeout=5)
            except Exception:
                server_proc.kill()
        try:
            if temp_db_path.exists():
                temp_db_path.unlink(missing_ok=True)
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


if __name__ == "__main__":
    main()
