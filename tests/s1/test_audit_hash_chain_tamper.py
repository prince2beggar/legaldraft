"""
Test Audit Hash Chain & Tamper Detection (SRS Section 8.6, 9.3 S1, X-002).
Verifies:
1. Every state-changing action creates an append-only hash-chained record.
2. Legitimate chain passes verify_integrity().
3. Unauthorized alteration of historical record breaks cryptographic integrity.
"""

import pytest

from packages.trust_kernel.audit import audit_service


@pytest.fixture(autouse=True)
def clean_audit_state():
    audit_service.clear()
    yield
    audit_service.clear()


def test_audit_hash_chain_and_tamper_detection():
    # 1. Initially empty or valid chain
    assert audit_service.verify_integrity() is True

    # 2. Append state-changing actions
    e1 = audit_service.log(
        actor_id="usr-101",
        actor_role="citizen",
        action="otp_verified",
        object_type="user",
        object_id="usr-101",
    )
    e2 = audit_service.log(
        actor_id="usr-101",
        actor_role="citizen",
        action="onboarding_completed",
        object_type="user",
        object_id="usr-101",
    )
    e3 = audit_service.log(
        actor_id="usr-101",
        actor_role="citizen",
        action="case_created",
        object_type="case",
        object_id="cas-001",
    )

    # 3. Verify chained linkage
    assert e2["prev_hash"] == e1["hash"]
    assert e3["prev_hash"] == e2["hash"]
    assert audit_service.verify_integrity() is True

    # 4. Simulate malicious tampering of record #1 (e.g. changing action or actor)
    audit_service.tamper_with_record(
        index=0, field="action", new_value="malicious_unauthorized_action"
    )

    # 5. Cryptographic verification MUST detect the tamper and return False!
    assert audit_service.verify_integrity() is False
