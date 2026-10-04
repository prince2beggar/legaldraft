"""
Helper script to test Playwright CDP slow-3G network emulation.
Measures time to first useful content for Home page (home.html).
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

def test_slow3g():
    server = http.server.HTTPServer(("127.0.0.1", 0), lambda *args: QuietHandler(*args, directory=str(STATIC_DIR)))
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        cdp = context.new_cdp_session(page)
        # Slow 3G specs: ~400 kbps down, 400 ms RTT
        # downloadThroughput: 400 kbps = 50,000 bytes/sec
        # latency: 400 ms
        cdp.send("Network.emulateNetworkConditions", {
            "offline": False,
            "latency": 400,
            "downloadThroughput": 50000,
            "uploadThroughput": 50000,
        })
        start_time = time.perf_counter()
        page.goto(f"http://127.0.0.1:{port}/home.html?variant=standard")
        # First useful content: problem input or next action card or welcome message
        page.wait_for_selector("#problemInputField", state="visible")
        elapsed = time.perf_counter() - start_time
        browser.close()
        server.shutdown()
        print(f"MEASURED_ELAPSED_SEC={elapsed:.3f}")
        return elapsed

if __name__ == "__main__":
    t = test_slow3g()
    print("SUCCESS" if t <= 4.0 else "SLOW")
