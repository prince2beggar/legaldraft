import os
import io
import base64
import html
import threading
from pathlib import Path
from docx import Document as DocxDocument
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from playwright.sync_api import sync_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
FONTS_DIR = REPO_ROOT / "backend" / "app" / "static" / "fonts"

_REGULAR_FONT_BASE64: str | None = None
_BOLD_FONT_BASE64: str | None = None
_EXPORT_PDF_SEMAPHORE = threading.Semaphore(2)


def _get_noto_fonts_base64() -> tuple[str, str]:
    """Returns base64 encoded strings of bundled Noto Sans Bengali fonts."""
    global _REGULAR_FONT_BASE64, _BOLD_FONT_BASE64
    if _REGULAR_FONT_BASE64 is None:
        reg_path = FONTS_DIR / "NotoSansBengali-Regular.ttf"
        if reg_path.exists():
            _REGULAR_FONT_BASE64 = base64.b64encode(reg_path.read_bytes()).decode("ascii")
        else:
            _REGULAR_FONT_BASE64 = ""
    if _BOLD_FONT_BASE64 is None:
        bold_path = FONTS_DIR / "NotoSansBengali-Bold.ttf"
        if bold_path.exists():
            _BOLD_FONT_BASE64 = base64.b64encode(bold_path.read_bytes()).decode("ascii")
        else:
            _BOLD_FONT_BASE64 = ""
    return _REGULAR_FONT_BASE64, _BOLD_FONT_BASE64


