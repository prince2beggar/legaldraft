"""
Synthetic Scans Generator for Sprint S4 Document Ingestion Testing (AC-M03-1..6).
Generates fixed synthetic document images and a 5-page PDF.
Guarantees:
- Every image and page is prominently labeled [নমুনা] and FAKE_TEST_DATA.
- Covers: clean, rotated, low-contrast, blurred, noisy, ben+eng mixed.
"""

import random
from pathlib import Path

import pypdf
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "synthetic_scans"
FONT_PATH = (
    Path(__file__).resolve().parents[1]
    / "backend"
    / "app"
    / "static"
    / "fonts"
    / "NotoSansBengali-Regular.ttf"
)


def get_font(size: int = 20):
    if FONT_PATH.exists():
        try:
            return ImageFont.truetype(str(FONT_PATH), size)
        except Exception:
            pass
    return ImageFont.load_default()


def create_base_canvas(
    width: int = 800, height: int = 1100, bg_color: str = "#FAF8F5"
) -> Image.Image:
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    # Border
    draw.rectangle([(20, 20), (width - 20, height - 20)], outline="#94A3B8", width=2)
    # Synthetic stamp banner
    font_large = get_font(26)
    font_sub = get_font(16)
    draw.rectangle([(20, 20), (width - 20, 80)], fill="#FEF3C7")
    draw.text((40, 28), "[নমুনা] আইনি পরীক্ষার দলিল (FAKE_TEST_DATA)", fill="#92400E", font=font_large)
    draw.text(
        (40, 56), "সতর্কতা: এটি সম্পূর্ণ কৃত্রিম ও সফটওয়্যার পরীক্ষার জন্য তৈরি।", fill="#B45309", font=font_sub
    )
    return img


def generate_clean_notice() -> Image.Image:
    img = create_base_canvas()
    draw = ImageDraw.Draw(img)
    font_title = get_font(22)
    font_body = get_font(18)
    font_bold = get_font(18)

    y = 110
    draw.text((250, y), "আইনি নোটিশ (LEGAL NOTICE)", fill="#0F172A", font=font_title)
    y += 50
    draw.text((50, y), "প্রেরক: অ্যাডভোকেট এম. এ. সালাম (সুপ্রিম কোর্ট বার)", fill="#0F172A", font=font_bold)
    y += 35
    draw.text((50, y), "প্রাপক: জনাব আরিফুল হক, পিতা: মরহুম কায়সার হক", fill="#0F172A", font=font_bold)
    y += 35
    draw.text(
        (50, y), "বিষয়: বকেয়া বাড়িভাড়া বাবদ ৫০,০০০ টাকা পরিশোধের নোটিশ", fill="#0F172A", font=font_bold
    )
    y += 45
    draw.line([(50, y), (750, y)], fill="#CBD5E1", width=1)
    y += 25

    body_lines = [
        "জনাব,",
        "আমার মক্কেল জনাব রফিকুল ইসলাম সাহেবের নির্দেশক্রমে আপনাকে জানানো যাইতেছে যে,",
        "আপনি মিরপুর সেকশন ১০, ব্লক বি, হোল্ডিং ১২/এ ঠিকানায় অবস্থিত দোকানটির ভাড়াটিয়া।",
        "বিগত ১৫ জানুয়ারি ২০২৬ তারিখ হইতে আপনি মাসিক ২৫,০০০ টাকা হারে দুই মাসের বকেয়া",
        "ভাড়া মোট ৫০,০০০ (পঞ্চাশ হাজার) টাকা পরিশোধ করেন নাই।",
        "অতএব, এই নোটিশ প্রাপ্তির ১৫ (পনেরো) দিনের মধ্যে উক্ত বকেয়া অর্থ পরিশোধ করিবার জন্য",
        "অনুরোধ করা যাইতেছে। অন্যথায় আপনার বিরুদ্ধে উপযুক্ত আদালতে আইনানুগ ব্যবস্থা গ্রহণ করা হইবে।",
    ]
    for line in body_lines:
        draw.text((50, y), line, fill="#1E293B", font=font_body)
        y += 34

    y += 40
    draw.text((50, y), "তারিখ: ১০ ফেব্রুয়ারি ২০২৬", fill="#334155", font=font_bold)
    draw.text((500, y), "স্বাক্ষর: এম. এ. সালাম (অ্যাডভোকেট)", fill="#334155", font=font_bold)
    return img


