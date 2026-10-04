"""
Sprint S2 Verification Test Suite (SRS Section 5.9, 5.10, 9.3 S2).
Test ACs:
- AC-M09-1: Search with as_of date never returns a version not in effect on that date.
- AC-M09-2: Only approved versions are searchable by citizens.
- AC-M09-3: Each result displays its rights badge; unlicensed items show a link only (no text).
- AC-M09-4: The explanation view always shows the AI label, source chip and as-of date.
- AC-M10-1: A source version cannot be approved by its uploader.
- AC-M10-2: Approving version N+1 sets version N's effective_to (or blocks on overlap), with diff view.
- AC-M10-3: Unapproved content is invisible to all citizen endpoints (API test).
- AC-M10-6: Ingestion completes asynchronously with per-step status and retry.
"""

import pytest
from fastapi.testclient import TestClient

from packages.trust_kernel.auth import auth_service
from packages.trust_kernel.db import db_manager
from packages.trust_kernel.retrieval import DeterministicEmbedder, retrieval_service
from packages.trust_kernel.source_registry import source_registry
from services.api.app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_database():
    db_manager.clear_all_data()
    auth_service.clear()
    from packages.trust_kernel.audit import audit_service
    audit_service.clear()
    yield
    db_manager.clear_all_data()
    auth_service.clear()
    audit_service.clear()


def _get_auth_headers(phone: str = "01711000001", role: str = "citizen") -> dict[str, str]:
    session = auth_service.request_otp(phone)
    res = auth_service.verify_otp(phone, session["dev_otp"])
    user_id = res["user"]["id"]
    if role != "citizen":
        user = auth_service.get_user(user_id)
        if user:
            user["role"] = role
            user["roles"] = [role, "citizen"]
            db_manager.save_user(user)
    token = res["access_token"]
    return {"Authorization": f"Bearer {token}", "x-user-id": user_id, "x-user-role": role}


def test_ac_m09_1_as_of_date_filtering():
    """
    AC-M09-1: Search with as_of=YYYY-MM-DD never returns a version not in effect on that date.
    """
    # Create fake statute
    source_id = source_registry.create_source(
        {
            "title": "Tenancy Regulation Act (Fake Test Data)",
            "title_bn": "বাড়িভাড়া নিয়ন্ত্রণ আইন (পরীক্ষামূলক ডেটা)",
            "source_type": "statute",
            "authority": "Parliament of Bangladesh",
            "rights": "official",
            "source_label": "FAKE_TEST_DATA",
        }
    )

    # Version 1: 1991-01-01 to 2019-12-31
    v1_id = source_registry.add_version(
        source_id=source_id,
        file_content="Section 1: Initial standard rent rules under 1991 Act.",
        effective_from="1991-01-01",
        effective_to="2019-12-31",
        version_label="1991 Original",
        uploader_id="usr-uploader",
    )
    source_registry.approve(v1_id, reviewer_id="usr-reviewer-1")

    # Version 2: 2020-01-01 to None
    v2_id = source_registry.add_version(
        source_id=source_id,
        file_content="Section 1: Modernized fair rent and digital receipts under 2020 Amendment.",
        effective_from="2020-01-01",
        effective_to=None,
        version_label="2020 Amendment",
        uploader_id="usr-uploader",
    )
    source_registry.approve(v2_id, reviewer_id="usr-reviewer-2")

    # Query 1: As-of 2015-06-01 -> MUST return Version 1 only
    results_2015 = retrieval_service.search("rent", as_of_date="2015-06-01")
    assert len(results_2015) > 0
    assert all(r["version_label"] == "1991 Original" for r in results_2015)
    assert not any(r["version_label"] == "2020 Amendment" for r in results_2015)

    # Query 2: As-of 2022-01-01 -> MUST return Version 2 only
    results_2022 = retrieval_service.search("rent", as_of_date="2022-01-01")
    assert len(results_2022) > 0
    assert all(r["version_label"] == "2020 Amendment" for r in results_2022)
    assert not any(r["version_label"] == "1991 Original" for r in results_2022)

    # Query 3: As-of 1800-01-01 (before law existed) -> MUST return empty
    results_1800 = retrieval_service.search("rent", as_of_date="1800-01-01")
    assert len(results_1800) == 0


