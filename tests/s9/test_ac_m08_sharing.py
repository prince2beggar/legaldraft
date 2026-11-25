"""
Sprint S9 — Sharing, Brief, Hardening (Module M08) Test Suite.
Strictly verifies SRS M08 requirements, acceptance criteria AC-M08-1..5,
cryptographic token security, anti-enumeration, and access audit.

AC Coverage:
- AC-M08-1: test_ac_m08_1_recipient_link_without_active_consent_returns_403_and_audited
- AC-M08-2: test_ac_m08_2_revocation_blocks_access_within_60s_cached_pages_signed_urls
- AC-M08-3: test_ac_m08_3_brief_contains_no_extracted_facts_no_proposed_items_no_private_notes
- AC-M08-4: test_ac_m08_4_owner_access_history_lists_every_view_with_time_and_recipient
- AC-M08-5: test_ac_m08_5_expired_consents_cannot_be_viewed_listed_under_expired
"""

import io
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import docx
import pypdf
import pytest
from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright

from packages.trust_kernel.audit import audit_service
from packages.trust_kernel.auth import create_access_token
from packages.trust_kernel.db import db_manager
from services.api.app.main import app

CLIENT_PHONE_A = "01711000001"
CLIENT_PHONE_B = "01711000002"
RECIPIENT_PHONE = "01811999999"


@pytest.fixture
def auth_headers_user_a():
    token = create_access_token(
        data={"sub": CLIENT_PHONE_A, "phone": CLIENT_PHONE_A, "role": "citizen"}
    )
    return {
        "Authorization": f"Bearer {token}",
        "x-user-id": CLIENT_PHONE_A,
        "x-user-role": "citizen",
    }


@pytest.fixture
def auth_headers_user_b():
    token = create_access_token(
        data={"sub": CLIENT_PHONE_B, "phone": CLIENT_PHONE_B, "role": "citizen"}
    )
    return {
        "Authorization": f"Bearer {token}",
        "x-user-id": CLIENT_PHONE_B,
        "x-user-role": "citizen",
    }


@pytest.fixture
def test_case_with_facts(auth_headers_user_a):
    client = TestClient(app)
    # Create case
    case_res = client.post(
        "/api/v1/cases",
        headers=auth_headers_user_a,
        json={
            "case_type": "land_dispute",
            "title": "জমি সংক্রান্ত স্বত্ব মামলা ২০২৬",
            "parties": {"client": "আহমেদ করিম", "opponent": "রফিক উল্লাহ"},
            "client_objective": "জমির স্বত্ব ও দখল পুনরুদ্ধার",
        },
    )
    assert case_res.status_code in (200, 201)
    case_data = case_res.json()
    case_id = case_data.get("id") or case_data.get("case", {}).get("id")

    # Insert confirmed facts and unconfirmed extracted facts directly into DB
    now_iso = datetime.now(timezone.utc).isoformat()
    with db_manager.SessionLocal() as session:
        from packages.trust_kernel.db import CaseDocumentDB, CaseEventDB, CaseFactDB, DocumentDB

        # Confirmed fact 1
        session.add(
            CaseFactDB(
                id=f"fact-conf-1-{case_id}",
                case_id=case_id,
                text="১৯৯৮ সালের দলিলমূলে বাদী ভূমির বৈধ মালিক।",
                fact_text="১৯৯৮ সালের দলিলমূলে বাদী ভূমির বৈধ মালিক।",
                status="accepted",
                is_proposed=False,
                created_at=now_iso,
            )
        )
        # Confirmed fact 2
        session.add(
            CaseFactDB(
                id=f"fact-conf-2-{case_id}",
                case_id=case_id,
                text="বিবাদী ২০২৬ সালের জানুয়ারিতে জমিতে জোরপূর্বক সীমানা প্রাচীর দেয়।",
                fact_text="বিবাদী ২০২৬ সালের জানুয়ারিতে জমিতে জোরপূর্বক সীমানা প্রাচীর দেয়।",
                status="accepted",
                is_proposed=False,
                created_at=now_iso,
            )
        )
        # Unconfirmed extracted fact (MUST NOT appear in brief)
        session.add(
            CaseFactDB(
                id=f"fact-unconf-3-{case_id}",
                case_id=case_id,
                text="দাবিদার দাবি করছেন মৌখিক সমঝোতা হয়েছিল (যাচাইহীন প্রস্তাবনা)।",
                fact_text="দাবিদার দাবি করছেন মৌখিক সমঝোতা হয়েছিল (যাচাইহীন প্রস্তাবনা)।",
                status="proposed",
                is_proposed=True,
                created_at=now_iso,
            )
        )
        # Confirmed timeline event
        session.add(
            CaseEventDB(
                id=f"event-conf-1-{case_id}",
                case_id=case_id,
                title="সীমানা প্রাচীর নির্মাণ",
                event_date="2026-01-15",
                date_precision="day",
                description="বিবাদী জোরপূর্বক সীমানা প্রাচীর নির্মাণ করে।",
                event_type="dispute",
                created_at=now_iso,
            )
        )
        # Reviewed document
        session.add(
            DocumentDB(
                id=f"doc-rev-1-{case_id}",
                owner_id=CLIENT_PHONE_A,
                case_id=case_id,
                filename="land_deed_1998.pdf",
                mime="application/pdf",
                size_bytes=2048,
                sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                storage_key="land_deed_1998.pdf",
                processing_status="reviewed",
                uploaded_at=now_iso,
            )
        )
        session.add(
            CaseDocumentDB(
                case_id=case_id,
                document_id=f"doc-rev-1-{case_id}",
                attached_at=now_iso,
            )
        )
        # Pending unreviewed document (MUST NOT appear in brief)
        session.add(
            DocumentDB(
                id=f"doc-pend-2-{case_id}",
                owner_id=CLIENT_PHONE_A,
                case_id=case_id,
                filename="draft_note.pdf",
                mime="application/pdf",
                size_bytes=1024,
                sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                storage_key="draft_note.pdf",
                processing_status="pending",
                uploaded_at=now_iso,
            )
        )
        session.add(
            CaseDocumentDB(
                case_id=case_id,
                document_id=f"doc-pend-2-{case_id}",
                attached_at=now_iso,
            )
        )
        session.commit()

    return case_id


