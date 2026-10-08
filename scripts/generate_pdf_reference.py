"""
Generates the reference PNG for PDF conjunct shaping proof.
Rasterizes page 0 using pypdfium2 and saves to tests/data/reference_conjuncts.png.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import pypdfium2

from packages.trust_kernel.ai_gateway import AIGateway
from packages.trust_kernel.db import DatabaseManager
from packages.trust_kernel.draft_engine import DraftEngine

DATA_DIR = REPO_ROOT / "tests" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
REF_PNG_PATH = DATA_DIR / "reference_conjuncts.png"
TEMP_DB_PATH = DATA_DIR / "temp_ref.db"


def generate_reference():
    db = DatabaseManager(f"sqlite:///{TEMP_DB_PATH}")
    db.init_db()
    db.seed_default_templates()

    reviewer = db.create_user(phone="01700000002", name="Reviewer", role="reviewer")
    citizen = db.create_user(phone="01711999888", name="মো: তানভীর হোসেন", role="citizen")
    db.approve_template("DT-02", approver_id=reviewer["id"], note="Approved for reference")

    gateway = AIGateway(db=db)
    engine = DraftEngine(db=db, gateway=gateway)

    conjunct_sentence = (
        "জ্ঞানী ব্যক্তিগণ সাক্ষ্য প্রদানপূর্বক নিঃশঙ্কচিত্তে চুক্তির শর্ত পালন করিবেন (ক্ষ, জ্ঞ, ন্দ, স্ত্র, ক্ত, ঙ্গ, শ্র)।"
    )

    draft = engine.start_draft(user_id=citizen["id"], template_id="DT-02")
    engine.save_answers(
        draft_id=draft["id"],
        user_id=citizen["id"],
        answers={
            "deponent_name": "শ্রী তানভীর হোসেন",
            "deponent_father": "আনোয়ার হোসেন",
            "deponent_address": "ঢাকা",
            "deponent_nid": "1992269251000002",
            "affidavit_purpose": "সাধারণ বিবরণ",
            "statement_text": conjunct_sentence,
            "declaration_date": "2026-10-15",
            "place_of_execution": "ঢাকা সিএমএম আদালত",
        },
    )

    res = engine.export_draft(draft_id=draft["id"], user_id=citizen["id"], export_format="pdf")
    dec_bytes, fn, mt = engine.get_decrypted_export_bytes(res["export_id"], citizen["id"])

    # Rasterize using pypdfium2
    pdf = pypdfium2.PdfDocument(dec_bytes)
    page = pdf[0]
    bitmap = page.render(scale=1.5)
    pil_image = bitmap.to_pil()

    pil_image.save(str(REF_PNG_PATH))
    print(
        f"Committed reference image generated at {REF_PNG_PATH} (size: {REF_PNG_PATH.stat().st_size} bytes)"
    )

    # Cleanup temp db
    try:
        db.engine.dispose()
        if TEMP_DB_PATH.exists():
            TEMP_DB_PATH.unlink()
    except Exception:
        pass


if __name__ == "__main__":
    generate_reference()