def test_ac_m09_2_only_approved_versions_searchable():
    """
    AC-M09-2: Only 'approved' versions are searchable by citizens.
    Draft, review_pending, and rejected versions must NEVER be returned.
    """
    source_id = source_registry.create_source(
        {
            "title": "Draft Cyber Safety Act (Fake Test Data)",
            "source_type": "statute",
            "source_label": "FAKE_TEST_DATA",
        }
    )

    # Version in draft / review_pending status
    v_draft_id = source_registry.add_version(
        source_id=source_id,
        file_content="Section 1: Unapproved cyber surveillance rules.",
        effective_from="2026-01-01",
        version_label="Draft 0.1",
        uploader_id="usr-uploader",
    )
    # Check that status is review_pending (or draft)
    v_draft = db_manager.get_source_version(v_draft_id)
    assert v_draft["status"] == "review_pending"

    # Search should NOT return this unapproved version
    results = retrieval_service.search("cyber", as_of_date="2026-10-02")
    assert len(results) == 0

    # Reject version
    source_registry.reject(v_draft_id, reviewer_id="usr-reviewer", notes="Flawed draft")
    results_rejected = retrieval_service.search("cyber", as_of_date="2026-10-02")
    assert len(results_rejected) == 0

    # Now approve it
    source_registry.approve(v_draft_id, reviewer_id="usr-reviewer-2")
    results_approved = retrieval_service.search("cyber", as_of_date="2026-10-02")
    assert len(results_approved) == 1
    assert results_approved[0]["source_version_id"] == v_draft_id


def test_ac_m09_3_rights_badge_and_unlicensed_restriction():
    """
    AC-M09-3: Each result displays its rights badge; unlicensed items show a link only (no text).
    """
    headers = _get_auth_headers(phone="01711000002", role="citizen")

    # 1. Official source
    src_official = source_registry.create_source(
        {
            "title": "Official Labour Act (Fake Test Data)",
            "source_type": "statute",
            "rights": "official",
            "source_label": "FAKE_TEST_DATA",
        }
    )
    v_off = source_registry.add_version(
        source_id=src_official,
        file_content="Section 1: Official workers minimum wage standards.",
        effective_from="2020-01-01",
        uploader_id="uploader-1",
    )
    source_registry.approve(v_off, reviewer_id="reviewer-1")

    # 2. Unlicensed third-party commentary
    src_unlicensed = source_registry.create_source(
        {
            "title": "Commercial Commentary on Labour (Fake Test Data)",
            "source_type": "judgment",
            "rights": "unlicensed",
            "url": "https://bdlaws.example.com/commentary",
            "source_label": "FAKE_TEST_DATA",
        }
    )
    v_unlic = source_registry.add_version(
        source_id=src_unlicensed,
        file_content="Section 1: Proprietary proprietary copyrighted commentary text.",
        effective_from="2020-01-01",
        uploader_id="uploader-1",
    )
    source_registry.approve(v_unlic, reviewer_id="reviewer-1")

    # Search via API
    res = client.get("/api/v1/library/search?q=Labour&as_of=2026-10-02", headers=headers)
    assert res.status_code == 200
    data = res.json()["results"]
    assert len(data) == 2

    # Check official result
    off_item = next(r for r in data if r["source_id"] == src_official)
    assert off_item["rights"] == "official"
    assert "Official workers minimum wage" in off_item["text"]

    # Check unlicensed result
    unlic_item = next(r for r in data if r["source_id"] == src_unlicensed)
    assert unlic_item["rights"] == "unlicensed"
    assert "Text unavailable due to licensing" in unlic_item["text"]
    assert unlic_item["url"] == "https://bdlaws.example.com/commentary"