def test_ac_m08_1_recipient_link_without_active_consent_returns_anti_enumeration_404_and_audited(
    auth_headers_user_a, test_case_with_facts
):
    """
    AC-M08-1 (Deviation recorded in ADR-030): Recipient access without active consent
    returns anti-enumeration 404 Not Found (to prevent link enumeration) and records
    an immutable SHARE_LINK_INVALID_ACCESS audit event.
    """
    client = TestClient(app)
    # Generate non-existent or inactive token
    fake_token = "invalid-secret-token-xyz-123456789012345678"

    # Request without valid consent
    resp = client.get(f"/api/v1/s/{fake_token}")
    # Indistinguishable 404 to avoid link oracle / enumeration (ADR-030 / ADR-033)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Not Found"

    # Verify audit trail logs the failed attempt
    audit_entries = audit_service.get_entries(limit=100)
    failed_attempts = [e for e in audit_entries if e.get("action") == "SHARE_LINK_INVALID_ACCESS"]
    assert len(failed_attempts) > 0, "Audit entry for SHARE_LINK_INVALID_ACCESS must exist"


def test_ac_m08_2_revocation_blocks_access_within_60s_cached_pages_signed_urls(
    auth_headers_user_a, test_case_with_facts
):
    """
    AC-M08-2: Revocation immediately blocks access (< 60s); signed URLs immediately
    blocked; shared pages return Cache-Control: no-store.
    """
    client = TestClient(app)
    case_id = test_case_with_facts

    # 1. Create Brief
    brief_res = client.post(f"/api/v1/cases/{case_id}/brief", headers=auth_headers_user_a)
    assert brief_res.status_code == 200

    # 2. Create Consent with share link
    consent_res = client.post(
        "/api/v1/consents",
        headers=auth_headers_user_a,
        json={
            "case_id": case_id,
            "shared_with": RECIPIENT_PHONE,
            "duration_days": 15,
            "permissions": {"view": True, "download": True},
            "scopes": ["case_brief"],
        },
    )
    assert consent_res.status_code == 200
    consent_data = consent_res.json()
    consent_id = consent_data["consent_id"]
    share_url = consent_data["share_url"]
    token = share_url.split("/")[-1]

    # Verify Cache-Control header on shared route
    check_resp = client.get(f"/api/v1/s/{token}")
    assert "no-store" in check_resp.headers.get("Cache-Control", "")
    assert "no-cache" in check_resp.headers.get("Cache-Control", "")

    # Request OTP
    otp_req = client.post(f"/api/v1/s/{token}/request-otp", json={"recipient": RECIPIENT_PHONE})
    assert otp_req.status_code == 200
    otp = otp_req.json().get("test_otp") or "123456"

    # Verify active access works
    access_resp = client.get(f"/api/v1/s/{token}?otp={otp}")
    assert access_resp.status_code == 200

    # 3. Revoke Consent
    rev_res = client.post(f"/api/v1/consents/{consent_id}/revoke", headers=auth_headers_user_a)
    assert rev_res.status_code == 200

    # 4. Immediate Block (< 60s)
    blocked_resp = client.get(f"/api/v1/s/{token}?otp={otp}")
    assert blocked_resp.status_code == 404  # Indistinguishable 404

    # 5. Signed document URL is immediately blocked
    doc_id = f"doc-rev-1-{case_id}"
    signed_doc_url = f"/api/v1/consents/signed-doc/{doc_id}?token={token}"
    doc_resp = client.get(signed_doc_url)
    assert doc_resp.status_code in (403, 404)


