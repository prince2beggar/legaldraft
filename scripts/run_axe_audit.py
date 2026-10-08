"""
Automated WCAG 2.2 AA Accessibility Audit using vendored axe-core (4.14.0).
Evaluates key citizen screens at mobile (360x640) and desktop (1280x800).
Vendored locally at backend/app/static/vendor/axe.min.js (NO CDN).
"""

import http.server
import json
import threading
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "backend" / "app" / "static"
AXE_JS_PATH = STATIC_DIR / "vendor" / "axe.min.js"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


def run_axe_on_page(page, axe_script: str) -> dict[str, Any]:
    # Inject local axe-core library
    page.evaluate(axe_script)
    # Run accessibility audit with WCAG 2.2 AA tags
    results = page.evaluate("""async () => {
        return await axe.run(document, {
            runOnly: {
                type: 'tag',
                values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa']
            }
        });
    }""")
    return results


def run_full_axe_audit() -> dict[str, Any]:
    if not AXE_JS_PATH.exists():
        raise FileNotFoundError(f"axe-core library missing at {AXE_JS_PATH}")

    axe_script = AXE_JS_PATH.read_text(encoding="utf-8")

    server = http.server.HTTPServer(
        ("127.0.0.1", 0), lambda *args: QuietHandler(*args, directory=str(STATIC_DIR))
    )
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    screens = [
        {"name": "Home", "file": "home.html"},
        {"name": "Intake", "file": "intake.html"},
        {"name": "Notice Result", "file": "document_notice.html"},
        {"name": "Case", "file": "case_detail.html"},
        {"name": "Draft", "file": "draft.html"},
        {"name": "Sharing", "file": "sharing.html"},
        {"name": "ConsentSheet", "file": "case_brief.html"},
        {"name": "Recipient Viewer", "file": "shared_brief.html"},
    ]

    viewports = [
        {"label": "mobile_360", "width": 360, "height": 640},
        {"label": "desktop_1280", "width": 1280, "height": 800},
    ]

    audit_summary = {
        "engine": "axe-core v4.14.0 (locally vendored)",
        "screens_tested": len(screens),
        "viewports_tested": len(viewports),
        "results": {},
        "total_critical": 0,
        "total_serious": 0,
        "total_moderate": 0,
        "total_minor": 0,
    }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            for s in screens:
                screen_key = s["name"]
                audit_summary["results"][screen_key] = {}

                for vp in viewports:
                    vp_label = vp["label"]
                    context = browser.new_context(
                        viewport={"width": vp["width"], "height": vp["height"]}
                    )
                    page = context.new_page()

                    url = f"http://127.0.0.1:{port}/{s['file']}"
                    page.goto(url, wait_until="load")
                    page.wait_for_timeout(300)

                    axe_results = run_axe_on_page(page, axe_script)
                    violations = axe_results.get("violations", [])

                    counts = {"critical": 0, "serious": 0, "moderate": 0, "minor": 0}
                    violation_details = []

                    for v in violations:
                        impact = v.get("impact", "minor")
                        counts[impact] = counts.get(impact, 0) + len(v.get("nodes", []))
                        violation_details.append(
                            {
                                "id": v.get("id"),
                                "impact": impact,
                                "description": v.get("description"),
                                "nodes_count": len(v.get("nodes", [])),
                            }
                        )

                    audit_summary["total_critical"] += counts["critical"]
                    audit_summary["total_serious"] += counts["serious"]
                    audit_summary["total_moderate"] += counts["moderate"]
                    audit_summary["total_minor"] += counts["minor"]

                    audit_summary["results"][screen_key][vp_label] = {
                        "violations_count": len(violations),
                        "severity_counts": counts,
                        "passes_count": len(axe_results.get("passes", [])),
                        "incomplete_count": len(axe_results.get("incomplete", [])),
                        "violations": violation_details,
                    }
                    context.close()
            browser.close()
    finally:
        server.shutdown()

    return audit_summary


if __name__ == "__main__":
    report = run_full_axe_audit()
    print(json.dumps(report, indent=2, ensure_ascii=False))