def test_ac_m09_4_explain_view_labels():
    """
    AC-M09-4: The explanation view always shows the AI label, source chip and as-of date.
    """
    headers = _get_auth_headers(phone="01711000003", role="citizen")

    src_id = source_registry.create_source(
        {
            "title": "Contract Act (Fake Test Data)",
            "source_type": "statute",
        }
    )
    v_id = source_registry.add_version(
        source_id=src_id,
        file_content="Section 73: Compensation for loss or damage caused by breach of contract.",
        effective_from="2000-01-01",
        uploader_id="uploader-1",
    )
    source_registry.approve(v_id, reviewer_id="reviewer-1")

    passages = db_manager.get_source_passages(v_id)
    assert len(passages) > 0
    pas_id = passages[0]["id"]

    res = client.post(
        f"/api/v1/library/passages/{pas_id}/explain",
        json={"as_of_date": "2026-10-02"},
        headers=headers,
    )
    assert res.status_code == 200
    body = res.json()

    assert "ai_label" in body
    assert "STATIC_PLACEHOLDER_NO_AI" in body["ai_label"]
    assert body["is_ai_generated"] is False
    assert "Contract Act" in body["source_chip"]
    assert body["as_of_date"] == "2026-10-02"
    assert "DRAFT_NOT_REVIEWED" in body["plain_explanation_bn"]
    assert "what_not_said" in body


def test_ac_m10_1_approver_cannot_be_uploader():
    """
    AC-M10-1: A source version cannot be approved by its uploader.
    """
    admin_headers = _get_auth_headers(phone="01711000004", role="admin")
    uploader_id = admin_headers["x-user-id"]

    src_id = source_registry.create_source(
        {
            "title": "Evidence Ordinance (Fake Test Data)",
            "source_type": "statute",
        }
    )

    # Uploader uploads version
    res_upload = client.post(
        f"/api/v1/admin/sources/{src_id}/versions/upload",
        json={
            "version_label": "1.0",
            "effective_from": "2024-01-01",
            "content": "Section 1: Burden of proof in civil and criminal disputes.",
        },
        headers=admin_headers,
    )
    assert res_upload.status_code == 202
    v_id = res_upload.json()["version_id"]

    # 1. Uploader attempts to self-approve -> MUST fail with 403 Forbidden
    res_self_approve = client.post(
        f"/api/v1/admin/sources/versions/{v_id}/review",
        json={"decision": "approve", "approval_notes": "Self approved"},
        headers=admin_headers,
    )
    assert res_self_approve.status_code == 403
    assert "cannot be approved by its uploader" in res_self_approve.json()["detail"]

    # Direct service layer check
    with pytest.raises(PermissionError, match="AC-M10-1"):
        source_registry.approve(v_id, reviewer_id=uploader_id)

    # 2. Different user with reviewer role approves -> MUST succeed
    reviewer_headers = _get_auth_headers(phone="01711000005", role="reviewer")
    res_other_approve = client.post(
        f"/api/v1/admin/sources/versions/{v_id}/review",
        json={"decision": "approve", "approval_notes": "Reviewed and verified."},
        headers=reviewer_headers,
    )
    assert res_other_approve.status_code == 200
    assert res_other_approve.json()["status"] == "approved"


def test_ac_m10_2_version_supersede_diff_and_overlap_block():
    """
    AC-M10-2: Approving version N+1 with effective_from sets version N's effective_to
    (or blocks on overlap) and retrieval respects both. Diff view compares versions.
    """
    reviewer_headers = _get_auth_headers(phone="01711000006", role="reviewer")
    src_id = source_registry.create_source(
        {
            "title": "Land Reforms Act (Fake Test Data)",
            "source_type": "statute",
        }
    )

    # Version 1: Effective from 2010-01-01, open-ended
    v1_id = source_registry.add_version(
        source_id=src_id,
        file_content="Section 1: Ceiling on agricultural land is 100 bighas.\n\nSection 2: Land tax is 10 taka per decimal.",
        effective_from="2010-01-01",
        version_label="2010 Act",
        uploader_id="usr-uploader-1",
    )
    source_registry.approve(v1_id, reviewer_id="usr-reviewer-1")

    v1 = db_manager.get_source_version(v1_id)
    assert v1["status"] == "approved"
    assert v1["effective_to"] is None

    # Version 2: Effective from 2023-01-01
    v2_id = source_registry.add_version(
        source_id=src_id,
        file_content="Section 1: Ceiling on agricultural land is 60 bighas.\n\nSection 2: Land tax is 25 taka per decimal.\n\nSection 3: Digital mutation mandated.",
        effective_from="2023-01-01",
        version_label="2023 Amendment",
        uploader_id="usr-uploader-1",
    )
    # Approve Version 2
    source_registry.approve(v2_id, reviewer_id="usr-reviewer-1")

    # Assert Version 1's effective_to is now set to 2022-12-31 (day before 2023-01-01)
    v1_updated = db_manager.get_source_version(v1_id)
    assert v1_updated["effective_to"] == "2022-12-31"
    assert v1_updated["superseded_by_version_id"] == v2_id

    # Test Diff between Version 1 and Version 2
    res_diff = client.get(
        f"/api/v1/admin/sources/versions/{v2_id}/diff?predecessor_id={v1_id}",
        headers=reviewer_headers,
    )
    assert res_diff.status_code == 200
    diff_data = res_diff.json()
    assert diff_data["added_count"] == 1  # Section 3 added
    assert diff_data["modified_count"] == 2  # Section 1 and Section 2 changed
    assert diff_data["removed_count"] == 0

    # Overlap block test: Attempt to approve Version 3 with effective_from earlier than v2
    v3_id = source_registry.add_version(
        source_id=src_id,
        file_content="Section 1: Conflicting backward amendment.",
        effective_from="2021-01-01",  # Overlaps / precedes Version 2!
        version_label="Conflicting v3",
        uploader_id="usr-uploader-1",
    )
    with pytest.raises(ValueError, match="Date overlap error"):
        source_registry.approve(v3_id, reviewer_id="usr-reviewer-2")