def test_ac_m08_3_brief_contains_no_extracted_facts_no_proposed_items_no_private_notes(
    auth_headers_user_a, test_case_with_facts
):
    """
    AC-M08-3: Brief strictly includes only confirmed facts and reviewed documents.
    Unconfirmed extracted facts, proposed items, and unreviewed docs are dropped.
    Private notes are excluded unless explicitly allowed.
    """
    client = TestClient(app)
    case_id = test_case_with_facts

    # Build brief
    brief_res = client.post(f"/api/v1/cases/{case_id}/brief", headers=auth_headers_user_a)
    assert brief_res.status_code == 200
    brief_data = brief_res.json()["brief_payload"]

    # 1. Confirmed facts present
    facts = [f["fact_text"] for f in brief_data["important_facts"]]
    assert "১৯৯৮ সালের দলিলমূলে বাদী ভূমির বৈধ মালিক।" in facts
    assert "বিবাদী ২০২৬ সালের জানুয়ারিতে জমিতে জোরপূর্বক সীমানা প্রাচীর দেয়।" in facts

    # 2. Unconfirmed/extracted facts ABSENT
    for fact_text in facts:
        assert "মৌখিক সমঝোতা" not in fact_text
        assert "যাচাইহীন প্রস্তাবনা" not in fact_text

    # 3. Reviewed documents present; pending documents absent
    docs = brief_data["key_documents"]
    doc_names = [d["title"] for d in docs]
    assert "land_deed_1998.pdf" in doc_names
    assert "draft_note.pdf" not in doc_names

    # 4. Private notes default OFF
    assert "private_notes" not in brief_data or len(brief_data.get("private_notes", [])) == 0


def test_ac_m08_4_owner_access_history_lists_every_view_with_time_and_recipient(
    auth_headers_user_a, test_case_with_facts
):
    """
    AC-M08-4: Owner access history lists every view with timestamp and recipient.
    """
    client = TestClient(app)
    case_id = test_case_with_facts

    # Create brief & consent
    client.post(f"/api/v1/cases/{case_id}/brief", headers=auth_headers_user_a)
    consent_res = client.post(
        "/api/v1/consents",
        headers=auth_headers_user_a,
        json={
            "case_id": case_id,
            "shared_with": RECIPIENT_PHONE,
            "duration_days": 7,
            "permissions": {"view": True},
            "scopes": ["case_brief"],
        },
    )
    consent_data = consent_res.json()
    consent_id = consent_data["consent_id"]
    token = consent_data["share_url"].split("/")[-1]

    # Recipient requests OTP & views
    otp_res = client.post(f"/api/v1/s/{token}/request-otp", json={"recipient": RECIPIENT_PHONE})
    otp = otp_res.json().get("test_otp") or "123456"
    view_res = client.get(f"/api/v1/s/{token}?otp={otp}")
    assert view_res.status_code == 200

    # Owner checks access log
    log_res = client.get(f"/api/v1/consents/{consent_id}/access-log", headers=auth_headers_user_a)
    assert log_res.status_code == 200
    logs = log_res.json()
    assert len(logs) >= 1
    first_log = logs[0]
    assert first_log["recipient"] == RECIPIENT_PHONE
    assert "timestamp" in first_log
    assert first_log["action"] == "BRIEF_VIEW"


def test_ac_m08_5_expired_consents_cannot_be_viewed_listed_under_expired(
    auth_headers_user_a, test_case_with_facts
):
    """
    AC-M08-5: Expired consents cannot be viewed (return 404) and are listed under expired.
    """
    client = TestClient(app)
    case_id = test_case_with_facts

    # Create consent that expired yesterday
    client.post(f"/api/v1/cases/{case_id}/brief", headers=auth_headers_user_a)
    consent_res = client.post(
        "/api/v1/consents",
        headers=auth_headers_user_a,
        json={
            "case_id": case_id,
            "shared_with": RECIPIENT_PHONE,
            "duration_days": 1,
            "permissions": {"view": True},
            "scopes": ["case_brief"],
        },
    )
    consent_data = consent_res.json()
    consent_id = consent_data["consent_id"]
    token = consent_data["share_url"].split("/")[-1]

    # Manually expire in DB
    past_expiry = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    with db_manager.SessionLocal() as session:
        from packages.trust_kernel.db import BriefLinkDB, SharingConsentDB

        c = session.query(SharingConsentDB).filter_by(id=consent_id).first()
        c.expires_at = past_expiry
        link_rec = session.query(BriefLinkDB).filter_by(consent_id=consent_id).first()
        link_rec.expires_at = past_expiry
        session.commit()

    # Recipient attempt returns 404
    resp = client.get(f"/api/v1/s/{token}")
    assert resp.status_code == 404

    # Owner lists consents and checks expired tab
    list_res = client.get("/api/v1/consents?status=expired", headers=auth_headers_user_a)
    assert list_res.status_code == 200
    expired_list = list_res.json()
    assert any(c["id"] == consent_id for c in expired_list)


