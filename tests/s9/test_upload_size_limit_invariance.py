"""
Directive Z6 (J4 & ZW1): Upload Size Limit (20 MB) Invariance & Enforcement Test Suite.

Authoritative Specification: SRS §5.3 / Route Table line 669 (20 MB limit).
Requirements:
1. Upload page (/documents/upload) shows the 20 MB limit, injected dynamically
   from single server config (settings.MAX_UPLOAD_SIZE_MB), not hard-coded in JS.
2. Checks the size client-side with a Bangla error badge:
   'ফাইলের আকার সীমা (২০ মেগাবাইট) অতিক্রম করেছে। অনুগ্রহ করে ছোট ফাইল নির্বাচন করুন।'
3. The server accepts <= 20 MB (20 MB boundary passes size check) and rejects 20 MB + 1 byte with HTTP 413.
4. Fails if any file, doc, UI string or ADR states a conflicting upload limit.
"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright

from backend.app.core.config import settings
from packages.trust_kernel.auth import create_access_token
from services.api.app.main import app

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_z6_upload_page_injects_limit_from_single_server_config(live_server):
    """Verifies upload page injects limit from backend settings and renders Bangla limit text."""
    # 1. Server config invariants (ZW1: SRS-authoritative 20 MB)
    assert settings.MAX_UPLOAD_SIZE_MB == 20, (
        f"Server config MAX_UPLOAD_SIZE_MB is {settings.MAX_UPLOAD_SIZE_MB}, expected 20"
    )
    assert settings.MAX_UPLOAD_SIZE_BYTES == 20 * 1024 * 1024, (
        f"Server config MAX_UPLOAD_SIZE_BYTES is {settings.MAX_UPLOAD_SIZE_BYTES}, expected 20971520"
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Check raw page content contains server-injected script
        page.goto(f"{live_server}/documents/upload", wait_until="domcontentloaded")
        raw_html = page.content()
        assert f"window.MAX_UPLOAD_SIZE_MB = {settings.MAX_UPLOAD_SIZE_MB}" in raw_html
        assert f"window.MAX_UPLOAD_SIZE_BYTES = {settings.MAX_UPLOAD_SIZE_BYTES}" in raw_html

        # Check rendered text in DOM
        limit_text_el = page.locator("#maxUploadLimitText")
        assert limit_text_el.count() > 0, "#maxUploadLimitText not found in upload page"
        rendered_limit = limit_text_el.inner_text().strip()
        assert "২০ মেগাবাইট" in rendered_limit or "20" in rendered_limit, (
            f"Expected '২০ মেগাবাইট' rendered in limit element, got '{rendered_limit}'"
        )
        browser.close()


def test_z6_client_side_size_check_bangla_error(live_server):
    """Verifies client-side check triggers Bangla error badge on exceeding limit."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(f"{live_server}/documents/upload", wait_until="domcontentloaded")

        # Simulate selecting a file of 20 MB + 1 byte
        error_msg = page.evaluate(
            """async () => {
                const oversize = (20 * 1024 * 1024) + 1;
                const fakeFile = {
                    name: 'oversized_document.pdf',
                    size: oversize,
                    type: 'application/pdf',
                    arrayBuffer: async () => new ArrayBuffer(8)
                };
                // Call handleFileSelect
                await handleFileSelect([fakeFile]);
                const badge = document.getElementById('uploadErrorBadge');
                return badge ? badge.innerText : '';
            }"""
        )
        browser.close()

    expected_bangla_substr = "ফাইলের আকার সীমা (২০ মেগাবাইট) অতিক্রম করেছে"
    assert expected_bangla_substr in error_msg, (
        f"Client-side check did not display expected Bangla error! Got: '{error_msg}'"
    )


def test_z6_server_rejects_20mb_plus_1_byte_and_accepts_boundary(monkeypatch):
    """
    Asserts backend API:
    1. Rejects 20 MB + 1 byte with HTTP 413 Payload Too Large.
    2. Accepts exactly 20 MB boundary without triggering HTTP 413.
    """
    client = TestClient(app)
    token = create_access_token(
        data={"sub": "01711223344", "phone": "01711223344", "role": "citizen"}
    )
    headers = {"Authorization": f"Bearer {token}"}

    limit_len = 20 * 1024 * 1024
    oversized_len = limit_len + 1

    # A. 20 MB + 1 byte: Rejected with HTTP 413
    oversized_data = b"0" * oversized_len
    res_over = client.post(
        "/api/v1/documents/upload",
        files={"file": ("test_oversized.pdf", oversized_data, "application/pdf")},
        headers=headers,
    )

    assert res_over.status_code == 413, (
        f"Server did not return HTTP 413 for 20MB + 1 byte! Got {res_over.status_code}: {res_over.text}"
    )
    detail = res_over.json().get("detail", "")
    assert "20MB" in detail or "limit" in detail.lower(), (
        f"Unexpected 413 error detail: {detail}"
    )

    # B. Exactly 20 MB boundary: Accepted (passes size check, returns 200 with mocked service)
    exact_data = b"%PDF-1.4\n" + b"0" * (limit_len - 9)
    monkeypatch.setattr(
        "services.api.app.routers.documents.document_service.upload_document",
        lambda **kwargs: {"id": "mock_20mb_doc", "status": "uploaded"},
    )
    res_exact = client.post(
        "/api/v1/documents/upload",
        files={"file": ("test_exact_20mb.pdf", exact_data, "application/pdf")},
        headers=headers,
    )
    assert res_exact.status_code != 413, (
        f"Server returned 413 for exact 20 MB upload! Got: {res_exact.status_code}"
    )
    assert res_exact.status_code in (200, 201), (
        f"Expected 200 or 201 for exact 20 MB upload, got {res_exact.status_code}: {res_exact.text}"
    )


def test_z6_no_conflicting_upload_limit_in_repo():
    """
    Scans code, docs, UI templates and ADRs:
    Fails if any file asserts or states an upload limit different from 20 MB.
    """
    conflicts = []
    # Match patterns like: "25 MB upload", "50 MB", "10 MB limit", etc. (excluding authoritative 20 MB)
    pattern = re.compile(
        r"(\b(?:10|15|25|30|50|100)\s*(?:MB|মেগাবাইট)\b.*?upload|upload.*?\b(?:10|15|25|30|50|100)\s*(?:MB|মেগাবাইট)\b)",
        re.IGNORECASE,
    )

    for ext in ["*.py", "*.html", "*.js", "*.md", "*.json"]:
        for file_path in REPO_ROOT.rglob(ext):
            parts = file_path.parts
            if any(
                skip in parts
                for skip in [
                    ".git",
                    ".pytest_cache",
                    "node_modules",
                    "reports",
                    ".next",
                    "_next",
                    "out",
                    ".cache",
                    "dist",
                    "build",
                ]
            ):
                continue
            # Skip this test file itself
            if file_path.name == "test_upload_size_limit_invariance.py":
                continue

            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
                for line_idx, line in enumerate(text.splitlines(), 1):
                    # Skip historical ADR description resolving legacy claims
                    if "ADR-034" in line and "Resolves conflicting legacy limit claims" in line:
                        continue
                    m = pattern.search(line)
                    if m:
                        conflicts.append(f"{file_path.relative_to(REPO_ROOT)}:{line_idx}: {line.strip()}")
            except Exception:
                pass

    assert not conflicts, (
        "Found conflicting upload size limits in repository (must be unified 20 MB):\n"
        + "\n".join(conflicts)
    )
