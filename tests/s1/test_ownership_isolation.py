"""
Test Suite: Cross-Tenant Data Isolation and Route Authorization (X-001)
Verifies:
1. Citizen A cannot read, edit, or list Citizen B's matters.
2. Citizen A cannot read, edit, export, version-check, or health-audit Citizen B's documents.
3. Citizen B cannot inject intake facts or attach drafts to Citizen A's matters.
4. Regular citizens are strictly forbidden (403) from all /api/v1/admin/* endpoints.
5. Admin users have legitimate administrative access.
"""

import pytest
from fastapi.testclient import TestClient

from packages.trust_kernel.auth import auth_service
from services.api.app.main import app

client = TestClient(app)


def _get_auth_headers(phone: str) -> dict:
    req = client.post("/auth/otp/request", json={"phone": phone})
    assert req.status_code == 200, f"OTP request failed: {req.text}"
    code = req.json()["dev_otp"]
    ver = client.post("/auth/otp/verify", json={"phone": phone, "code": code})
    assert ver.status_code == 200, f"OTP verify failed: {ver.text}"
    token = ver.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def clean_state():
    auth_service.clear()
    yield
    auth_service.clear()


def test_matter_ownership_isolation_between_citizens():
    headers_a = _get_auth_headers("01711111111")
    headers_b = _get_auth_headers("01722222222")

    # 1. Citizen A creates a matter
    res_create = client.post(
        "/api/v1/matters/",
        json={
            "title": "Confidential Lease Agreement - Citizen A",
            "matter_type": "commercial_lease",
            "client_name": "Citizen A Firm",
            "notes": "Highly sensitive business details",
        },
        headers=headers_a,
    )
    assert res_create.status_code == 200, res_create.text
    matter_a = res_create.json()
    matter_a_id = matter_a["id"]

    # 2. Citizen A can read their own matter
    res_read_a = client.get(f"/api/v1/matters/{matter_a_id}", headers=headers_a)
    assert res_read_a.status_code == 200
    assert res_read_a.json()["id"] == matter_a_id

    # 3. Citizen B attempts to read Citizen A's matter -> MUST return 403 Forbidden
    res_read_b = client.get(f"/api/v1/matters/{matter_a_id}", headers=headers_b)
    assert res_read_b.status_code == 403, (
        f"Data Leak: Citizen B was able to read Citizen A's matter! Status: {res_read_b.status_code}"
    )
    assert (
        "forbidden" in res_read_b.json()["detail"].lower()
        or "consent" in res_read_b.json()["detail"].lower()
    )

    # 4. Citizen B lists matters -> Matter A must NOT be visible in the list
    res_list_b = client.get("/api/v1/matters/", headers=headers_b)
    assert res_list_b.status_code == 200
    matters_for_b = res_list_b.json()
    assert all(m["id"] != matter_a_id for m in matters_for_b), (
        "Data Leak: Citizen A's matter appeared in Citizen B's matter list!"
    )