def test_ac_m10_3_unapproved_content_invisible_to_citizens():
    """
    AC-M10-3: Unapproved content is invisible to all citizen endpoints (API test).
    """
    citizen_headers = _get_auth_headers(phone="01711000007", role="citizen")

    src_id = source_registry.create_source(
        {
            "title": "Confidential Draft Regulations (Fake Test Data)",
            "source_type": "rule",
        }
    )
    v_draft_id = source_registry.add_version(
        source_id=src_id,
        file_content="Section 1: Secret draft rule content.",
        effective_from="2026-01-01",
        version_label="Unapproved Draft",
        uploader_id="usr-admin",
    )

    # 1. Citizen cannot find it in search
    res_search = client.get(
        "/api/v1/library/search?q=Secret&as_of=2026-10-02",
        headers=citizen_headers,
    )
    assert res_search.status_code == 200
    assert len(res_search.json()["results"]) == 0

    # 2. Citizen direct GET on unapproved version returns 404
    res_ver = client.get(f"/api/v1/library/versions/{v_draft_id}", headers=citizen_headers)
    assert res_ver.status_code == 404


def test_ac_m10_6_ingestion_pipeline_steps_and_retry():
    """
    AC-M10-6: Ingestion pipeline completes asynchronously with per-step status and retry.
    """
    admin_headers = _get_auth_headers(phone="01711000008", role="admin")

    src_id = source_registry.create_source(
        {
            "title": "Family Courts Act (Fake Test Data)",
            "source_type": "statute",
        }
    )

    # 1. Normal successful ingestion
    v_id = source_registry.add_version(
        source_id=src_id,
        file_content="Section 1: Short title and commencement.\n\nSection 2: Establishment of Family Courts.",
        effective_from="2023-01-01",
        version_label="1.0",
        uploader_id=admin_headers["x-user-id"],
    )
    jobs = db_manager.list_ingestion_jobs(source_id=src_id)
    assert len(jobs) == 1
    job = jobs[0]
    assert job["step"] == "completed"
    assert job["status"] == "completed"
    assert job["details"]["passage_count"] == 2

    # Verify per-step API
    res_job = client.get(f"/api/v1/admin/sources/jobs/{job['id']}/status", headers=admin_headers)
    assert res_job.status_code == 200
    assert res_job.json()["job"]["status"] == "completed"

    # 2. Simulated failure and retry
    job_fail_id = "job-fail-test-123"
    db_manager.save_ingestion_job(
        {
            "id": job_fail_id,
            "source_id": src_id,
            "source_version_id": v_id,
            "step": "extracted",
            "status": "pending",
            "details": {},
        }
    )

    # Run with failure at cleaned step
    with pytest.raises(RuntimeError, match="Simulated cleaning error"):
        source_registry.run_ingestion_pipeline(job_fail_id, "Some text", fail_at_step="cleaned")

    failed_job = db_manager.get_ingestion_job(job_fail_id)
    assert failed_job["status"] == "failed"
    assert "Simulated cleaning error" in failed_job["error_message"]

    # Retry job via API
    res_retry = client.post(
        f"/api/v1/admin/sources/jobs/{job_fail_id}/retry", headers=admin_headers
    )
    assert res_retry.status_code == 200
    retried_job = db_manager.get_ingestion_job(job_fail_id)
    assert retried_job["status"] == "completed"
    assert retried_job["error_message"] is None


