"""
Sprint S4 Interactive Demonstration Script (Module M03 Document Ingestion).
Demonstrates:
1. Document upload & safety scan (BasicMagicBytesScanner).
2. PDF page splitting & image enhancement (deskew, contrast, grayscale).
3. OCR text extraction (FakeOcr benchmark runner).
4. Document classification (notice, deed, court_order).
5. Legal entity & stated date extraction with bbox snippet cropping.
6. Field review state machine (extracted -> reviewed -> verified).
7. SHA-256 deduplication (idempotent duplicate detection).
8. Secure purge with immutable hash-chained audit logging.

Run: python scripts/demo_s4.py
"""

import sys
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Set stdout to UTF-8 for Bengali console output
if sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from packages.trust_kernel.audit import audit_logger
from packages.trust_kernel.document_engine import document_service

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "synthetic_scans"


def run_demo():
    print("=" * 70)
    print("আইন-AI — Sprint S4: Document Ingestion & Management Demo (M03)")
    print("=" * 70)

    # 1. Upload 5-Page Synthetic Court Pleadings PDF
    pdf_file = FIXTURES_DIR / "synthetic_5page_sample.pdf"
    if not pdf_file.exists():
        print(f"Error: Fixture {pdf_file} not found. Run scripts/generate_synthetic_scans.py first.")
        return

    print("\n[ধাপ ১] ৫ পৃষ্ঠার আদালত ফাইলিং নমুনা PDF আপলোড...")
    owner_id = f"demo-advocate-{uuid.uuid4().hex[:6]}"
    pdf_bytes = pdf_file.read_bytes()

    doc = document_service.upload_document(
        owner_id=owner_id,
        filename="synthetic_5page_sample.pdf",
        file_bytes=pdf_bytes,
        intent="prepare_matter",
    )

    print(f"  ✓ নথি আইডি: {doc['id']}")
    print(f"  ✓ প্রক্রিয়াকরণ স্থিতি: {doc['processing_status']}")
    print(f"  ✓ পৃষ্ঠার সংখ্যা: {doc['page_count']} টি পৃষ্ঠা")
    print(f"  ✓ স্বয়ংক্রিয় শ্রেণিবিভাগ: {doc['doc_type']} (Court Pleadings / Order)")
    print(f"  ✓ হ্যাশ (SHA-256): {doc['sha256'][:16]}...")

    # 2. Inspect Extracted Fields
    print("\n[ধাপ ২] নথির পৃষ্ঠা ও নিষ্কাশিত আইনি তথ্যমালা:")
    fields = document_service.db.list_document_fields(doc["id"])
    for f in fields[:6]:
        crop_status = "ক্রপ প্রস্তুত" if f.get("crop_key") else "ক্রপ নেই"
        print(f"  - [{f['confidence_word'].upper()}] {f['key']}: \"{f['value']}\" (পৃষ্ঠা {f['page_no']}, {crop_status})")

    # 3. Field State Machine: Edit & Confirm (AC-M03-2)
    if fields:
        fld = fields[0]
        fld_id = fld["id"]
        print("\n[ধাপ ৩] তথ্য সংশোধন ও পর্যালোচনা স্টেট মেশিন (AC-M03-2):")
        print(f"  * বর্তমান অবস্থা: {fld['state']} | মান: \"{fld['value']}\"")

        # Edit with confirm=True
        updated = document_service.edit_field_value(
            field_id=fld_id,
            new_value=f"{fld['value']} (সংশোধিত)",
            user_id=owner_id,
            confirm=True,
        )
        print(f"  ✓ সংশোধনের পর অবস্থা: {updated['state']} (পর্যালোচিত)")
        print(f"  ✓ সংশোধক ব্যবহারকারী: {updated['reviewed_by']}")

        # Verify field
        verified = document_service.verify_field_value(field_id=fld_id, user_id=owner_id)
        print(f"  ✓ চূড়ান্ত স্বাক্ষরের পর অবস্থা: {verified['state']} (যাচাইকৃত)")

    # 4. SHA-256 Deduplication (Idempotent Check)
    print("\n[ধাপ ৪] ডিডুপ্লিকেশন (SHA-256) পরীক্ষা:")
    doc_dup = document_service.upload_document(
        owner_id=owner_id,
        filename="duplicate_copy.pdf",
        file_bytes=pdf_bytes,
        intent="prepare_matter",
    )
    if doc_dup["id"] == doc["id"] and doc_dup.get("is_deduplicated"):
        print("  ✓ সফল: একই নথির দ্বিতীয় আপলোড শনাক্ত হয়েছে। অতিরিক্ত স্টোরেজ খরচ ব্যতিরেকে পূর্বের নথি ফেরত দেওয়া হয়েছে।")

    # 5. Purge Document with Immutable Audit Log
    print("\n[ধাপ ৫] নিরাপদ ডেটা পার্জ ও অডিট লেজার সংরক্ষণ:")
    document_service.purge_document_with_audit(doc_id=doc["id"], user_id=owner_id)
    purged_doc = document_service.db.get_document(doc["id"])
    assert purged_doc is None, "Document must be purged from database"
    print("  ✓ ডাটাবেস ও অবজেক্ট স্টোরেজ থেকে নথি সম্পূর্ণ মুছে ফেলা হয়েছে।")

    recent_audits = audit_logger.get_recent_logs(limit=5)
    purge_log = next((entry for entry in recent_audits if entry["action"] == "document.purge" and entry["object_id"] == doc["id"]), None)
    if purge_log:
        print(f"  ✓ অডিট ট্রেইলে অপরিবর্তনীয় রেকর্ড সংরক্ষিত: অ্যাকশন={purge_log['action']}, মেটা={purge_log['meta']}")

    print("\n" + "=" * 70)
    print("Sprint S4 ডেমো সফলভাবে সম্পন্ন হয়েছে। সকল নিরাপত্তা ও আইনি যাচাই কার্যকর।")
    print("=" * 70)


if __name__ == "__main__":
    run_demo()