def test_document_ownership_isolation_between_citizens():
    headers_a = _get_auth_headers("01733333333")
    headers_b = _get_auth_headers("01744444444")

    # Citizen A creates a matter and generates a draft document
    res_create_m = client.post(
        "/api/v1/matters/",
        json={"title": "Tenancy Case A", "matter_type": "commercial_lease"},
        headers=headers_a,
    )
    assert res_create_m.status_code == 200
    matter_a_id = res_create_m.json()["id"]

    res_gen = client.post(
        "/api/v1/drafting/generate",
        json={
            "template_code": "BD_COMMERCIAL_LEASE",
            "facts": {
                "lessor_name": "Owner A",
                "lessee_name": "Tenant A",
                "monthly_rent": "50000",
            },
            "matter_id": matter_a_id,
        },
        headers=headers_a,
    )
    assert res_gen.status_code == 200, res_gen.text
    doc_a_id = res_gen.json()["id"]

    # 1. Citizen A can read their document
    res_doc_a = client.get(f"/api/v1/documents/{doc_a_id}", headers=headers_a)
    assert res_doc_a.status_code == 200

    # 2. Citizen B attempts to read Citizen A's document -> 403 Forbidden
    res_doc_b = client.get(f"/api/v1/documents/{doc_a_id}", headers=headers_b)
    assert res_doc_b.status_code == 403, (
        f"Data Leak: Citizen B read Citizen A's document! Status: {res_doc_b.status_code}"
    )

    # 3. Citizen B attempts to update Citizen A's document -> 403 Forbidden
    res_upd_b = client.put(
        f"/api/v1/documents/{doc_a_id}",
        json={"full_text": "Malicious Tampered Content", "change_summary": "Injected by B"},
        headers=headers_b,
    )
    assert res_upd_b.status_code == 403

    # 4. Citizen B attempts to view Document A versions -> 403 Forbidden
    res_ver_b = client.get(f"/api/v1/documents/{doc_a_id}/versions", headers=headers_b)
    assert res_ver_b.status_code == 403

    # 5. Citizen B attempts to export Document A -> 403 Forbidden
    res_docx_b = client.get(f"/api/v1/documents/{doc_a_id}/export/docx", headers=headers_b)
    assert res_docx_b.status_code == 403

    # 6. Citizen B attempts to audit Document A health -> 403 Forbidden
    res_health_b = client.get(f"/api/v1/review/{doc_a_id}/health", headers=headers_b)
    assert res_health_b.status_code == 403

    # 7. Citizen B lists documents -> Document A must not be visible
    res_list_b = client.get("/api/v1/documents/", headers=headers_b)
    assert res_list_b.status_code == 200
    docs_for_b = res_list_b.json()
    assert all(d["id"] != doc_a_id for d in docs_for_b)


def test_cross_user_matter_tampering_prevented():
    headers_a = _get_auth_headers("01755555555")
    headers_b = _get_auth_headers("01766666666")

    res_matter = client.post(
        "/api/v1/matters/",
        json={"title": "Case 555", "matter_type": "commercial_lease"},
        headers=headers_a,
    )
    assert res_matter.status_code == 200
    matter_id = res_matter.json()["id"]

    # Citizen B attempts to inject facts into Citizen A's matter via chat -> 403 Forbidden
    res_tamper_chat = client.post(
        f"/api/v1/intake/chat?matter_id={matter_id}",
        json={"user_input": "Injected statement from user B", "matter_type": "commercial_lease"},
        headers=headers_b,
    )
    assert res_tamper_chat.status_code == 403

    # Citizen B attempts to attach generated draft to Citizen A's matter -> 403 Forbidden
    res_tamper_draft = client.post(
        "/api/v1/drafting/generate",
        json={"template_code": "BD_COMMERCIAL_LEASE", "facts": {}, "matter_id": matter_id},
        headers=headers_b,
    )
    assert res_tamper_draft.status_code == 403


def test_admin_routes_role_restrictions():
    headers_citizen = _get_auth_headers("01777777777")
    headers_admin = _get_auth_headers("01700000001")  # Pre-seeded admin

    # 1. Citizen cannot access /api/v1/admin/stats -> 403 Forbidden
    res_stats_cit = client.get("/api/v1/admin/stats", headers=headers_citizen)
    assert res_stats_cit.status_code == 403
    assert "admin or reviewer role required" in res_stats_cit.json()["detail"].lower()

    # 2. Citizen cannot access /api/v1/admin/audit-logs -> 403 Forbidden
    res_audit_cit = client.get("/api/v1/admin/audit-logs", headers=headers_citizen)
    assert res_audit_cit.status_code == 403

    # 3. Citizen cannot access /api/v1/admin/feedback-queue -> 403 Forbidden
    res_fb_cit = client.get("/api/v1/admin/feedback-queue", headers=headers_citizen)
    assert res_fb_cit.status_code == 403

    # 4. Admin CAN access /api/v1/admin/stats -> 200 OK
    res_stats_adm = client.get("/api/v1/admin/stats", headers=headers_admin)
    assert res_stats_adm.status_code == 200
    assert "platform_status" in res_stats_adm.json()

    # 5. Admin CAN access /api/v1/admin/audit-logs -> 200 OK
    res_audit_adm = client.get("/api/v1/admin/audit-logs", headers=headers_admin)
    assert res_audit_adm.status_code == 200
    assert isinstance(res_audit_adm.json(), list)