def generate_mixed_deed() -> Image.Image:
    img = create_base_canvas()
    draw = ImageDraw.Draw(img)
    font_title = get_font(22)
    font_body = get_font(17)
    font_bold = get_font(17)

    y = 110
    draw.text((220, y), "চুক্তিপত্র ও দলিল (DEED OF AGREEMENT)", fill="#0F172A", font=font_title)
    y += 50
    draw.text(
        (50, y),
        "১ম পক্ষ (First Party): মেসার্স গোল্ডেন ট্রেডিং (Golden Trading Ltd)",
        fill="#0F172A",
        font=font_bold,
    )
    y += 35
    draw.text(
        (50, y),
        "জাতীয় পরিচয়পত্র (NID): 198526925000123, Phone: +8801711223344",
        fill="#0F172A",
        font=font_body,
    )
    y += 35
    draw.text(
        (50, y),
        "২য় পক্ষ (Second Party): জনাব বশির উদ্দিন (Bashir Uddin)",
        fill="#0F172A",
        font=font_bold,
    )
    y += 35
    draw.text(
        (50, y), "NID No: 199026925000456, Passport: BD-9876543", fill="#0F172A", font=font_body
    )
    y += 45
    draw.line([(50, y), (750, y)], fill="#CBD5E1", width=1)
    y += 25

    body_lines = [
        "তফসিল বিবরণী (Property Schedule):",
        "মৌজা: তেজগাঁও, খতিয়ান নং: ১২৩৪, দাগ নং: ৫৬৭৮, জমির পরিমাণ: ৫ শতাংশ।",
        "চুক্তি মূল্য (Consideration Amount): BDT 2,50,000/- (দুই লক্ষ পঞ্চাশ হাজার টাকা)।",
        "অগ্রিম জামানত (Advance Security Deposit): BDT 50,000/- (Paid on 12 March 2026).",
        "কার্যকর তারিখ (Effective Date): 01 April 2026 to 31 March 2029.",
        "Dispute Resolution: Any breach shall be settled under the Arbitration Act 2001.",
    ]
    for line in body_lines:
        draw.text((50, y), line, fill="#1E293B", font=font_body)
        y += 34

    return img


def generate_all_scans():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Clean scan
    clean = generate_clean_notice()
    clean.save(OUTPUT_DIR / "clean_scan.png")

    # 2. Rotated scan (rotated 90 deg clockwise)
    rotated = clean.rotate(-90, expand=True)
    rotated.save(OUTPUT_DIR / "rotated_scan.png")

    # 3. Low-contrast scan
    enhancer = ImageEnhance.Contrast(clean)
    low_contrast = enhancer.enhance(0.3)
    low_contrast.save(OUTPUT_DIR / "low_contrast_scan.png")

    # 4. Blurred scan
    blurred = clean.filter(ImageFilter.GaussianBlur(radius=2.0))
    blurred.save(OUTPUT_DIR / "blurred_scan.png")

    # 5. Noisy scan (salt & pepper)
    noisy = clean.copy()
    pixels = noisy.load()
    w, h = noisy.size
    for _ in range(int(w * h * 0.04)):
        rx = random.randint(0, w - 1)
        ry = random.randint(0, h - 1)
        pixels[rx, ry] = (0, 0, 0) if random.random() < 0.5 else (255, 255, 255)
    noisy.save(OUTPUT_DIR / "noisy_scan.png")

    # 6. Mixed Bangla + English scan
    mixed = generate_mixed_deed()
    mixed.save(OUTPUT_DIR / "ben_eng_mixed_scan.png")

    # 7. 5-page synthetic PDF for AC-M03-1
    pdf_writer = pypdf.PdfWriter()
    temp_images = []
    for page_num in range(1, 6):
        page_img = create_base_canvas()
        draw = ImageDraw.Draw(page_img)
        f_head = get_font(22)
        f_txt = get_font(18)
        draw.text((220, 120), f"[নমুনা] মামলার নথি — পৃষ্ঠা নং {page_num}", fill="#0F172A", font=f_head)
        draw.text(
            (50, 180),
            f"Page {page_num} of 5: Synthetic Court Pleadings & Exhibits (FAKE_TEST_DATA)",
            fill="#334155",
            font=f_txt,
        )
        draw.text(
            (50, 220),
            f"অনুচ্ছেদ {page_num}: বিজ্ঞ সিনিয়র সহকারী জজ আদালত, ঢাকা। মোকদ্দমা নং {page_num}৫/২০২৬।",
            fill="#1E293B",
            font=f_txt,
        )
        draw.text(
            (50, 260),
            "বাদী: হাজি কাশেম আলী বনাম বিবাদী: মেসার্স সোনালী ট্রেডার্স।",
            fill="#1E293B",
            font=f_txt,
        )
        draw.text(
            (50, 300),
            f"দাবির পরিমাণ: {page_num * 10000} টাকা। তারিখ: {page_num} মার্চ ২০২৬।",
            fill="#1E293B",
            font=f_txt,
        )
        page_pdf_path = OUTPUT_DIR / f"temp_page_{page_num}.pdf"
        page_img.save(page_pdf_path, "PDF", resolution=100.0)
        temp_images.append(page_pdf_path)

        reader = pypdf.PdfReader(str(page_pdf_path))
        pdf_writer.add_page(reader.pages[0])

    five_page_pdf = OUTPUT_DIR / "synthetic_5page_sample.pdf"
    with open(five_page_pdf, "wb") as f_out:
        pdf_writer.write(f_out)

    for p in temp_images:
        try:
            p.unlink()
        except Exception:
            pass

    print(f"Generated 6 synthetic scans and 1 5-page PDF in: {OUTPUT_DIR}")


if __name__ == "__main__":
    generate_all_scans()
