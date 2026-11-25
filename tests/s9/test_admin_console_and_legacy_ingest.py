"""
Directive Z1 (Y1): Admin Console Landing and Legacy Ingest Protection Test Suite.

Asserts:
1. /admin renders the SRS M10 Admin Console landing with links to:
   - sources (/admin/sources)
   - templates (/admin/templates)
   - rules (/admin/rules)
   - evals (/admin/evals)
   - emergency contacts (/admin/emergency-contacts)
   - system (/admin/system)
2. Legacy book-ingestion page (/admin/legacy-ingest):
   - returns 404 Not Found when DEV_MODE=false
   - is reachable (returns 200 OK) only when DEV_MODE=true
3. No shipped nav or page links to legacy book-ingestion page or legacy ingest endpoints
   (asserted via crawling all page links across all shipped pages in demo mode).
"""

from pathlib import Path

import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from packages.trust_kernel.auth import create_access_token
from services.api.app.main import app


@pytest.fixture
def admin_headers():
    token = create_access_token(
        data={"sub": "admin_root", "phone": "01799999999", "role": "admin"}
    )
    return {
        "Authorization": f"Bearer {token}",
        "x-user-role": "admin",
    }


def test_z1_admin_console_renders_all_six_m10_sections(admin_headers):
    """Asserts /admin renders M10 Console with links to sources, templates, rules, evals, emergency contacts, system."""
    client = TestClient(app)
    res = client.get("/admin", headers=admin_headers)
    assert res.status_code == 200, f"Failed to load /admin: {res.status_code}"

    html = res.text
    soup = BeautifulSoup(html, "html.parser")

    # Check landing header / title
    h1 = soup.find("h1")
    assert h1 is not None, "Missing h1 in /admin"
    assert "অ্যাডমিন কনসোল" in h1.get_text()

    # 6 Required SRS M10 Links
    required_links = {
        "/admin/sources": "নলেজ সেন্টার / লিগ্যাল সোর্স",
        "/admin/templates": "দলিল টেমপ্লেট রেজিস্ট্রি",
        "/admin/rules": "রুলস ইঞ্জিন ও ভ্যালিডেশন",
        "/admin/evals": "কোয়ালিটি গেট ও ইভ্যালস",
        "/admin/emergency-contacts": "জরুরি হেল্পলাইন",
        "/admin/system": "সিস্টেম অবস্থা ও নির্ভরযোগ্যতা",
    }

    found_links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].split("?")[0].rstrip("/")
        if href in required_links:
            found_links.add(href)

    for req_link, label in required_links.items():
        assert req_link in found_links, (
            f"Admin console missing required M10 link to {req_link} ({label})"
        )


def test_z1_legacy_ingest_page_returns_404_when_dev_mode_false(monkeypatch, admin_headers):
    """Asserts /admin/legacy-ingest returns 404 when DEV_MODE=false."""
    monkeypatch.setenv("DEV_MODE", "false")
    client = TestClient(app)
    res = client.get("/admin/legacy-ingest", headers=admin_headers)
    assert res.status_code == 404, (
        f"Expected 404 for /admin/legacy-ingest with DEV_MODE=false, got {res.status_code}"
    )


def test_z1_legacy_ingest_page_reachable_when_dev_mode_true(monkeypatch, admin_headers):
    """Asserts /admin/legacy-ingest returns 200 when DEV_MODE=true."""
    monkeypatch.setenv("DEV_MODE", "true")
    client = TestClient(app)
    res = client.get("/admin/legacy-ingest", headers=admin_headers)
    assert res.status_code == 200, (
        f"Expected 200 for /admin/legacy-ingest with DEV_MODE=true, got {res.status_code}"
    )
    assert "বই ইনজেকশন" in res.text


def test_z1_no_shipped_nav_or_page_links_to_legacy_ingest(monkeypatch, admin_headers):
    """
    Crawls every nav and link across all shipped HTML pages and templates in demo/production mode.
    Asserts zero shipped links point to /admin/legacy-ingest or legacy book ingestion routes.
    """
    repo_root = Path(__file__).resolve().parents[2]
    static_dir = repo_root / "backend" / "app" / "static"

    html_files = list(static_dir.glob("*.html"))
    assert len(html_files) >= 20, "Static templates missing"

    prohibited_destinations = [
        "/admin/legacy-ingest",
        "/api/v1/admin/ingest-nasrin-book",
    ]

    offending_links = []

    for f in html_files:
        if f.name == "legacy_ingest.html":
            # The legacy ingest page itself is the DEV-only target, not a shipped public page
            continue

        content = f.read_text(encoding="utf-8")
        soup = BeautifulSoup(content, "html.parser")

        # Check all <a href> and <button onclick> or form actions
        for tag in soup.find_all(["a", "form", "button"]):
            href = tag.get("href") or tag.get("action") or tag.get("onclick") or ""
            for prohibited in prohibited_destinations:
                if prohibited in href:
                    offending_links.append((f.name, tag.name, href))

    assert len(offending_links) == 0, (
        f"Found forbidden links pointing to legacy ingestion in shipped templates: {offending_links}"
    )