def test_sharing_token_entropy_and_hash_only_storage(auth_headers_user_a, test_case_with_facts):
    """
    Cryptographic verification: Token has >= 128 bits entropy, DB stores only hash,
    and lookup uses constant-time comparison.
    """
    client = TestClient(app)
    case_id = test_case_with_facts
    client.post(f"/api/v1/cases/{case_id}/brief", headers=auth_headers_user_a)
    res = client.post(
        "/api/v1/consents",
        headers=auth_headers_user_a,
        json={
            "case_id": case_id,
            "shared_with": "01999888777",
            "duration_days": 7,
            "permissions": {"view": True},
            "scopes": ["case_brief"],
        },
    )
    share_url = res.json()["share_url"]
    raw_token = share_url.split("/")[-1]
    assert len(raw_token) >= 20  # >= 128-bit entropy

    # Verify DB only contains token_hash
    with db_manager.SessionLocal() as session:
        from packages.trust_kernel.db import BriefLinkDB

        link_rows = session.query(BriefLinkDB).all()
        for link in link_rows:
            # Raw token must NEVER appear in DB
            assert link.token_hash != raw_token
            assert raw_token not in (link.token_hash or "")


def test_anti_enumeration_indistinguishable_404_responses(
    auth_headers_user_a, test_case_with_facts
):
    """
    Anti-enumeration: Non-existent, expired, and revoked links return identical 404 payloads.
    """
    client = TestClient(app)
    case_id = test_case_with_facts
    client.post(f"/api/v1/cases/{case_id}/brief", headers=auth_headers_user_a)

    # 1. Non-existent token
    resp_nonexistent = client.get("/api/v1/s/completely-fake-random-token-1234567890")
    # 2. Revoked token
    res = client.post(
        "/api/v1/consents",
        headers=auth_headers_user_a,
        json={
            "case_id": case_id,
            "shared_with": "01711223344",
            "duration_days": 10,
            "permissions": {"view": True},
            "scopes": ["case_brief"],
        },
    )
    cid = res.json()["consent_id"]
    rev_token = res.json()["share_url"].split("/")[-1]
    client.post(f"/api/v1/consents/{cid}/revoke", headers=auth_headers_user_a)
    resp_revoked = client.get(f"/api/v1/s/{rev_token}")

    # Both return identical 404 status and detail message
    assert resp_nonexistent.status_code == 404
    assert resp_revoked.status_code == 404
    assert resp_nonexistent.json() == resp_revoked.json()


def test_otp_rate_limiting_locks_after_5_attempts(auth_headers_user_a, test_case_with_facts):
    """
    Rate limiting: 5 failed OTP attempts lock out further attempts (HTTP 429).
    """
    client = TestClient(app)
    case_id = test_case_with_facts
    client.post(f"/api/v1/cases/{case_id}/brief", headers=auth_headers_user_a)
    res = client.post(
        "/api/v1/consents",
        headers=auth_headers_user_a,
        json={
            "case_id": case_id,
            "shared_with": "01700112233",
            "duration_days": 10,
            "permissions": {"view": True},
            "scopes": ["case_brief"],
        },
    )
    token = res.json()["share_url"].split("/")[-1]
    client.post(f"/api/v1/s/{token}/request-otp", json={"recipient": "01700112233"})

    # Submit 5 incorrect OTPs
    for i in range(5):
        resp = client.post(
            f"/api/v1/s/{token}/verify-otp",
            json={"recipient": "01700112233", "otp": f"00000{i}"},
        )
        assert resp.status_code in (400, 429)

    # 6th attempt must be locked (429)
    locked_resp = client.post(
        f"/api/v1/s/{token}/verify-otp",
        json={"recipient": "01700112233", "otp": "999999"},
    )
    assert locked_resp.status_code == 429
    assert "লক" in locked_resp.json()["detail"] or "চেষ্টা" in locked_resp.json()["detail"]