def test_deterministic_embedder_properties():
    """Validates properties of the pure-Python DeterministicEmbedder."""
    emb = DeterministicEmbedder()
    vec1 = emb.embed_text("landlord eviction notice")
    vec2 = emb.embed_text("landlord eviction notice")
    vec3 = emb.embed_text("child custody divorce")

    # Length matches DIM
    assert len(vec1) == 128
    # Deterministic
    assert vec1 == vec2
    # Semantically distinct texts have lower similarity
    from packages.trust_kernel.retrieval import cosine_similarity

    sim_identical = cosine_similarity(vec1, vec2)
    sim_different = cosine_similarity(vec1, vec3)

    assert pytest.approx(sim_identical, 0.0001) == 1.0
    assert sim_different < 0.85


# =========================================================================
# Explicit Verification Tests for User Checklist Items 3a - 3f
# =========================================================================


def test_3a_negative_draft_unapproved_version_never_retrieved():
    """
    Checklist Item 3a (Negative Test):
    A draft/unapproved source version is NEVER returned by retrieval or citizen endpoints.
    """
    src_id = source_registry.create_source(
        {
            "title": "Secret Internal Draft (Fake Test Data)",
            "source_type": "statute",
            "source_label": "FAKE_TEST_DATA",
        }
    )
    v_id = source_registry.add_version(
        source_id=src_id,
        file_content="Section 1: Confidential unapproved statutory content.",
        effective_from="2020-01-01",
        version_label="Draft 0.1",
        uploader_id="uploader-3a",
    )
    # Check status is review_pending (unapproved)
    v = db_manager.get_source_version(v_id)
    assert v["status"] == "review_pending"

    # 1. Search retrieval returns zero results
    res_search = retrieval_service.search("Confidential", as_of_date="2026-10-02")
    assert len(res_search) == 0

    # 2. Citizen API search returns zero results
    citizen_headers = _get_auth_headers(phone="01711000031", role="citizen")
    res_api = client.get("/api/v1/library/search?q=Confidential&as_of=2026-10-02", headers=citizen_headers)
    assert res_api.status_code == 200
    assert len(res_api.json()["results"]) == 0

    # 3. Citizen direct version GET returns 404
    res_ver = client.get(f"/api/v1/library/versions/{v_id}", headers=citizen_headers)
    assert res_ver.status_code == 404


def test_3b_version_outside_effective_period_never_retrieved():
    """
    Checklist Item 3b (Negative Test):
    A version whose effective period does not include the as-of date is NEVER returned.
    """
    src_id = source_registry.create_source(
        {
            "title": "Historic Ordinance (Fake Test Data)",
            "source_type": "ordinance",
            "source_label": "FAKE_TEST_DATA",
        }
    )
    # Effective strictly between 2010-01-01 and 2015-12-31
    v_id = source_registry.add_version(
        source_id=src_id,
        file_content="Section 1: Temporary economic emergency measures.",
        effective_from="2010-01-01",
        effective_to="2015-12-31",
        version_label="2010 Ordinance",
        uploader_id="uploader-3b",
    )
    source_registry.approve(v_id, reviewer_id="reviewer-3b")

    # Before effective period (2009-12-31) -> 0 results
    res_before = retrieval_service.search("emergency", as_of_date="2009-12-31")
    assert len(res_before) == 0

    # After effective period (2016-01-01) -> 0 results
    res_after = retrieval_service.search("emergency", as_of_date="2016-01-01")
    assert len(res_after) == 0

    # Inside effective period (2012-06-15) -> 1 result
    res_inside = retrieval_service.search("emergency", as_of_date="2012-06-15")
    assert len(res_inside) == 1
    assert res_inside[0]["source_version_id"] == v_id


