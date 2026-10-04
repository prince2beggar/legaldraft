"""
Test Persistence Across Application / Session Restart (SRS 9.3 S1 Fixes, Requirement 2).
Verifies that:
1. Users, devices, consents, and audit logs are saved in the real database layer.
2. Upon restarting the app/services, all records are re-hydrated from database.
3. Cryptographic hash chain remains intact and verifies after restart.
"""

import os
import sys

import pytest

from packages.trust_kernel.audit import InMemoryAuditService
from packages.trust_kernel.auth import AuthService
from packages.trust_kernel.db import DatabaseManager
from packages.trust_kernel.policy_consent import PolicyConsentService

TEST_DB_FILE = "test_persistence_restart.db"
TEST_DB_URL = f"sqlite:///{TEST_DB_FILE}"


@pytest.fixture
def isolated_db(monkeypatch):
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except OSError:
            pass

    monkeypatch.setenv("DATABASE_URL", TEST_DB_URL)
    from packages.trust_kernel import audit, auth, db

    pc_mod = sys.modules["packages.trust_kernel.policy_consent"]

    orig_db = db.db_manager
    orig_auth = auth.db_manager
    orig_audit = audit.db_manager
    orig_policy = pc_mod.db_manager

    test_mgr = DatabaseManager(TEST_DB_URL)
    db.db_manager = test_mgr
    auth.db_manager = test_mgr
    audit.db_manager = test_mgr
    pc_mod.db_manager = test_mgr
    audit.audit_service.clear()

    try:
        yield test_mgr
    finally:
        db.db_manager = orig_db
        auth.db_manager = orig_auth
        audit.db_manager = orig_audit
        pc_mod.db_manager = orig_policy
        audit.audit_service.clear()

        if os.path.exists(TEST_DB_FILE):
            try:
                os.remove(TEST_DB_FILE)
            except OSError:
                pass


def test_persistence_and_chain_verification_across_restart(isolated_db):
    phone = "01811223344"

    # --- Session 1: Create user, onboard, record audit events ---
    auth_s1 = AuthService()

    # 1. Request OTP
    req_res = auth_s1.request_otp(phone=phone, device_id="dev-pers-1", device_label="Chrome Laptop")
    otp_code = req_res["dev_otp"]

    # 2. Verify OTP -> User and Device created
    ver_res = auth_s1.verify_otp(
        phone=phone, code=otp_code, device_id="dev-pers-1", device_label="Chrome Laptop"
    )
    user_id = ver_res["user"]["id"]

    # 3. Complete onboarding -> Consents recorded and user updated
    auth_s1.complete_onboarding(
        user_id=user_id,
        name="Kamal Uddin",
        preferred_lang="bn",
        numeral_style="bn",
        terms_accepted=True,
        privacy_accepted=True,
        ai_disclaimer_accepted=True,
    )

    # 4. Verify Session 1 in-memory state and chain
    from packages.trust_kernel.audit import audit_service
    from packages.trust_kernel.policy_consent import policy_consent

    assert user_id in auth_s1._users
    assert len(policy_consent.get_user_consents(user_id)) >= 3
    assert len(audit_service.get_entries()) >= 2
    assert audit_service.verify_integrity() is True

    # --- SIMULATE APP / SESSION RESTART ---
    # In a new session, fresh service instances are instantiated against the same database
    auth_s2 = AuthService()
    policy_s2 = PolicyConsentService()
    audit_s2 = InMemoryAuditService(load_db=True)

    # 1. User is rehydrated from real database
    assert user_id in auth_s2._users
    rehydrated_user = auth_s2._users[user_id]
    assert rehydrated_user["name"] == "Kamal Uddin"
    assert rehydrated_user["phone"] == phone
    assert rehydrated_user["is_onboarded"] is True

    # 2. Device is rehydrated from real database
    assert "dev-pers-1" in auth_s2._devices
    assert auth_s2._devices["dev-pers-1"]["user_id"] == user_id

    # 3. Consents are rehydrated from real database
    rehydrated_consents = policy_s2.get_user_consents(user_id)
    assert len(rehydrated_consents) >= 3
    scopes = {c["scope"] for c in rehydrated_consents}
    assert "terms_of_service" in scopes
    assert "privacy_policy" in scopes
    assert "ai_disclaimer" in scopes

    # 4. Audit ledger is rehydrated and cryptographic hash chain verifies
    rehydrated_audit = audit_s2.get_entries()
    assert len(rehydrated_audit) >= 2
    assert audit_s2.verify_integrity() is True
    print(
        "\n[Persistence Test] Re-hydrated user, devices, consents, and verified audit hash chain successfully!"
    )