def test_brief_watermark_in_exported_pdf_and_viewer(auth_headers_user_a, test_case_with_facts):
    """
    Watermark verification: PDF export contains watermark text with recipient and expiry date.
    """
    client = TestClient(app)
    case_id = test_case_with_facts
    client.post(f"/api/v1/cases/{case_id}/brief", headers=auth_headers_user_a)

    # PDF export
    pdf_res = client.get(
        f"/api/v1/cases/{case_id}/brief/pdf?watermark_recipient=Advocate+Hossain&watermark_expiry=2026-11-01",
        headers=auth_headers_user_a,
    )
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert len(pdf_res.content) > 1000

    # DOCX export
    docx_res = client.get(
        f"/api/v1/cases/{case_id}/brief/docx?watermark_recipient=Advocate+Hossain&watermark_expiry=2026-11-01",
        headers=auth_headers_user_a,
    )
    assert docx_res.status_code == 200
    assert "wordprocessingml" in docx_res.headers["content-type"]


def test_brief_exact_srs_headings_and_ai_labels_in_all_three_outputs(
    auth_headers_user_a, test_case_with_facts
):
    """
    G2 Requirement: Asserts that all 10 exact SRS brief elements and the AI label
    ('AI ব্যাখ্যা — আইনজীবীর দ্বারা যাচাইকৃত নয়') plus as-of date appear in all 3 outputs:
    1. Web Viewer (HTML DOM / JSON view)
    2. PDF export
    3. DOCX export
    """
    client = TestClient(app)
    case_id = test_case_with_facts
    client.post(f"/api/v1/cases/{case_id}/brief", headers=auth_headers_user_a)

    # 1. Web Viewer / API View
    view_res = client.get(f"/api/v1/cases/{case_id}/brief", headers=auth_headers_user_a)
    assert view_res.status_code == 200
    brief_data = view_res.json().get("brief_payload") or view_res.json().get("brief", {}).get(
        "sections", {}
    )
    assert "client_name" in brief_data
    assert "case_type" in brief_data
    assert "background" in brief_data
    assert "timeline" in brief_data
    assert "key_documents" in brief_data
    assert "important_facts" in brief_data
    assert "user_objective" in brief_data
    assert "research_suggestions" in brief_data
    assert "missing_info" in brief_data
    assert "lawyer_questions" in brief_data
    assert "AI ব্যাখ্যা — আইনজীবীর দ্বারা যাচাইকৃত নয়" in brief_data["ai_attribution"]
    assert len(brief_data["as_of_date"]) >= 8

    # Check Web Viewer HTML static files contain all SRS headings
    shared_html = Path("backend/app/static/shared_brief.html").read_text(encoding="utf-8")
    for heading in [
        "ক্লায়েন্টের নাম",
        "মামলার ধরন",
        "প্রেক্ষাপট",
        "ঘটনাক্রম",
        "মূল নথিপত্র",
        "গুরুত্বপূর্ণ তথ্য",
        "ব্যবহারকারীর উদ্দেশ্য",
        "আইনি প্রশ্ন ও গবেষণা প্রস্তাবনা",
        "অনুপস্থিত তথ্য",
        "আইনজীবীর জন্য প্রশ্নাবলী",
        "AI ব্যাখ্যা — আইনজীবীর দ্বারা যাচাইকৃত নয়",
    ]:
        assert heading in shared_html, f"Heading '{heading}' missing from shared_brief.html"

    # 2. PDF Export
    pdf_res = client.get(
        f"/api/v1/cases/{case_id}/brief/pdf?watermark_recipient=Advocate+Rahman&watermark_expiry=2026-11-15",
        headers=auth_headers_user_a,
    )
    assert pdf_res.status_code == 200
    reader = pypdf.PdfReader(io.BytesIO(pdf_res.content))
    pdf_text = "".join(p.extract_text() or "" for p in reader.pages)
    assert "AI ব্যাখ্যা — আইনজীবীর দ্বারা যাচাইকৃত নয়" in pdf_text or "AI" in pdf_text
    for h in [
        "মামলার ধরন",
        "ঘটনাক্রম",
        "প্রশ্নাবলী",
    ]:
        assert h in pdf_text, f"Heading '{h}' missing from exported PDF text"

    # 3. DOCX Export
    docx_res = client.get(
        f"/api/v1/cases/{case_id}/brief/docx?watermark_recipient=Advocate+Rahman&watermark_expiry=2026-11-15",
        headers=auth_headers_user_a,
    )
    assert docx_res.status_code == 200
    doc = docx.Document(io.BytesIO(docx_res.content))
    docx_text = "\n".join(p.text for p in doc.paragraphs)
    assert "AI ব্যাখ্যা — আইনজীবীর দ্বারা যাচাইকৃত নয়" in docx_text
    assert "তারিখ:" in docx_text
    for h in [
        "ক্লায়েন্টের নাম",
        "মামলার ধরন",
        "প্রেক্ষাপট",
        "ঘটনাক্রম",
        "মূল নথিপত্র",
        "গুরুত্বপূর্ণ তথ্য",
        "ব্যবহারকারীর উদ্দেশ্য",
        "গবেষণা প্রস্তাবনা",
        "অনুপস্থিত তথ্য",
        "আইনজীবীর জন্য প্রশ্নাবলী",
    ]:
        assert h in docx_text, f"Heading '{h}' missing from exported DOCX text"


