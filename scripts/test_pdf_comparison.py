"""Test rasterization comparison against reference_conjuncts.png."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import math

import pypdfium2
from PIL import Image

from packages.trust_kernel.ai_gateway import AIGateway
from packages.trust_kernel.db import DatabaseManager
from packages.trust_kernel.draft_engine import DraftEngine


def main():
    data_dir = REPO_ROOT / "tests" / "data"
    ref_img_path = data_dir / "reference_conjuncts.png"
    assert ref_img_path.exists(), f"Reference PNG missing: {ref_img_path}"

    temp_db_path = data_dir / "temp_cmp.db"
    db = DatabaseManager(f"sqlite:///{temp_db_path}")
    db.init_db()
    db.seed_default_templates()

    reviewer = db.create_user(phone="01700000002", name="Reviewer", role="reviewer")
    citizen = db.create_user(phone="01711999888", name="মো: তানভীর হোসেন", role="citizen")
    db.approve_template("DT-02", approver_id=reviewer["id"], note="Approved")

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
    # Get decrypted bytes
    dec_bytes, fn, mt = engine.get_decrypted_export_bytes(res["export_id"], citizen["id"])

    # Load pdf from bytes
    pdf = pypdfium2.PdfDocument(dec_bytes)
    page = pdf[0]
    bitmap = page.render(scale=1.5)
    rendered_img = bitmap.to_pil()

    ref_img = Image.open(str(ref_img_path))

    # Calculate RMSE
    g1 = rendered_img.convert("L")
    g2 = ref_img.convert("L")
    if g1.size != g2.size:
        print(f"Sizes differ: {g1.size} vs {g2.size}")
        g2 = g2.resize(g1.size)
    pixels1 = list(g1.getdata())
    pixels2 = list(g2.getdata())
    diff_sq_sum = sum((p1 - p2) ** 2 for p1, p2 in zip(pixels1, pixels2))
    rmse = math.sqrt(diff_sq_sum / len(pixels1))
    print(f"Calculated RMSE: {rmse:.4f}")

    # Dispose db
    try:
        db.engine.dispose()
        if temp_db_path.exists():
            temp_db_path.unlink()
    except Exception:
        pass


if __name__ == "__main__":
    main()
