"""
Slow-3G Benchmark with Control (AC-M02-4).
Measures first useful content (#problemInputField) under:
1. Unthrottled network (control)
2. Throttled Slow 3G (400 kbps down, 400 ms RTT)
Both with cleared service worker cache / fresh context (first visit).
Records load time and number of network requests for each.
"""

import http.server
import threading
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "backend" / "app" / "static"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


def run_benchmark():
    server = http.server.HTTPServer(
        ("127.0.0.1", 0), lambda *args: QuietHandler(*args, directory=str(STATIC_DIR))
    )
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    url = f"http://127.0.0.1:{port}/home.html?variant=standard"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            # -------------------------------------------------------------
            # 1. Unthrottled Control (First visit, cleared cache)
            # -------------------------------------------------------------
            context_ctrl = browser.new_context()
            page_ctrl = context_ctrl.new_page()

            unthrottled_requests = []
            page_ctrl.on("request", lambda req: unthrottled_requests.append(req.url))

            cdp_ctrl = context_ctrl.new_cdp_session(page_ctrl)
            cdp_ctrl.send("Network.enable")
            cdp_ctrl.send("Network.clearBrowserCache")
            cdp_ctrl.send("Network.setCacheDisabled", {"cacheDisabled": True})

            t0 = time.perf_counter()
            page_ctrl.goto(url, wait_until="commit")
            page_ctrl.wait_for_selector("#problemInputField", state="visible")
            unthrottled_time = time.perf_counter() - t0
            context_ctrl.close()

            # -------------------------------------------------------------
            # 2. Throttled Slow 3G (First visit, cleared cache, 400 kbps, 400 ms RTT)
            # -------------------------------------------------------------
            context_slow = browser.new_context()
            page_slow = context_slow.new_page()

            throttled_requests = []
            page_slow.on("request", lambda req: throttled_requests.append(req.url))

            cdp_slow = context_slow.new_cdp_session(page_slow)
            cdp_slow.send("Network.enable")
            cdp_slow.send("Network.clearBrowserCache")
            cdp_slow.send("Network.setCacheDisabled", {"cacheDisabled": True})
            cdp_slow.send(
                "Network.emulateNetworkConditions",
                {
                    "offline": False,
                    "latency": 400,
                    "downloadThroughput": 50000,  # ~400 kbps
                    "uploadThroughput": 50000,  # ~400 kbps
                },
            )

            t1 = time.perf_counter()
            page_slow.goto(url, wait_until="commit")
            page_slow.wait_for_selector("#problemInputField", state="visible")
            throttled_time = time.perf_counter() - t1
            context_slow.close()

            browser.close()

            print("=" * 60)
            print(" SLOW-3G BENCHMARK WITH CONTROL (AC-M02-4)")
            print("=" * 60)
            print(f"Unthrottled Time:        {unthrottled_time:.3f} s")
            print(f"Unthrottled Requests:    {len(unthrottled_requests)}")
            print(f"Throttled Time (Slow3G): {throttled_time:.3f} s")
            print(f"Throttled Requests:      {len(throttled_requests)}")
            print(f"Throttled > Unthrottled: {throttled_time > unthrottled_time}")
            print(f"Budget <= 4.0s:          {throttled_time <= 4.0}")
            print("=" * 60)

            return {
                "unthrottled_time": unthrottled_time,
                "unthrottled_requests": len(unthrottled_requests),
                "throttled_time": throttled_time,
                "throttled_requests": len(throttled_requests),
            }
    finally:
        server.shutdown()


if __name__ == "__main__":
    run_benchmark()
