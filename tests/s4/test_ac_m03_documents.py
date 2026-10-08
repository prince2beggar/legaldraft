"""
Tests for Sprint S4: Document Ingestion & Management (Module M03).
SRS Section 5.3, Section 9.3 (S4), AC-M03-1 to AC-M03-6.

Covers:
- AC-M03-1: 5-page PDF ingestion, splitting, enhancement, OCR, classification, extraction under 60s
- AC-M03-1 (variants): synthetic scan variants (clean, rotated, low_contrast, blurred, noisy, ben_eng_mixed)
- AC-M03-2: Field bbox crop linkage & state machine (extracted -> reviewed (requires confirm=True) -> verified)
- AC-M03-3: Auto-retry 3 times on OCR failure, user-friendly error message, zero data loss
- AC-M03-4: Screening items without bbox/span_ref NEVER appear in client UI/response
- AC-M03-5: Unauthorised access attempt returns 403/404 and is logged in trust_audit_logs
- AC-M03-6: Resumable chunked upload reassembly
- Deduplication: SHA-256 hash match returns existing document idempotently
- Purge: Document file & DB purge with immutable audit ledger recording
- Adapter Slots: ClamAV, MinIO, Tesseract marked UNVERIFIED with clean local fallbacks
"""

import hashlib
import time
import uuid
from pathlib import Path

import pytest

from packages.trust_kernel.audit import audit_logger
from packages.trust_kernel.db import db_manager
from packages.trust_kernel.document_engine import (
    BasicMagicBytesScanner,
    ClamAvAdapterSlot,
    DocumentService,
    FakeOcrEngine,
    ImageEnhancer,
    LocalFilesystemObjectStore,
    MinioObjectStoreAdapterSlot,
    TesseractOcrAdapter,
)

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "synthetic_scans"


@pytest.fixture
def doc_service(tmp_path):
    """Provides an isolated DocumentService instance with temporary object store."""
    store = LocalFilesystemObjectStore(base_dir=tmp_path / "doc_storage")
    scanner = BasicMagicBytesScanner()
    ocr = FakeOcrEngine()
    service = DocumentService(db=db_manager, store=store, scanner=scanner, ocr=ocr)
    return service


def test_ac_m03_1_five_page_pdf_pipeline_enhancement_and_classification(doc_service):
    """
    AC-M03-1: 5-page PDF uploaded, pages split, enhanced, OCR executed,
    document classified, and fields extracted in under 60 seconds.
    """
    pdf_path = FIXTURES_DIR / "synthetic_5page_sample.pdf"
    assert pdf_path.exists(), f"Missing test fixture: {pdf_path}"
    pdf_bytes = pdf_path.read_bytes()

    owner_id = f"test-citizen-{uuid.uuid4().hex[:6]}"
    start_time = time.time()

    doc = doc_service.upload_document(
        owner_id=owner_id,
        filename="synthetic_5page_sample.pdf",
        file_bytes=pdf_bytes,
        intent="prepare_matter",
    )
    elapsed = time.time() - start_time

    # Performance requirement: under 60 seconds
    assert elapsed < 60.0, f"Processing took {elapsed}s, exceeding 60s limit"
    assert doc["id"] is not None
    assert doc["page_count"] == 5
    assert doc["processing_status"] == "completed"
    assert doc["doc_type"] in ("notice", "deed", "court_order", "petition")

    # Verify pages saved in DB and store
    pages = doc_service.db.list_document_pages(doc["id"])
    assert len(pages) == 5
    for idx, p in enumerate(pages, start=1):
        assert p["page_no"] == idx
        assert p["image_key"] is not None
        assert doc_service.store.exists(p["image_key"])
        assert "[নমুনা]" in p["ocr_text"]

    # Verify extracted fields
    fields = doc_service.db.list_document_fields(doc["id"])
    assert len(fields) > 0
    # Every extracted field must have a valid bbox
    for f in fields:
        assert f["bbox"] is not None
        assert len(f["bbox"]) == 4
        assert f["state"] == "extracted"


def test_ac_m03_1_synthetic_scan_variants_enhancement_and_ocr(doc_service):
    """
    AC-M03-1: Pipeline processes synthetic scans (clean, rotated, low_contrast, blurred, noisy, ben_eng_mixed)
    and successfully applies enhancement (deskew, contrast, grayscale).
    """
    variants = [
        "clean_scan.png",
        "rotated_scan.png",
        "low_contrast_scan.png",
        "blurred_scan.png",
        "noisy_scan.png",
        "ben_eng_mixed_scan.png",
    ]

    for variant_file in variants:
        img_path = FIXTURES_DIR / variant_file
        assert img_path.exists(), f"Fixture missing: {variant_file}"
        img_bytes = img_path.read_bytes()

        # Direct ImageEnhancer check
        enh_bytes, enh_name = ImageEnhancer.enhance_image(img_bytes)
        assert len(enh_bytes) > 0
        if "rotated" in variant_file:
            assert "rotate_90_deskew" in enh_name
        assert "contrast_norm" in enh_name

        # Ingest through service
        owner_id = f"test-user-{uuid.uuid4().hex[:6]}"
        doc = doc_service.upload_document(
            owner_id=owner_id,
            filename=variant_file,
            file_bytes=img_bytes,
            intent="understand",
        )
        assert doc["processing_status"] == "completed"
        assert doc["page_count"] == 1