def test_3c_superseded_version_time_travel_retrieval():
    """
    Checklist Item 3c:
    After superseding a version, searching with an as-of date inside the OLD version's
    period still returns the OLD version, and a later date returns the NEW one.
    """
    src_id = source_registry.create_source(
        {
            "title": "Companies Regulation Act (Fake Test Data)",
            "source_type": "statute",
            "source_label": "FAKE_TEST_DATA",
        }
    )
    # Version 1: 1994-01-01 to open-ended
    v1_id = source_registry.add_version(
        source_id=src_id,
        file_content="Section 1: Physical share certificate delivery mandatory for company shares.",
        effective_from="1994-01-01",
        version_label="1994 Original",
        uploader_id="uploader-3c",
    )
    source_registry.approve(v1_id, reviewer_id="reviewer-3c-1")

    # Version 2: Effective from 2020-01-01
    v2_id = source_registry.add_version(
        source_id=src_id,
        file_content="Section 1: Dematerialized electronic shares mandatory for company shares.",
        effective_from="2020-01-01",
        version_label="2020 Electronic Amendment",
        uploader_id="uploader-3c",
    )
    source_registry.approve(v2_id, reviewer_id="reviewer-3c-2")

    # Verify Version 1 was superseded: effective_to set to 2019-12-31
    v1 = db_manager.get_source_version(v1_id)
    assert v1["effective_to"] == "2019-12-31"
    assert v1["superseded_by_version_id"] == v2_id

    # Time-travel query 1: As-of 2010-05-01 (inside OLD version period) -> MUST return OLD version
    res_old = retrieval_service.search("shares", as_of_date="2010-05-01")
    assert len(res_old) > 0
    assert all(r["source_version_id"] == v1_id for r in res_old)
    assert "Physical share certificate" in res_old[0]["text"]

    # Time-travel query 2: As-of 2024-01-01 (inside NEW version period) -> MUST return NEW version
    res_new = retrieval_service.search("shares", as_of_date="2024-01-01")
    assert len(res_new) > 0
    assert all(r["source_version_id"] == v2_id for r in res_new)
    assert "Dematerialized electronic shares" in res_new[0]["text"]


def test_3d_overlapping_effective_dates_rejected():
    """
    Checklist Item 3d:
    Overlapping effective dates for the same source are rejected (overlap check).
    """
    src_id = source_registry.create_source(
        {
            "title": "Stamp Duty Act (Fake Test Data)",
            "source_type": "statute",
            "source_label": "FAKE_TEST_DATA",
        }
    )
    # Version 1 approved: 2020-01-01 onwards
    v1_id = source_registry.add_version(
        source_id=src_id,
        file_content="Section 1: Fixed stamp fee 100 taka.",
        effective_from="2020-01-01",
        version_label="2020 Version",
        uploader_id="uploader-3d",
    )
    source_registry.approve(v1_id, reviewer_id="reviewer-3d-1")

    # Version 2 approved: 2025-01-01 onwards
    v2_id = source_registry.add_version(
        source_id=src_id,
        file_content="Section 1: Fixed stamp fee 300 taka.",
        effective_from="2025-01-01",
        version_label="2025 Version",
        uploader_id="uploader-3d",
    )
    source_registry.approve(v2_id, reviewer_id="reviewer-3d-2")

    # Version 3 attempts to approve with effective_from 2023-01-01
    # Conflicts because 2025-01-01 is already approved and would overlap / break chronological sequence
    v3_id = source_registry.add_version(
        source_id=src_id,
        file_content="Section 1: Intermediate stamp fee 200 taka.",
        effective_from="2023-01-01",
        version_label="2023 Conflict Version",
        uploader_id="uploader-3d",
    )
    with pytest.raises(ValueError, match="Date overlap error"):
        source_registry.approve(v3_id, reviewer_id="reviewer-3d-3")


