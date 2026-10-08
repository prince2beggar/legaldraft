"""
Generates sample SRS-compliant Brief PDF and DOCX artifacts (G10 / S9 Hardening).
Saves to storage/screenshots/ and copies to brain artifact directory.
Uses exact 10 SRS elements with watermark text.
"""

import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.trust_kernel.brief_engine import brief_engine
from packages.trust_kernel.case_engine import CaseEngine

STORAGE_DIR = REPO_ROOT / "storage" / "screenshots"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACT_DIR = Path(
    r"C:\Users\Lenovo\.gemini\antigravity\brain\f5b387fc-eb28-4e1b-9940-b3291f442234"
)


def generate_sample_brief_files():
    user_id = "01711000001"
    case_engine = CaseEngine()
    case = case_engine.create_case(
        user_id=user_id,
        title="জমি সংক্রান্ত দখল পুনরুদ্ধার মোকদ্দমা",
        case_type="দেওয়ানি বিরোধ (জমির স্বত্ব)",
    )
    case_id = case["id"]

    brief_data = brief_engine.build_case_brief(
        case_id=case_id,
        owner_id=user_id,
        include_private_notes=True,
    )
    brief_id = brief_data["id"]

    watermark = "গোপনীয় • প্রাপক: 01799887766 • মেয়াদ: ২০২৬-১১-০৭"

    # 1. Render PDF
    pdf_bytes = brief_engine.render_brief_pdf(
        brief_id=brief_id,
        owner_id=user_id,
        watermark_text=watermark,
    )
    pdf_path = STORAGE_DIR / "sample_case_brief_srs.pdf"
    pdf_path.write_bytes(pdf_bytes)

    # 2. Render DOCX
    docx_bytes = brief_engine.render_brief_docx(
        brief_id=brief_id,
        owner_id=user_id,
        watermark_text=watermark,
    )
    docx_path = STORAGE_DIR / "sample_case_brief_srs.docx"
    docx_path.write_bytes(docx_bytes)

    # Copy to brain artifact directory
    if ARTIFACT_DIR.exists():
        shutil.copy2(pdf_path, ARTIFACT_DIR / "sample_case_brief_srs.pdf")
        shutil.copy2(docx_path, ARTIFACT_DIR / "sample_case_brief_srs.docx")

    print(f"Sample PDF generated:  {pdf_path} ({len(pdf_bytes)} bytes)")
    print(f"Sample DOCX generated: {docx_path} ({len(docx_bytes)} bytes)")
    return {
        "pdf_path": str(pdf_path),
        "pdf_size": len(pdf_bytes),
        "docx_path": str(docx_path),
        "docx_size": len(docx_bytes),
    }


if __name__ == "__main__":
    generate_sample_brief_files()
