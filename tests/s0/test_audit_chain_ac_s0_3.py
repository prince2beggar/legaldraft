"""
Test AC-S0-3: Hash-chained Audit Log Integrity
"""

from packages.trust_kernel.audit import GENESIS_HASH, InMemoryAuditService


def test_audit_hash_chain():
    service = InMemoryAuditService()

    # 1. Log three actions
    e1 = service.log("user-1", "citizen", "upload_document", "document", "doc-101")
    assert e1["prev_hash"] == GENESIS_HASH
    assert len(e1["hash"]) == 64

    e2 = service.log("user-1", "citizen", "start_draft", "draft", "dft-202")
    assert e2["prev_hash"] == e1["hash"]

    e3 = service.log("user-1", "citizen", "confirm_field", "field", "fld-303")
    assert e3["prev_hash"] == e2["hash"]

    # 2. Verify integrity passes on unaltered chain
    assert service.verify_integrity() is True


def test_audit_tamper_detection():
    service = InMemoryAuditService()
    service.log("user-1", "citizen", "action_1", "doc", "1")
    service.log("user-1", "citizen", "action_2", "doc", "2")
    service.log("user-1", "citizen", "action_3", "doc", "3")

    assert service.verify_integrity() is True

    # Tamper with an existing entry
    service._entries[1]["action"] = "tampered_action"

    # Integrity verification must catch tampering
    assert service.verify_integrity() is False