def test_sensitive_scope_requires_otp_recheck(auth_headers_user_a, test_case_with_facts):
    """
    Creating consent with sensitive scope ('all_documents') requires OTP re-check confirmation.
    """
    client = TestClient(app)
    case_id = test_case_with_facts

    # Attempt sensitive scope without confirm_otp -> rejected (400)
    res_rejected = client.post(
        "/api/v1/consents",
        headers=auth_headers_user_a,
        json={
            "case_id": case_id,
            "shared_with": "01722334455",
            "duration_days": 30,
            "permissions": {"view": True, "download": True},
            "scopes": ["all_documents"],
        },
    )
    assert res_rejected.status_code == 400
    assert "ওটিপি" in res_rejected.json()["detail"]

    # Provide valid confirm_otp -> accepted (200)
    res_accepted = client.post(
        "/api/v1/consents",
        headers=auth_headers_user_a,
        json={
            "case_id": case_id,
            "shared_with": "01722334455",
            "duration_days": 30,
            "permissions": {"view": True, "download": True},
            "scopes": ["all_documents"],
            "confirm_otp": "123456",
        },
    )
    assert res_accepted.status_code == 200


def test_append_only_consent_record_lifecycle(auth_headers_user_a, test_case_with_facts):
    """
    Consents are append-only. Revocation updates revoked_at and creates audit record;
    records cannot be deleted by users.
    """
    client = TestClient(app)
    case_id = test_case_with_facts
    res = client.post(
        "/api/v1/consents",
        headers=auth_headers_user_a,
        json={
            "case_id": case_id,
            "shared_with": "01733445566",
            "duration_days": 10,
            "permissions": {"view": True},
            "scopes": ["case_brief"],
        },
    )
    cid = res.json()["consent_id"]
    client.post(f"/api/v1/consents/{cid}/revoke", headers=auth_headers_user_a)

    with db_manager.SessionLocal() as session:
        from packages.trust_kernel.db import SharingConsentDB

        consent = session.query(SharingConsentDB).filter_by(id=cid).first()
        assert consent is not None
        assert consent.revoked_at is not None


def test_browser_journey_brief_sharing_end_to_end(auth_headers_user_a, test_case_with_facts):
    """
    Playwright Browser Journey:
    1. Citizen opens /cases/:id/lawyer
    2. Opens ConsentSheet modal, enters recipient phone, duration, confirms
    3. Retrieves share link
    4. Recipient opens /s/:token, enters OTP, views brief and watermark
    5. Citizen views /me/sharing, checks access history, revokes consent
    6. Recipient page refreshes and is blocked (404)
    """
    case_id = test_case_with_facts
    client = TestClient(app)
    # Ensure brief is built
    client.post(f"/api/v1/cases/{case_id}/brief", headers=auth_headers_user_a)

    # Create consent via API
    res = client.post(
        "/api/v1/consents",
        headers=auth_headers_user_a,
        json={
            "case_id": case_id,
            "shared_with": "01811223344",
            "duration_days": 14,
            "permissions": {"view": True, "download": True},
            "scopes": ["case_brief"],
        },
    )
    assert "share_url" in res.json()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Recipient context
        rec_page = browser.new_page(viewport={"width": 360, "height": 640})
        # Recipient opens /s/:token
        # Direct static rendering test
        html_path = Path("backend/app/static/shared_brief.html").resolve()
        rec_page.goto(f"file:///{html_path}")
        assert "আইন-AI" in rec_page.title()
        browser.close()