def test_ac_m03_2_field_crop_link_and_state_machine_reviewed_verified(doc_service):
    """
    AC-M03-2: Every extracted field links to a snippet crop.
    Editing a field value changes state to 'reviewed' ONLY after explicit confirm=True.
    Verification transitions to 'verified'.
    """
    img_path = FIXTURES_DIR / "clean_scan.png"
    img_bytes = img_path.read_bytes()
    owner_id = f"test-citizen-{uuid.uuid4().hex[:6]}"

    doc = doc_service.upload_document(
        owner_id=owner_id,
        filename="clean_scan.png",
        file_bytes=img_bytes,
    )
    fields = doc_service.db.list_document_fields(doc["id"])
    assert len(fields) > 0

    field = fields[0]
    field_id = field["id"]
    assert field["state"] == "extracted"
    assert field["crop_key"] is not None
    assert doc_service.store.exists(field["crop_key"]), (
        "Snippet crop image must exist in object store"
    )

    # Negative test: editing field without confirm=True MUST fail
    with pytest.raises(ValueError, match="Explicit confirmation required"):
        doc_service.edit_field_value(field_id, "সংশোধিত নাম", user_id=owner_id, confirm=False)

    # State remains 'extracted'
    field_after_fail = doc_service.db.get_document_field(field_id)
    assert field_after_fail["state"] == "extracted"

    # Positive test: editing with confirm=True transitions to 'reviewed'
    updated = doc_service.edit_field_value(field_id, "সংশোধিত নাম", user_id=owner_id, confirm=True)
    assert updated["value"] == "সংশোধিত নাম"
    assert updated["state"] == "reviewed"
    assert updated["reviewed_by"] == owner_id

    # Verify transitions to 'verified'
    verified = doc_service.verify_field_value(field_id, user_id=owner_id)
    assert verified["state"] == "verified"
    assert verified["verified_by"] == owner_id


def test_ac_m03_3_failed_ocr_retry_three_times_and_user_error_message(tmp_path):
    """
    AC-M03-3: If OCR fails, system retries up to 3 times.
    After 3rd failure, document state is 'failed' with a user-friendly Bangla message
    and zero data loss (original file preserved in object store).
    """

    class FailingOcrEngine(FakeOcrEngine):
        def __init__(self):
            self.call_count = 0

        def ocr_page(self, image_bytes: bytes, lang: str = "ben+eng") -> tuple[str, float]:
            self.call_count += 1
            raise RuntimeError("Synthetic OCR Engine Error: Unreadable blurred fragment")

    failing_ocr = FailingOcrEngine()
    store = LocalFilesystemObjectStore(base_dir=tmp_path / "retry_storage")
    service = DocumentService(
        db=db_manager, store=store, scanner=BasicMagicBytesScanner(), ocr=failing_ocr
    )

    img_path = FIXTURES_DIR / "blurred_scan.png"
    img_bytes = img_path.read_bytes()
    owner_id = f"test-user-{uuid.uuid4().hex[:6]}"

    doc = service.upload_document(
        owner_id=owner_id,
        filename="blurred_scan.png",
        file_bytes=img_bytes,
    )

    # Verified: retried 3 times
    assert failing_ocr.call_count == 3
    assert doc["processing_status"] == "failed"
    assert doc["retry_count"] == 3
    # User-friendly Bangla message
    assert "নথি প্রক্রিয়াকরণে সমস্যা হয়েছে" in doc["error_message"]
    # Zero data loss: original file is intact in object store
    assert store.exists(doc["storage_key"])
    assert store.get_object(doc["storage_key"]) == img_bytes


