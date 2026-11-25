#!/usr/bin/env python3
"""
Directive J1: Generates a test PDF with Bengali conjunct glyphs (ক্ষ জ্ঞ ন্দ স্ত্র ক্ত ঙ্গ শ্র),
watermark, and footer disclaimer using Chromium (Playwright).
Rasterizes page 1 via pypdfium2 and saves the cropped conjunct check to
reports/conjunct_check_2026-10-09.png for human verification.
"""

import sys
from pathlib import Path

import pypdfium2 as pdfium

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "backend"))

from backend.app.services.export_service import export_service

REPORTS_DIR = REPO_ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

PDF_OUTPUT_PATH = REPORTS_DIR / "conjunct_test_2026-10-09.pdf"
IMAGE_OUTPUT_PATH = REPORTS_DIR / "conjunct_check_2026-10-09.png"

CONJUNCT_TEST_STR = "ক্ষ জ্ঞ ন্দ স্ত্র ক্ত ঙ্গ শ্র"

DOCUMENT_TEXT = f"""বাণিজ্যিক দোকান ও অফিস ভাড়ার চুক্তিপত্র
১. পক্ষগণের পরিচিতি ও বিবরণ
প্রথম পক্ষ (মালিক): এ বি এম রফিকুল ইসলাম, পিতা: মৃত আবদুল হামিদ
দ্বিতীয় পক্ষ (ভাড়াটিয়া): মো: তানভীর আহমেদ, পিতা: মো: নুরুল হুদা

২. ভাড়ার শর্তাবলী ও মেয়াদ
দোকান ঘরের মাসিক ভাড়া ৩০,০০০ (ত্রিশ হাজার) টাকা। চুক্তিপত্রের মেয়াদ ৩ (তিন) বৎসর।

৩. বিশেষ বিধান ও সংযুক্ত বর্ণ নিরীক্ষা (Bengali Conjunct Test)
অত্র চুক্তিপত্রে বাংলা লিপির জটিল যুক্তবর্ণসমূহ নির্ভুলভাবে মুদ্রিত হইয়াছে: {CONJUNCT_TEST_STR}।
উক্ত যুক্তাক্ষরসমূহের সঠিক রূপায়ন (Shaping) মালিক ও ভাড়াটিয়ার অধিকার রক্ষার্থে সুস্পষ্ট রাখা হইল।

৪. সমাপ্তি ও দায়বদ্ধতা
উভয় পক্ষ স্বেচ্ছায় ও সজ্ঞানে অত্র দলিলে স্বাক্ষর করিলেন।
"""


def generate_conjunct_proof():
    print(f"Generating PDF with Chromium at: {PDF_OUTPUT_PATH}")
    export_service.generate_pdf(
        document_title="বাণিজ্যিক দোকান ভাড়ার চুক্তিপত্র",
        full_text=DOCUMENT_TEXT,
        output_path=str(PDF_OUTPUT_PATH),
        watermark_text="গোপনীয় নমুনা • মেয়াদ: ৩১ ডিসেম্বর ২০২৬",
        conjunct_test_str=CONJUNCT_TEST_STR,
    )

    assert PDF_OUTPUT_PATH.exists(), "PDF output file was not generated"
    pdf_size = PDF_OUTPUT_PATH.stat().st_size
    print(f"PDF generated successfully ({pdf_size:,} bytes).")

    # Rasterize page 1 using pypdfium2
    print("Rasterizing PDF page 1 via pypdfium2...")
    pdf = pdfium.PdfDocument(str(PDF_OUTPUT_PATH))
    page = pdf.get_page(0)
    # Render at 300 DPI (approx 4.16x scale from 72 DPI)
    bitmap = page.render(scale=300 / 72)
    pil_image = bitmap.to_pil()

    # Crop around the conjunct test box
    # A4 at 300 DPI is approx 2480 x 3508 pixels
    width, height = pil_image.size
    print(f"Rendered image size: {width} x {height}")

    # The conjunct box is rendered right below title/watermark near top-center
    crop_box = (
        int(width * 0.08),
        int(height * 0.12),
        int(width * 0.92),
        int(height * 0.28),
    )
    cropped = pil_image.crop(crop_box)
    cropped.save(str(IMAGE_OUTPUT_PATH), "PNG")

    assert IMAGE_OUTPUT_PATH.exists(), "Cropped image was not saved"
    img_size = IMAGE_OUTPUT_PATH.stat().st_size
    print(f"Successfully saved cropped conjunct check to: {IMAGE_OUTPUT_PATH} ({img_size:,} bytes)")


if __name__ == "__main__":
    generate_conjunct_proof()
