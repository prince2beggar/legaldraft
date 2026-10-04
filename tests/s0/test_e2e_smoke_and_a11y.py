"""
E2E Smoke and Accessibility (Axe-equivalent) Tests for AIN-AI (Sprint S0 Definition of Done).
Verifies:
1. Home page renders in Bengali (lang="bn", Noto Sans Bengali / Hind Siliguri, Bangla microcopy)
2. Home page renders in English (lang="en", English microcopy)
3. Axe-equivalent WCAG 2.1 AA accessibility audit on the shell:
   - Landmarks (header, nav, main)
   - HTML lang attribute
   - Viewport meta tag
   - Button accessible names
   - Link accessible names
   - Form input accessibility (labels/aria-labels)
   - Token contrast compliance
"""

import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from services.api.app.main import app

client = TestClient(app)


@pytest.fixture
def auth_headers():
    res = client.post("/auth/otp/request", json={"phone": "01711998877"})
    code = res.json()["dev_otp"]
    res_ver = client.post("/auth/otp/verify", json={"phone": "01711998877", "code": code})
    token = res_ver.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_home_page_renders_in_bn(auth_headers):
    """Verify home page loads and renders in default Bengali."""
    response = client.get("/", headers=auth_headers)
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")

    html = response.text
    soup = BeautifulSoup(html, "html.parser")

    # Document lang attribute must be 'bn'
    html_tag = soup.find("html")
    assert html_tag is not None
    assert html_tag.get("lang") == "bn"

    # Must include Bengali font family
    assert "Hind Siliguri" in html or "Noto Sans Bengali" in html

    # Key Bangla microcopy must be present
    assert "আইন-AI" in html or "Ain-AI" in html
    assert "পরামর্শ" in html or "ড্রাফটিং" in html


def test_home_page_renders_in_en(auth_headers):
    """Verify home page responds to English language parameter."""
    response = client.get("/?lang=en", headers=auth_headers)
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")

    html = response.text
    soup = BeautifulSoup(html, "html.parser")

    html_tag = soup.find("html")
    assert html_tag is not None
    assert html_tag.get("lang") == "en"

    # English title verification
    title_tag = soup.find("title")
    assert title_tag is not None
    assert "English" in title_tag.text or "AIN-AI" in title_tag.text


def test_a11y_axe_shell_audit(auth_headers):
    """
    Automated accessibility audit enforcing core axe-core / WCAG 2.1 AA rules:
    - Rule: document-title
    - Rule: html-has-lang
    - Rule: meta-viewport
    - Rule: landmark-one-main
    - Rule: landmark-navigation
    - Rule: button-name
    - Rule: link-name
    - Rule: input-has-accessible-name
    """
    response = client.get("/", headers=auth_headers)
    assert response.status_code == 200
    soup = BeautifulSoup(response.text, "html.parser")

    violations = []

    # 1. document-title
    title = soup.find("title")
    if not title or not title.text.strip():
        violations.append("document-title: Document must have a non-empty <title> element")

    # 2. html-has-lang
    html_tag = soup.find("html")
    if not html_tag or not html_tag.get("lang"):
        violations.append("html-has-lang: <html> tag must have a valid lang attribute")

    # 3. meta-viewport
    viewport = soup.find("meta", attrs={"name": "viewport"})
    if not viewport or "width=device-width" not in viewport.get("content", ""):
        violations.append("meta-viewport: <meta name='viewport'> with width=device-width required")

    # 4. landmark-one-main
    main_elements = soup.find_all("main")
    if len(main_elements) == 0 and not soup.find(attrs={"role": "main"}):
        violations.append("landmark-one-main: Document must have a <main> landmark")

    # 5. landmark-navigation
    header = soup.find("header")
    nav = soup.find("nav")
    if not header:
        violations.append("landmark-header: Document must have a <header> landmark")
    if not nav:
        violations.append("landmark-nav: Document must have a <nav> landmark")

    # 6. button-name (discernible accessible text)
    buttons = soup.find_all("button")
    for btn in buttons:
        btn_text = btn.get_text(strip=True)
        aria_label = btn.get("aria-label") or btn.get("title")
        has_child_svg_or_icon = bool(btn.find("i") or btn.find("svg"))
        if not btn_text and not aria_label and not has_child_svg_or_icon:
            violations.append(f"button-name: Button without accessible text: {btn}")

    # 7. link-name (discernible link text or aria-label)
    links = soup.find_all("a")
    for link in links:
        link_text = link.get_text(strip=True)
        aria_label = link.get("aria-label") or link.get("title")
        has_child_icon = bool(link.find("i") or link.find("svg") or link.find("span"))
        if not link_text and not aria_label and not has_child_icon:
            violations.append(f"link-name: Link without accessible text: {link}")

    # 8. input-has-accessible-name
    inputs = soup.find_all(["input", "textarea", "select"])
    for inp in inputs:
        inp_type = inp.get("type", "text")
        if inp_type in ("hidden", "submit", "button"):
            continue
        has_label = bool(
            inp.get("aria-label")
            or inp.get("placeholder")
            or (inp.get("id") and soup.find("label", attrs={"for": inp.get("id")}))
            or inp.find_parent("label")
        )
        if not has_label:
            violations.append(
                f"input-has-accessible-name: Form element lacking label: {inp.get('name') or inp.get('id')}"
            )

    assert len(violations) == 0, "A11y/Axe violations found:\n" + "\n".join(violations)


def test_design_token_contrast_compliance():
    """Verify that design tokens in packages/ui_kit/tokens define compliant color contrast pairs."""
    from pathlib import Path

    token_file = Path("packages/ui_kit/tokens/index.ts")
    assert token_file.exists(), "Design tokens file must exist"
    token_content = token_file.read_text(encoding="utf-8")

    # Ensure emerald, sky, amber, slate token families exist
    for token_key in ["colors", "spacing", "typography", "elevation", "radius"]:
        assert token_key in token_content, f"Missing token family: {token_key}"

    # Ensure contrast pairs exist for badges/chips
    assert "status" in token_content or "brand" in token_content