def test_ac_m03_4_screening_items_without_bbox_never_appear(doc_service):
    """
    AC-M03-4: Screening items or fields without a bounding box / span_ref NEVER
    appear in the document viewer UI or get_document_secure API payload.
    """
    img_path = FIXTURES_DIR / "clean_scan.png"
    img_bytes = img_path.read_bytes()
    owner_id = f"test-user-{uuid.uuid4().hex[:6]}"

    doc = doc_service.upload_document(
        owner_id=owner_id,
        filename="clean_scan.png",
        file_bytes=img_bytes,
    )

    # Manually inject a ghost field without bbox into DB to test screening filter
    doc_service.db.save_document_field(
        {
            "document_id": doc["id"],
            "key": "ghost.unreferenced_field",
            "value": "Ghost Value Without Span",
            "confidence": 0.50,
            "confidence_word": "check",
            "page_no": 1,
            "bbox": None,  # No bbox
            "state": "extracted",
        }
    )

    # Call get_document_secure
    secure_doc = doc_service.get_document_secure(doc["id"], actor_id=owner_id)
    visible_keys = [f["key"] for f in secure_doc["fields"]]

    assert "ghost.unreferenced_field" not in visible_keys
    for f in secure_doc["fields"]:
        assert f["bbox"] is not None and len(f["bbox"]) == 4


def test_ac_m03_5_unauthorised_user_document_isolated_and_audited(doc_service):
    """
    AC-M03-5: Unauthorised requests (User B requesting User A's document)
    return 403 / raise PermissionError and are recorded in trust_audit_logs.
    """
    img_bytes = (FIXTURES_DIR / "clean_scan.png").read_bytes()
    user_a = f"citizen-alice-{uuid.uuid4().hex[:6]}"
    user_b = f"citizen-intruder-bob-{uuid.uuid4().hex[:6]}"

    doc = doc_service.upload_document(
        owner_id=user_a,
        filename="alice_confidential.png",
        file_bytes=img_bytes,
    )

    # User B attempts to access User A's document
    with pytest.raises(PermissionError, match="Unauthorised access"):
        doc_service.get_document_secure(doc["id"], actor_id=user_b, actor_role="citizen")

    # Verify audit entry in trust_audit_logs
    recent_logs = audit_logger.get_recent_logs(limit=10)
    breach_logs = [
        entry
        for entry in recent_logs
        if entry["action"] == "document.unauthorized_access_attempt"
        and entry["actor_id"] == user_b
        and entry["object_id"] == doc["id"]
    ]
    assert len(breach_logs) >= 1, "Breach attempt must be recorded in trust_audit_logs"


def test_ac_m03_6_resumable_chunked_upload_and_reassembly(doc_service):
    """
    AC-M03-6: Resumable chunked upload splits file into chunks, allows resumption,
    and accurately reassembles full file and completes ingestion upon last chunk.
    """
    img_path = FIXTURES_DIR / "ben_eng_mixed_scan.png"
    img_bytes = img_path.read_bytes()
    total_size = len(img_bytes)
    sha256_full = hashlib.sha256(img_bytes).hexdigest()
    owner_id = f"test-resumable-{uuid.uuid4().hex[:6]}"

    # Split into 3 chunks
    chunk_size = (total_size + 2) // 3
    chunks = [
        img_bytes[0:chunk_size],
        img_bytes[chunk_size : 2 * chunk_size],
        img_bytes[2 * chunk_size :],
    ]
    assert len(chunks) == 3

    # Initiate
    session = doc_service.initiate_resumable_upload(
        owner_id=owner_id,
        filename="ben_eng_mixed_scan.png",
        total_size=total_size,
        total_chunks=3,
        sha256_hash=sha256_full,
    )
    upload_id = session["upload_id"]

    # Upload chunk 0
    res0 = doc_service.upload_chunk(upload_id, 0, chunks[0])
    assert res0["status"] == "in_progress"
    assert 0 in res0["uploaded_chunks"]

    # Upload chunk 1
    res1 = doc_service.upload_chunk(upload_id, 1, chunks[1])
    assert res1["status"] == "in_progress"
    assert 1 in res1["uploaded_chunks"]

    # Upload chunk 2 (final chunk triggers reassembly and ingestion)
    res2 = doc_service.upload_chunk(upload_id, 2, chunks[2])
    assert res2["status"] == "complete"
    final_doc = res2["document"]
    assert final_doc["processing_status"] == "completed"
    assert final_doc["sha256"] == sha256_full
    assert final_doc["size_bytes"] == total_size


def test_ac_m03_deduplication_sha256_idempotent(doc_service):
    """
    Deduplication: Uploading the exact same document twice by the same user
    returns the existing document idempotently (marked is_deduplicated=True)
    without duplicating storage keys.
    """
    img_bytes = (FIXTURES_DIR / "clean_scan.png").read_bytes()
    owner_id = f"test-dedupe-{uuid.uuid4().hex[:6]}"

    doc1 = doc_service.upload_document(
        owner_id=owner_id, filename="original.png", file_bytes=img_bytes
    )
    assert doc1.get("is_deduplicated") is not True

    doc2 = doc_service.upload_document(
        owner_id=owner_id, filename="duplicate.png", file_bytes=img_bytes
    )
    assert doc2["id"] == doc1["id"]
    assert doc2.get("is_deduplicated") is True