def test_3e_uploader_cannot_self_approve_but_different_reviewer_can():
    """
    Checklist Item 3e:
    Uploader cannot approve own upload (prohibited by AC-M10-1),
    and a reviewer who is a different user can.
    """
    admin_headers = _get_auth_headers(phone="01711000035", role="admin")
    uploader_id = admin_headers["x-user-id"]

    src_id = source_registry.create_source(
        {
            "title": "Insolvency Act (Fake Test Data)",
            "source_type": "statute",
            "source_label": "FAKE_TEST_DATA",
        }
    )
    v_id = source_registry.add_version(
        source_id=src_id,
        file_content="Section 1: Insolvency petition procedure.",
        effective_from="2024-01-01",
        version_label="1.0",
        uploader_id=uploader_id,
    )

    # 1. Uploader attempts to self-approve via service -> raises PermissionError
    with pytest.raises(PermissionError, match="AC-M10-1"):
        source_registry.approve(v_id, reviewer_id=uploader_id)

    # 2. Uploader attempts to self-approve via API -> returns 403 Forbidden
    res_self = client.post(
        f"/api/v1/admin/sources/versions/{v_id}/review",
        json={"decision": "approve", "approval_notes": "Trying to self approve"},
        headers=admin_headers,
    )
    assert res_self.status_code == 403
    assert "cannot be approved by its uploader" in res_self.json()["detail"]

    # 3. Different user with reviewer role approves -> succeeds with 200 OK
    reviewer_headers = _get_auth_headers(phone="01711000036", role="reviewer")
    reviewer_id = reviewer_headers["x-user-id"]
    assert reviewer_id != uploader_id

    res_review = client.post(
        f"/api/v1/admin/sources/versions/{v_id}/review",
        json={"decision": "approve", "approval_notes": "Dual custody verified by distinct reviewer."},
        headers=reviewer_headers,
    )
    assert res_review.status_code == 200
    assert res_review.json()["status"] == "approved"


def test_3f_all_source_state_changes_audited_and_x001_covered():
    """
    Checklist Item 3f:
    Every state change is audited (create_source, upload_source_version,
    supersede_source_version, approve_source_version, reject_source_version)
    and all new library/knowledge routes are covered by X-001 sweep.
    """
    from packages.trust_kernel.audit import audit_service
    from packages.trust_kernel.auth import auth_service

    auth_service.clear()

    # 1. Create source -> audit
    src_id = source_registry.create_source(
        {
            "title": "Audit Test Statute (Fake Test Data)",
            "source_type": "statute",
            "source_label": "FAKE_TEST_DATA",
        },
        actor_id="admin-auditor",
    )

    # 2. Add version 1 -> audit
    v1_id = source_registry.add_version(
        source_id=src_id,
        file_content="Section 1: Initial audit test text.",
        effective_from="2020-01-01",
        version_label="1.0",
        uploader_id="uploader-auditor",
    )

    # 3. Approve version 1 -> audit
    source_registry.approve(v1_id, reviewer_id="reviewer-auditor-1")

    # 4. Add version 2 and approve -> audits version 2 approve AND version 1 supersede
    v2_id = source_registry.add_version(
        source_id=src_id,
        file_content="Section 1: Superseding audit test text.",
        effective_from="2024-01-01",
        version_label="2.0",
        uploader_id="uploader-auditor",
    )
    source_registry.approve(v2_id, reviewer_id="reviewer-auditor-2")

    # 5. Add version 3 and reject -> audit reject
    v3_id = source_registry.add_version(
        source_id=src_id,
        file_content="Section 1: Rejected audit test text.",
        effective_from="2026-01-01",
        version_label="3.0",
        uploader_id="uploader-auditor",
    )
    source_registry.reject(v3_id, reviewer_id="reviewer-auditor-2", notes="Rejected for audit test")

    # Verify audit records in DB
    records = db_manager.load_all_audit_entries()
    actions = [r["action"] for r in records]

    assert "create_source" in actions
    assert "upload_source_version" in actions
    assert "approve_source_version" in actions
    assert "supersede_source_version" in actions
    assert "reject_source_version" in actions

    # Verify audit hash chain integrity
    assert audit_service.verify_integrity() is True

    # 6. Verify that all library and admin/sources routes reject unauthenticated requests (X-001)
    for route_path in [
        "/api/v1/library/categories",
        "/api/v1/library/search",
        f"/api/v1/library/sources/{src_id}",
        f"/api/v1/library/versions/{v1_id}",
        "/api/v1/admin/sources",
        f"/api/v1/admin/sources/{src_id}/versions/upload",
    ]:
        res_unauth = client.get(route_path)
        assert res_unauth.status_code in (401, 403, 405), f"Route {route_path} was not protected!"

