"""Test embedding Noto Sans Bengali via base64 data URI in Playwright PDF."""

import base64
from pathlib import Path

import pypdf
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = REPO_ROOT / "backend" / "app" / "static" / "fonts"
font_bytes = (FONTS_DIR / "NotoSansBengali-Regular.ttf").read_bytes()
font_b64 = base64.b64encode(font_bytes).decode("ascii")

html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
@font-face {{
  font-family: 'Noto Sans Bengali';
  src: url('data:font/truetype;charset=utf-8;base64,{font_b64}') format('truetype');
}}
body {{
  font-family: 'Noto Sans Bengali', sans-serif;
  font-size: 16px;
}}
</style>
</head>
<body>
<p>জ্ঞানী ব্যক্তিগণ সাক্ষ্য প্রদানপূর্বক নিঃশঙ্কচিত্তে চুক্তির শর্ত পালন করিবেন (ক্ষ, জ্ঞ, ন্দ, স্ত্র, ক্ত, ঙ্গ, শ্র)।</p>
</body>
</html>
"""

test_pdf = REPO_ROOT / "storage" / "test_embedded_font.pdf"
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.set_content(html, wait_until="networkidle")
    page.pdf(path=str(test_pdf), format="A4")
    browser.close()

reader = pypdf.PdfReader(str(test_pdf))
fonts = []
for page in reader.pages:
    if "/Resources" in page and "/Font" in page["/Resources"]:
        f_dict = page["/Resources"]["/Font"]
        for f_name, f_obj in f_dict.items():
            base_font = f_obj.get("/BaseFont", "")
            fonts.append(str(base_font))

print("Embedded fonts:", fonts)
print("Assert Noto in fonts:", any("Noto" in f for f in fonts))