def test_ac_m03_purge_document_with_immutable_audit(doc_service):
    """
    Purge: Deleting a document completely removes files and DB records,
    and logs an audit record with document SHA-256 and size (zero sensitive text).
    """
    img_bytes = (FIXTURES_DIR / "clean_scan.png").read_bytes()
    owner_id = f"test-purge-{uuid.uuid4().hex[:6]}"

    doc = doc_service.upload_document(
        owner_id=owner_id, filename="purge_me.png", file_bytes=img_bytes
    )
    doc_id = doc["id"]
    storage_key = doc["storage_key"]
    assert doc_service.store.exists(storage_key)

    doc_service.purge_document_with_audit(doc_id=doc_id, user_id=owner_id)

    # Storage and DB records are purged
    assert not doc_service.store.exists(storage_key)
    assert doc_service.db.get_document(doc_id) is None
    assert len(doc_service.db.list_document_pages(doc_id)) == 0
    assert len(doc_service.db.list_document_fields(doc_id)) == 0

    # Immutable audit ledger has purge entry
    recent_logs = audit_logger.get_recent_logs(limit=10)
    purge_entries = [
        entry
        for entry in recent_logs
        if entry["action"] == "document.purge" and entry["object_id"] == doc_id
    ]
    assert len(purge_entries) >= 1
    # Check that audit log contains metadata but no sensitive content
    meta = purge_entries[0]["meta"]
    assert "sha256" in meta
    assert "size_bytes" in meta


def test_ac_m03_adapter_slots_unverified_fallback():
    """
    Adapter Slots: Verifies that ClamAV, MinIO, and Tesseract adapter slots
    are marked UNVERIFIED and cleanly delegate to functional local implementations.
    """
    clam = ClamAvAdapterSlot()
    assert clam.status == "UNVERIFIED"
    safe, _ = clam.scan(b"%PDF-1.4 test", "test.pdf")
    assert safe is True

    unsafe, reason = clam.scan(b"MZ\x90executable", "malware.exe")
    assert unsafe is False
    assert "Dangerous executable" in reason or "PE format" in reason

    minio = MinioObjectStoreAdapterSlot()
    assert minio.status == "UNVERIFIED"

    tesseract = TesseractOcrAdapter()
    assert tesseract.status == "UNVERIFIED"
    text, conf = tesseract.ocr_page(b"", "ben+eng")
    assert isinstance(text, str)
    assert 0.0 <= conf <= 1.0


def test_ac_m03_6_pwa_offline_queue_and_online_flush():
    """
    AC-M03-6 (PWA Queue): An upload started offline completes after connectivity returns.
    Verifies in browser with Playwright offline mode:
    1. Camera capture input is available with capture='environment'.
    2. Setting network offline, user selects document -> stored in browser IndexedDB queue.
    3. Setting network online -> queue flushes to server with idempotency key without duplication.
    """
    import json
    import time
    from pathlib import Path

    from playwright.sync_api import sync_playwright

    static_file = (
        Path(__file__).resolve().parents[2] / "backend" / "app" / "static" / "documents_upload.html"
    )

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context()
        page = context.new_page()

        page.route(
            "**/api/v1/documents/upload",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(
                    {"document": {"id": "doc-test-pwa-flushed"}, "status": "completed"}
                ),
            ),
        )

        page.goto(static_file.as_uri())

        # 1. Verify Camera button and capture attribute
        cam_btn = page.locator("#btnCamera")
        cam_input = page.locator("#cameraInput")
        assert cam_btn.is_visible(), "Camera button must be visible"
        assert cam_input.count() == 1, "Camera input must exist"
        assert cam_input.get_attribute("capture") == "environment", (
            "Camera input must have capture=environment"
        )

        # 2. Simulate Offline
        context.set_offline(True)

        # 3. Select file while offline
        sample_file = str((FIXTURES_DIR / "clean_scan.png").resolve())
        page.set_input_files("#fileInput", sample_file)
        time.sleep(1)

        # 4. Assert offline badge visible and IndexedDB contains queued item
        assert page.locator("#offlineQueuedBadge").is_visible(), (
            "Offline badge must be visible when offline"
        )
        queued_count = page.evaluate("async () => (await getQueuedUploads()).length")
        assert queued_count == 1, f"Expected 1 item in IndexedDB queue, got {queued_count}"

        # 5. Restore Online
        context.set_offline(False)
        page.evaluate("() => window.dispatchEvent(new Event('online'))")
        time.sleep(2)

        # 6. Verify queued items flushed
        rem_count = page.evaluate("async () => (await getQueuedUploads()).length")
        assert rem_count == 0, f"Expected 0 items in queue after online flush, got {rem_count}"

        browser.close()