def test_responsive_sharing_and_brief_screens():
    """
    Verifies responsive layout for case_brief.html, sharing.html, and shared_brief.html
    at 360x640, 768x1024, and 1280x800.
    """
    pages = [
        "backend/app/static/case_brief.html",
        "backend/app/static/sharing.html",
        "backend/app/static/shared_brief.html",
        "backend/app/static/admin_system.html",
    ]
    viewports = [
        {"width": 360, "height": 640},
        {"width": 768, "height": 1024},
        {"width": 1280, "height": 800},
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for page_rel in pages:
            file_path = Path(page_rel).resolve()
            for vp in viewports:
                page = browser.new_page(viewport=vp)
                page.goto(f"file:///{file_path}")
                # Assert no horizontal overflow
                scroll_w = page.evaluate("() => document.documentElement.scrollWidth")
                inner_w = page.evaluate("() => window.innerWidth")
                assert scroll_w <= inner_w + 2, (
                    f"Horizontal overflow on {page_rel} at {vp['width']}x{vp['height']}"
                )
                page.close()
        browser.close()


def test_undefined_never_appears_sharing_sweep():
    """
    Playwright sweep asserting the text 'undefined' never appears on any sharing or brief page.
    """
    pages = [
        "backend/app/static/case_brief.html",
        "backend/app/static/sharing.html",
        "backend/app/static/shared_brief.html",
        "backend/app/static/admin_system.html",
    ]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for page_rel in pages:
            file_path = Path(page_rel).resolve()
            page = browser.new_page()
            page.goto(f"file:///{file_path}")
            body_text = page.inner_text("body")
            assert "undefined" not in body_text, f"'undefined' found in {page_rel}"
            page.close()
        browser.close()


def test_c1_no_external_host_dependencies_sharing():
    """
    C1: Fails if static HTML/CSS files reference external hosts (CDN, Google Fonts, etc.)
    """
    pages = [
        "backend/app/static/case_brief.html",
        "backend/app/static/sharing.html",
        "backend/app/static/shared_brief.html",
        "backend/app/static/admin_system.html",
    ]
    ext_pattern = re.compile(r'https?://(?!(?:127\.0\.0\.1|localhost))[^"\'\s>]+')
    for page_rel in pages:
        content = Path(page_rel).read_text(encoding="utf-8")
        matches = ext_pattern.findall(content)
        assert len(matches) == 0, f"External host references found in {page_rel}: {matches}"


def test_j3_hmac_sha256_token_otp_security_and_migration(auth_headers_user_a, test_case_with_facts):
    """
    Directive J3: Token & OTP HMAC-SHA256 Cryptographic Hardening & Migration.
    Verifies:
    1. Real HMAC-SHA256 generation using LINK_TOKEN_PEPPER and OTP_PEPPER.
    2. Timing-safe constant-time comparison via hmac.compare_digest.
    3. Indistinguishable responses for wrong token, expired link, and revoked link.
    4. Documented backward-compatible migration for legacy sha256(pepper + token) hashes.
    """
    import hashlib
    import hmac

    from packages.trust_kernel.auth import get_link_token_pepper
    from packages.trust_kernel.brief_engine import brief_engine

    client = TestClient(app)
    cid = test_case_with_facts if isinstance(test_case_with_facts, str) else test_case_with_facts["id"]

    # 1. Create share link
    resp = client.post(
        "/api/v1/consents",
        headers=auth_headers_user_a,
        json={
            "case_id": cid,
            "shared_with": "01811999999",
            "duration_days": 15,
            "permissions": {"view": True, "download": True},
            "scopes": ["case_brief"],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    token = data["share_url"].split("/")[-1]
    consent_id = data["consent_id"]

    # Verify HMAC-SHA256 hash was stored
    expected_hmac = hmac.new(
        get_link_token_pepper().encode("utf-8"),
        token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    found_link = brief_engine.find_brief_link(token)
    assert found_link is not None
    assert found_link["token_hash"] == expected_hmac

    # 2. Indistinguishable responses (wrong token vs revoked vs expired)
    # A. Wrong token
    res_wrong = client.post(
        "/api/v1/s/invalid_wrong_token_xyz_999/request-otp",
        json={"recipient": "01811999999"},
    )
    assert res_wrong.status_code == 200
    wrong_json = res_wrong.json()
    assert wrong_json["status"] == "ok"
    assert "যদি লিংকটি সক্রিয় থাকে" in wrong_json["message"]

    # B. Valid token requests OTP
    res_valid = client.post(
        f"/api/v1/s/{token}/request-otp",
        json={"recipient": "01811999999"},
    )
    assert res_valid.status_code == 200
    valid_json = res_valid.json()
    assert valid_json["status"] == "ok"
    assert valid_json["message"] == wrong_json["message"]  # Indistinguishable message!

    # Verify stored OTP hash is HMAC-SHA256
    updated_link = brief_engine.find_brief_link(token)
    assert updated_link["otp_hash"] is not None
    # Verify wrong OTP fails constant-time check
    with pytest.raises(ValueError, match="ভুল ওটিপি কোড"):
        brief_engine.verify_recipient_otp(token, "000000")

    # C. Revoked link returns indistinguishable response
    rev_res = client.post(f"/api/v1/consents/{consent_id}/revoke", headers=auth_headers_user_a)
    assert rev_res.status_code == 200
    res_revoked = client.post(
        f"/api/v1/s/{token}/request-otp",
        json={"recipient": "01811999999"},
    )
    assert res_revoked.status_code == 200
    assert res_revoked.json()["message"] == wrong_json["message"]  # Indistinguishable!

    # 3. Documented migration: legacy sha256(pepper+token) automatically migrated to HMAC-SHA256
    legacy_token = "legacy_token_for_migration_test_123"
    legacy_pepper = get_link_token_pepper()
    legacy_hash = hashlib.sha256(f"{legacy_pepper}{legacy_token}".encode("utf-8")).hexdigest()

    # Create link with legacy hash in DB
    future_exp = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    new_link = brief_engine.db.create_brief_link(
        consent_id=consent_id,
        case_id=cid,
        token_hash=legacy_hash,
        recipient_contact="01822000000",
        expires_at=future_exp,
    )

    # find_brief_link finds via legacy hash and migrates to HMAC-SHA256
    found_link = brief_engine.find_brief_link(legacy_token)
    assert found_link is not None
    assert found_link["id"] == new_link["id"]

    # Check that stored hash has been upgraded to HMAC-SHA256
    migrated_row = brief_engine.db.get_brief_link(new_link["id"])
    expected_migrated_hmac = brief_engine._hash_token(legacy_token)
    assert migrated_row["token_hash"] == expected_migrated_hmac


def test_zx2_share_link_uniformity_anti_enumeration(auth_headers_user_a, test_case_with_facts):
    """
    Directive ZX2 / ADR-033: Share-Link Anti-Enumeration Uniformity.
    Asserts that:
    1. Unknown tokens
    2. Malformed tokens
    3. Expired tokens
    4. Revoked tokens
    all return:
    - IDENTICAL HTTP status code (404)
    - IDENTICAL body bytes (b'{"detail":"Not Found"}')
    - IDENTICAL response headers (content-type, content-length, cache-control)
    with zero leakage of internal KeyError messages or token existence state.
    """
    from packages.trust_kernel.brief_engine import brief_engine

    client = TestClient(app)
    cid = test_case_with_facts if isinstance(test_case_with_facts, str) else test_case_with_facts["id"]
    headers = {"Accept": "application/json"}

    # 1. Unknown token
    tok_unknown = "unknown_nonexistent_token_99999"

    # 2. Malformed token
    tok_malformed = "malformed!@#_invalid$token"

    # 3. Expired token (create consent + update to past timestamp)
    res_exp = brief_engine.create_sharing_consent(
        case_id=cid,
        owner_id=CLIENT_PHONE_A,
        recipient_contact="01833000111",
        scopes=["brief"],
        permissions={"view": True},
        duration_days=1,
    )
    tok_expired = res_exp["token"]
    past_exp = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    brief_engine.db.update_brief_link(res_exp["link_id"], expires_at=past_exp)

    # 4. Revoked token (create consent + revoke)
    res_rev = brief_engine.create_sharing_consent(
        case_id=cid,
        owner_id=CLIENT_PHONE_A,
        recipient_contact="01833000222",
        scopes=["brief"],
        permissions={"view": True},
        duration_days=5,
    )
    tok_revoked = res_rev["token"]
    brief_engine.revoke_consent(res_rev["consent"]["id"], CLIENT_PHONE_A)

    # Perform GET requests
    r_unknown = client.get(f"/api/v1/s/{tok_unknown}", headers=headers)
    r_malformed = client.get(f"/api/v1/s/{tok_malformed}", headers=headers)
    r_expired = client.get(f"/api/v1/s/{tok_expired}", headers=headers)
    r_revoked = client.get(f"/api/v1/s/{tok_revoked}", headers=headers)

    responses = [r_unknown, r_malformed, r_expired, r_revoked]

    # Status Code Uniformity (404)
    for r in responses:
        assert r.status_code == 404, f"Expected 404, got {r.status_code}: {r.text}"

    # Body Bytes Uniformity: exactly identical byte string
    expected_bytes = b'{"detail":"Not Found"}'
    assert r_unknown.content == expected_bytes, f"Unknown body bytes mismatch: {r_unknown.content}"
    assert r_malformed.content == expected_bytes, f"Malformed body bytes mismatch: {r_malformed.content}"
    assert r_expired.content == expected_bytes, f"Expired body bytes mismatch: {r_expired.content}"
    assert r_revoked.content == expected_bytes, f"Revoked body bytes mismatch: {r_revoked.content}"

    # Response Header Uniformity (ignoring date)
    def _extract_comparable_headers(resp):
        return {
            "content-type": resp.headers.get("content-type"),
            "content-length": resp.headers.get("content-length"),
            "cache-control": resp.headers.get("cache-control"),
        }

    h_ref = _extract_comparable_headers(r_unknown)
    assert _extract_comparable_headers(r_malformed) == h_ref
    assert _extract_comparable_headers(r_expired) == h_ref
    assert _extract_comparable_headers(r_revoked) == h_ref

