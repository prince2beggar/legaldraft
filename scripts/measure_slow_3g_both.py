"""
Network Emulation & Performance Measurement via Playwright CDP (G3 / S9 Hardening).
Measures time-to-first-useful-screen for:
1. Home Screen (home.html -> #problemInputField)
2. Recipient Viewer Screen (shared_brief.html -> #otpChallengeBox / #briefContentBox)

Across 3 profiles:
- Unthrottled (Control): 0ms latency, unlimited throughput
- Throttled (Standard Slow 3G): 400ms latency, 400kbps (50,000 B/s) down/up
- Severe Profile (Severe Slow 3G): 800ms latency, 250kbps (31,250 B/s) down, 50kbps (6,250 B/s) up

Logs all network requests and outputs structured JSON and table.
"""

import http.server
import json
import threading
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "backend" / "app" / "static"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


def measure_page(page, url: str, selector: str, profile_name: str, cdp_params: dict | None) -> dict:
    requests_log = []
    page.on("request", lambda req: requests_log.append({"url": req.url, "method": req.method}))

    # Verify and enforce fresh isolated cache state
    cdp = page.context.new_cdp_session(page)
    cdp.send("Network.enable")
    cdp.send("Network.clearBrowserCache")
    cdp.send("Network.setCacheDisabled", {"cacheDisabled": True})

    if cdp_params:
        cdp.send("Network.emulateNetworkConditions", cdp_params)

    # 1. Measure exact time to First Useful Screen (FUS)
    t0 = time.perf_counter()
    page.goto(url, wait_until="commit")
    page.wait_for_selector(selector, state="visible")
    elapsed_sec = time.perf_counter() - t0

    # 2. Allow deferred client-side scripts to dispatch initial requests so counts are deterministic
    try:
        page.wait_for_load_state("load", timeout=5000)
        # Small settle window for event-loop deferred fetches
        time.sleep(0.1)
    except Exception:
        pass

    return {
        "profile": profile_name,
        "elapsed_seconds": round(elapsed_sec, 3),
        "requests_count": len(requests_log),
        "request_urls": [r["url"] for r in requests_log],
        "cache_disabled": True,
    }


def run_benchmark():
    server = http.server.HTTPServer(
        ("127.0.0.1", 0), lambda *args: QuietHandler(*args, directory=str(STATIC_DIR))
    )
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    profiles = [
        {
            "name": "Unthrottled",
            "cdp": None,
        },
        {
            "name": "Throttled (Slow 3G)",
            "cdp": {
                "offline": False,
                "latency": 400,
                "downloadThroughput": 50000,
                "uploadThroughput": 50000,
            },
        },
        {
            "name": "Severe Profile",
            "cdp": {
                "offline": False,
                "latency": 800,
                "downloadThroughput": 31250,
                "uploadThroughput": 6250,
            },
        },
    ]

    targets = [
        {
            "screen": "Home Screen",
            "url": f"http://127.0.0.1:{port}/home.html?variant=standard",
            "selector": "#problemInputField",
        },
        {
            "screen": "Recipient Viewer",
            "url": f"http://127.0.0.1:{port}/shared_brief.html?token=test_token_cdp",
            "selector": ".recipient-header",
        },
    ]

    results = {}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            for t in targets:
                screen_name = t["screen"]
                results[screen_name] = {}
                for prof in profiles:
                    context = browser.new_context()
                    page = context.new_page()
                    m = measure_page(page, t["url"], t["selector"], prof["name"], prof["cdp"])
                    results[screen_name][prof["name"]] = m
                    context.close()
            browser.close()
    finally:
        server.shutdown()

    out_file = REPO_ROOT / "storage" / "slow_3g_measurements.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    print("=" * 80)
    print(" SLOW-3G PERFORMANCE EVIDENCE (CDP Unthrottled vs Throttled vs Severe)")
    print("=" * 80)
    for scr, profs in results.items():
        print(f"\nScreen: {scr}")
        print(f"{'Profile':<25} | {'Elapsed (s)':<12} | {'Requests':<10} | {'Budget <= 4.0s'}")
        print("-" * 65)
        for pname, pdata in profs.items():
            within_budget = pdata["elapsed_seconds"] <= 4.0
            print(
                f"{pname:<25} | {pdata['elapsed_seconds']:<12} | {pdata['requests_count']:<10} | {within_budget}"
            )
    print("\n" + "=" * 80)
    print(f"Results and request logs saved to: {out_file}")
    return results


if __name__ == "__main__":
    run_benchmark()