class ExportService:
    @staticmethod
    def generate_docx(document_title: str, full_text: str, output_path: str) -> str:
        """
        Generates a professionally styled Microsoft Word (.docx) legal document.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        doc = DocxDocument()

        # Set 1-inch margins
        for section in doc.sections:
            section.top_margin = Inches(1)
            section.bottom_margin = Inches(1)
            section.left_margin = Inches(1)
            section.right_margin = Inches(1)

        lines = full_text.split('\n')
        is_title = True

        for line in lines:
            line_str = line.strip()
            if not line_str:
                doc.add_paragraph()
                continue

            if is_title and ("COMMERCIAL LEASE" in line_str.upper() or "AGREEMENT" in line_str.upper()):
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = p.add_run(line_str)
                run.bold = True
                run.font.size = Pt(16)
                run.font.name = "Times New Roman"
                is_title = False
            elif line_str.startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.", "10.", "SCHEDULE", "BETWEEN", "WHEREAS", "NOW THIS")):
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                run = p.add_run(line_str)
                run.bold = True
                run.font.size = Pt(12)
                run.font.name = "Times New Roman"
            else:
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                run = p.add_run(line_str)
                run.font.size = Pt(11)
                run.font.name = "Times New Roman"

        doc.save(output_path)
        return output_path

    @staticmethod
    def generate_pdf(
        document_title: str,
        full_text: str,
        output_path: str,
        watermark_text: str | None = None,
        conjunct_test_str: str | None = None,
    ) -> str:
        """
        Generates a print-ready legal PDF using Chromium (Playwright)
        with bundled Noto Sans Bengali font embedded, ensuring 100% correct
        Bengali conjunct glyph shaping and layout fidelity.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        reg_b64, bold_b64 = _get_noto_fonts_base64()

        font_face_css = ""
        if reg_b64:
            font_face_css += f"""
            @font-face {{
                font-family: 'Noto Sans Bengali';
                src: url('data:font/truetype;charset=utf-8;base64,{reg_b64}') format('truetype');
                font-weight: normal;
                font-style: normal;
            }}
            """
        if bold_b64:
            font_face_css += f"""
            @font-face {{
                font-family: 'Noto Sans Bengali';
                src: url('data:font/truetype;charset=utf-8;base64,{bold_b64}') format('truetype');
                font-weight: bold;
                font-style: normal;
            }}
            """

        watermark_html = ""
        if watermark_text:
            watermark_html = f"""
            <div class="watermark-overlay">{html.escape(watermark_text)}</div>
            """

        conjunct_html = ""
        if conjunct_test_str:
            conjunct_html = f"""
            <div class="conjunct-test-box" id="conjunctCheck">
                <span class="conjunct-label">সংযুক্ত বর্ণ নিরীক্ষা (Conjunct Shaping Check):</span>
                <span class="conjunct-glyphs">{html.escape(conjunct_test_str)}</span>
            </div>
            """

        paragraphs = []
        lines = full_text.split('\n')
        is_first = True

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
            clean_str = html.escape(line_str)
            if is_first and any(k in clean_str.upper() for k in ["LEASE", "AGREEMENT", "চুক্তিপত্র", "নোটিশ", "দলিল"]):
                paragraphs.append(f'<h1 class="doc-title">{clean_str}</h1>')
                is_first = False
            elif clean_str.startswith(("১.", "২.", "৩.", "৪.", "৫.", "৬.", "৭.", "৮.", "৯.", "১০.", "1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.", "10.", "SCHEDULE", "BETWEEN", "WHEREAS", "NOW THIS")):
                paragraphs.append(f'<h2 class="clause-heading">{clean_str}</h2>')
            else:
                paragraphs.append(f'<p class="legal-body">{clean_str}</p>')

        body_html = "\n".join(paragraphs)

        html_document = f"""<!DOCTYPE html>
<html lang="bn">
<head>
<meta charset="utf-8">
<style>
  {font_face_css}
  * {{
    box-sizing: border-box;
  }}
  body {{
    font-family: 'Noto Sans Bengali', 'Times New Roman', serif;
    font-size: 13px;
    line-height: 1.7;
    color: #0F172A;
    margin: 0;
    padding: 30px;
    position: relative;
  }}
  .watermark-overlay {{
    position: fixed;
    top: 40%;
    left: 5%;
    right: 5%;
    text-align: center;
    font-size: 24px;
    font-weight: bold;
    color: rgba(220, 38, 38, 0.18);
    transform: rotate(-30deg);
    pointer-events: none;
    border: 2px dashed rgba(220, 38, 38, 0.25);
    padding: 20px;
    border-radius: 8px;
    z-index: 1000;
  }}
  .doc-title {{
    text-align: center;
    font-size: 18px;
    font-weight: bold;
    color: #0F766E;
    margin-bottom: 20px;
    padding-bottom: 8px;
    border-bottom: 2px solid #0F766E;
  }}
  .clause-heading {{
    font-size: 14px;
    font-weight: bold;
    color: #1E293B;
    margin-top: 14px;
    margin-bottom: 4px;
  }}
  .legal-body {{
    text-align: justify;
    margin-bottom: 8px;
    font-size: 12.5px;
  }}
  .conjunct-test-box {{
    margin: 16px 0;
    padding: 10px 14px;
    background: #F8FAFC;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    font-size: 13px;
  }}
  .conjunct-label {{
    font-weight: bold;
    color: #0F766E;
    display: block;
    margin-bottom: 4px;
  }}
  .conjunct-glyphs {{
    font-size: 16px;
    font-weight: bold;
    letter-spacing: 2px;
    color: #0F172A;
  }}
  .footer-disclaimer {{
    margin-top: 36px;
    padding-top: 10px;
    border-top: 1px solid #E2E8F0;
    font-size: 10px;
    color: #64748B;
    display: flex;
    justify-content: space-between;
  }}
</style>
</head>
<body>
  {watermark_html}
  {conjunct_html}
  {body_html}
  <div class="footer-disclaimer">
    <span>আইন-AI বাংলাদেশ লিগ্যাল প্ল্যাটফর্ম • আদালত-পরীক্ষিত কাঠামো</span>
    <span>গোপনীয় ও আইনগত যাচাইকরণের জন্য প্রস্তুত</span>
  </div>
</body>
</html>"""

        with _EXPORT_PDF_SEMAPHORE:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(java_script_enabled=False)
                page = context.new_page()
                page.set_default_timeout(15000)
                page.route("**/*", lambda route: route.abort())
                page.set_content(html_document, wait_until="load")
                pdf_bytes = page.pdf(
                    format="A4",
                    print_background=True,
                    margin={"top": "18mm", "bottom": "18mm", "left": "16mm", "right": "16mm"},
                )
                context.close()
                browser.close()

        with open(output_path, "wb") as f:
            f.write(pdf_bytes)

        return output_path


export_service = ExportService()
