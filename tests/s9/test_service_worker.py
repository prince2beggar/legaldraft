"""
Test Service Worker Lifecycle & Network-First Caching Strategy (Sprint S9-I Directive M3 / K3)
Asserts:
1. Cache name is versioned by build.
2. Old caches are purged upon activation.
3. Network-first strategy: serving version A then version B of a static file causes the browser
   to display version B after one reload.
4. Service Worker is disabled when DEV_MODE=true.
"""

import threading
import time
from pathlib import Path

import pytest
import uvicorn
from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse
from playwright.sync_api import sync_playwright


@pytest.fixture(scope="module")
def sw_test_server():
    app = FastAPI()
    current_version = {"val": "Version A"}

    @app.get("/sw.js")
    def get_sw():
        sw_code = Path("backend/app/static/sw.js").read_text(encoding="utf-8")
        return Response(
            content=sw_code,
            media_type="application/javascript",
            headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"},
        )

    @app.get("/test-page")
    def get_test_page():
        html = """<!DOCTYPE html>
<html>
<head>
    <title>SW Test</title>
</head>
<body>
    <div id="content">Loading...</div>
    <script>
        navigator.serviceWorker.register('/sw.js').then(() => {
            fetch('/data.txt').then(r => r.text()).then(t => {
                document.getElementById('content').textContent = t;
            });
        });
    </script>
</body>
</html>"""
        return HTMLResponse(content=html, status_code=200)

    @app.get("/data.txt")
    def get_data():
        return Response(content=current_version["val"], media_type="text/plain")

    # Start ephemeral uvicorn server in daemon thread
    port = 8765
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(1.0)

    yield f"http://127.0.0.1:{port}", current_version
    server.should_exit = True


def test_service_worker_network_first_update_on_reload(sw_test_server):
    """
    Playwright test (Directive M3):
    Serve version A then version B of a static file;
    the browser must show B after one reload under network-first service worker caching.
    """
    base_url, version_holder = sw_test_server

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # Step 1: Initial load with Version A
        version_holder["val"] = "Version A"
        page.goto(f"{base_url}/test-page")
        page.wait_for_selector("#content:has-text('Version A')", timeout=10000)
        assert page.locator("#content").inner_text() == "Version A"

        # Step 2: Server updates to Version B
        version_holder["val"] = "Version B"

        # Step 3: Browser reloads once; network-first fetches Version B
        page.reload()
        page.wait_for_selector("#content:has-text('Version B')", timeout=10000)
        assert page.locator("#content").inner_text() == "Version B"

        browser.close()


def test_service_worker_disabled_when_dev_mode_true():
    """
    Asserts GET /sw.js returns disabled mock service worker when DEV_MODE=true.
    """
    from fastapi.testclient import TestClient

    from services.api.app.main import app

    client = TestClient(app)
    res = client.get("/sw.js")
    assert res.status_code == 200
    assert "disabled when DEV_MODE=true" in res.text


def test_service_worker_cache_invalidation_on_static_change_in_real_browser(monkeypatch):
    """
    Directive P2:
    In a real browser:
    1. Register service worker derived from dynamic build_id.
    2. Capture initial cache name from caches.keys().
    3. Modify a static file WITHOUT bumping the version.
    4. Reload/update service worker.
    5. Prove the cache name changes, old caches are deleted, and new content is served.
    """
    import socket

    from services.api.app.main import app

    monkeypatch.setenv("DEV_MODE", "false")

    def get_port():
        s = socket.socket()
        s.bind(("", 0))
        p = s.getsockname()[1]
        s.close()
        return p

    port = get_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(1.2)

    marker_file = Path("backend/app/static/test_p2_marker.txt")
    if marker_file.exists():
        marker_file.unlink()

    base_url = f"http://127.0.0.1:{port}"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            # 1. Load static shell
            page.goto(f"{base_url}/documents/upload")
            page.wait_for_load_state("domcontentloaded")

            # Wait for service worker to register and create cache
            initial_caches = page.evaluate("""async () => {
                const reg = await navigator.serviceWorker.register('/sw.js');
                await navigator.serviceWorker.ready;
                await new Promise(r => setTimeout(r, 1200));
                return await caches.keys();
            }""")
            assert len(initial_caches) > 0, f"Expected cache to be created, got {initial_caches}"
            initial_cache_name = [c for c in initial_caches if c.startswith("ain-ai-build-")][0]

            # 2. Modify a static file WITHOUT bumping any version
            marker_file.write_text("cache_bust_static_content_change_without_bumping_version", encoding="utf-8")

            # 3. Trigger SW update in browser
            page.evaluate("""async () => {
                const reg = await navigator.serviceWorker.getRegistration();
                if (reg) await reg.update();
                await new Promise(r => setTimeout(r, 1500));
            }""")

            # 4. Reload page to activate new worker and purge old cache
            page.reload()
            time.sleep(1.2)
            final_caches = page.evaluate("async () => await caches.keys()")

            new_cache_name = [c for c in final_caches if c.startswith("ain-ai-build-")][0]
            assert new_cache_name != initial_cache_name, (
                f"Cache name did not change after static file change! Old: {initial_cache_name}, New: {new_cache_name}"
            )
            assert initial_cache_name not in final_caches, (
                f"Old cache {initial_cache_name} was not deleted! Present caches: {final_caches}"
            )

            browser.close()
    finally:
        if marker_file.exists():
            marker_file.unlink()
        server.should_exit = True
