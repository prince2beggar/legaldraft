"""
Script to capture V8/S9 Evidence screenshots across 360, 768, 1280, 1920 px viewports
for:
1. home (/home)
2. cases (/cases)
3. case detail (/cases/case-demo-01)
4. intake (/intake)
5. draft (/draft)
6. notifications (/notifications)
7. sharing (/me/sharing)
8. library (/library)
9. documents/upload (/static/documents_upload.html)
10. admin (/admin)

Directive X1 Requirements:
- Uses ephemeral free port with isolated temporary SQLite DB (never uses 8000, never touches legal_saas.db).
- Captures real /library page distinct from /notifications.
- Saves all 40 screenshots to storage/screenshots/visible_fix/.
- Computes true SHA-256 and exact byte size in code from the saved image files.
- Writes reports/screenshot_hashes.json with: path, viewport, page route, sha256, byte size.
"""

import hashlib
import json
import os
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

OUTPUT_DIR = REPO_ROOT / "storage" / "screenshots" / "visible_fix"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR = REPO_ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
HASHES_JSON_PATH = REPORTS_DIR / "screenshot_hashes.json"

VIEWPORTS = [
    {"name": "360px", "width": 360, "height": 740},
    {"name": "768px", "width": 768, "height": 1024},
    {"name": "1280px", "width": 1280, "height": 800},
    {"name": "1920px", "width": 1920, "height": 1080},
]

PAGES = [
    {"route": "/home", "slug": "home", "role": "citizen"},
    {"route": "/cases", "slug": "cases", "role": "citizen"},
    {"route": "/cases/case-demo-01", "slug": "case_detail", "role": "citizen"},
    {"route": "/intake", "slug": "intake", "role": "citizen"},
    {"route": "/draft", "slug": "draft", "role": "citizen"},
    {"route": "/notifications", "slug": "notifications", "role": "citizen"},
    {"route": "/me/sharing", "slug": "sharing", "role": "citizen"},
    {"route": "/library", "slug": "library", "role": "citizen"},
    {"route": "/static/documents_upload.html", "slug": "documents_upload", "role": "citizen"},
    {"route": "/admin", "slug": "admin", "role": "admin"},
]


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = int(s.getsockname()[1])
    if port == 8000:
        raise RuntimeError("Ephemeral port allocated 8000 unexpectedly; must not use 8000.")
    return port


def is_server_alive(url: str) -> bool:
    import urllib.request
    try:
        with urllib.request.urlopen(f"{url}/health", timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def capture_all(base_url: str) -> list[dict[str, Any]]:
    results = []
    now = datetime.now(timezone.utc)
    jwt_secret = os.environ.get("JWT_SECRET", "capture-secret-key-12345678901234567890123456789012")

    citizen_token = jwt.encode({
        "sub": "user-demo-citizen",
        "phone": "01711223344",
        "device_id": "dev-demo-v8",
        "role": "citizen",
        "roles": ["citizen"],
        "type": "access",
        "exp": int((now + timedelta(hours=2)).timestamp()),
    }, jwt_secret, algorithm="HS256")

    admin_token = jwt.encode({
        "sub": "user-demo-admin",
        "phone": "01999887766",
        "device_id": "dev-demo-admin",
        "role": "admin",
        "roles": ["admin"],
        "type": "access",
        "exp": int((now + timedelta(hours=2)).timestamp()),
    }, jwt_secret, algorithm="HS256")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for vp in VIEWPORTS:
            context = browser.new_context(viewport={"width": vp["width"], "height": vp["height"]})
            page = context.new_page()

            for pg in PAGES:
                url = f"{base_url}{pg['route']}"
                print(f"Capturing {pg['slug']} at {vp['name']} ({url})...")

                # Setup auth in origin
                page.goto(f"{base_url}/signin", wait_until="commit")
                if pg["role"] == "admin":
                    page.evaluate(
                        "tok => { localStorage.setItem('ain_token', tok); localStorage.setItem('ain_user_role', 'admin'); }",
                        admin_token,
                    )
                else:
                    page.evaluate(
                        "tok => { localStorage.setItem('ain_token', tok); localStorage.setItem('ain_user_role', 'citizen'); }",
                        citizen_token,
                    )

                page.goto(url, wait_until="domcontentloaded", timeout=15000)
                time.sleep(0.7)  # Let dynamic rendering & layout settle

                filename = f"{pg['slug']}_{vp['width']}px.png"
                filepath = OUTPUT_DIR / filename
                page.screenshot(path=str(filepath), full_page=False)

                content_bytes = filepath.read_bytes()
                sha256 = hashlib.sha256(content_bytes).hexdigest()
                rel_path = filepath.relative_to(REPO_ROOT).as_posix()
                results.append({
                    "path": rel_path,
                    "viewport": vp["name"],
                    "page_slug": pg["slug"],
                    "route": pg["route"],
                    "sha256": sha256,
                    "bytes": len(content_bytes),
                })
            context.close()

        browser.close()

    # Write JSON output computed in code directly to reports/screenshot_hashes.json
    with open(HASHES_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] Successfully wrote {len(results)} screenshot records to {HASHES_JSON_PATH}")

    return results


def main():
    port = get_free_port()
    temp_dir = Path(tempfile.mkdtemp(prefix="ain_capture_db_"))
    temp_db_path = temp_dir / "isolated_temp_capture.db"

    # Strictly isolate away from legal_saas.db
    os.environ["DATABASE_URL"] = f"sqlite:///{temp_db_path}"
    os.environ["SQLITE_DB_PATH"] = str(temp_db_path)
    os.environ["DEMO_MODE"] = "true"
    os.environ["DEV_MODE"] = "true"
    os.environ["JWT_SECRET"] = "capture-secret-key-12345678901234567890123456789012"
    os.environ["OTP_PEPPER"] = "capture-pepper-12345678901234567890123456789012"
    os.environ["LINK_TOKEN_PEPPER"] = "capture-link-pepper-12345678901234567890123456789012"
    os.environ["DRAFT_STORAGE_KEY"] = "capture-draft-key-12345678901234567890123456789012"

    print(f"Creating isolated temporary DB for screenshot capture: {temp_db_path}")
    from scripts.seed_demo import build_and_seed_demo_db
    build_and_seed_demo_db(temp_db_path)

    base_url = f"http://127.0.0.1:{port}"
    print(f"Starting ephemeral test server on port {port}...")

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
                print(f"Ephemeral test server ready at {base_url}.")
                break
        if not ready:
            print("Failed to start ephemeral server for screenshot capture.")
            sys.exit(1)

        results = capture_all(base_url)
        print(f"Captured {len(results)} screenshots successfully.")
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
