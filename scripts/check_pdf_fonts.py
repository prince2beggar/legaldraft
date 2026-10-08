"""Test font listing and watermark in generated PDF."""

from pathlib import Path

import pypdf

REPO_ROOT = Path(__file__).resolve().parent.parent
sample_pdf = REPO_ROOT / "storage" / "sample_draft_export_DT01.pdf"

reader = pypdf.PdfReader(str(sample_pdf))
print(f"Total pages: {len(reader.pages)}")

# Extract fonts
font_names = set()
for page in reader.pages:
    if "/Resources" in page and "/Font" in page["/Resources"]:
        f_dict = page["/Resources"]["/Font"]
        for f_name, f_obj in f_dict.items():
            base_font = f_obj.get("/BaseFont", "")
            font_names.add(str(base_font))

print("Embedded fonts:", font_names)

# Extract text
text = ""
for page in reader.pages:
    text += page.extract_text() or ""

print("Contains watermark?", "খসড়া" in text)
print("Contains conjuncts?", any(c in text for c in ["ক্ষ", "জ্ঞ", "ন্দ"]))
