"""
Generates a sample draft PDF using DraftEngine to verify PDF generation and store sample in storage/.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from packages.trust_kernel.ai_gateway import AIGateway
from packages.trust_kernel.db import DatabaseManager
from packages.trust_kernel.draft_engine import DraftEngine

STORAGE_DIR = REPO_ROOT / "storage"
DB_FILE = STORAGE_DIR / "sample_temp.db"


def generate_sample_pdf():
    db = DatabaseManager(f"sqlite:///{DB_FILE}")
    db.init_db()
    db.seed_default_templates()

    # Approve DT-01 for sample export
    db.create_user(phone="01700000001", name="Admin Author", role="admin")
    reviewer = db.create_user(phone="01700000002", name="Reviewer Lawyer", role="reviewer")
    citizen = db.create_user(phone="01711999888", name="মো: তানভীর হোসেন", role="citizen")

    db.approve_template("DT-01", approver_id=reviewer["id"], note="Approved for sample PDF demo")

    gateway = AIGateway(db=db)
    engine = DraftEngine(db=db, gateway=gateway)

    # Start draft
    draft = engine.start_draft(user_id=citizen["id"], template_id="DT-01")
    did = draft["id"]

    # Fill sample answers
    engine.save_answers(
        draft_id=did,
        user_id=citizen["id"],
        answers={
            "landlord_name": "আবুল কাশেম",
            "landlord_father": "মরহুম রফিকুল ইসলাম",
            "landlord_address": "বাড়ি # ১২, রোড # ৪, ধানমন্ডি, ঢাকা",
            "landlord_nid": "1980269251000001",
            "tenant_name": "মো: তানভীর হোসেন",
            "tenant_father": "আনোয়ার হোসেন",
            "tenant_address": "বাড়ি # ৫, সেকশন # ১০, মিরপুর, ঢাকা",
            "tenant_nid": "1992269251000002",
            "premises_address": "বাড়ি # ৪২/এ, ফ্ল্যাট ৩-বি, ধানমন্ডি আ/এ, ঢাকা",
            "start_date": "2026-11-01",
            "end_date": "2027-10-31",
            "monthly_rent": 35000,
            "monthly_rent_words": "পঁয়ত্রিশ হাজার টাকা",
            "security_deposit": 70000,
            "security_deposit_words": "সত্তর হাজার টাকা",
            "rent_due_day": 7,
            "utility_included": "no",
            "utility_details": "বিদ্যুৎ ও গ্যাস বিল মিটার রিডিং অনুযায়ী ভাড়াটিয়া পরিশোধ করিবেন।",
        },
    )

    # Export draft to PDF
    res = engine.export_draft(draft_id=did, user_id=citizen["id"], export_format="pdf")
    src_pdf = Path(res["file_path"])

    dest_pdf = STORAGE_DIR / "sample_draft_export_DT01.pdf"
    if src_pdf.exists():
        import shutil

        shutil.copy(src_pdf, dest_pdf)
        print(
            f"Sample PDF successfully exported to {dest_pdf} (size: {dest_pdf.stat().st_size} bytes)"
        )

    # Dispose engine before cleanup on Windows
    try:
        db.engine.dispose()
        if DB_FILE.exists():
            DB_FILE.unlink()
    except Exception:
        pass


if __name__ == "__main__":
    generate_sample_pdf()
