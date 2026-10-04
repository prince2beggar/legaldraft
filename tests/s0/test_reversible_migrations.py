"""
Tests that Alembic database migrations are fully reversible (SRS 9.4 Definition of Done).
Verifies:
1. alembic upgrade head -> all tables created
2. Data seeding into multiple core tables
3. alembic downgrade base -> all tables successfully dropped
4. alembic upgrade head -> re-applies cleanly without errors
"""

import os
import sqlite3

import pytest
from alembic import command
from alembic.config import Config

TEST_DB_PATH = "test_migration_reversibility.db"


@pytest.fixture(scope="module")
def migration_config():
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except OSError:
            pass

    old_db_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"

    alembic_cfg = Config("services/api/alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{TEST_DB_PATH}")
    yield alembic_cfg

    if old_db_url is not None:
        os.environ["DATABASE_URL"] = old_db_url
    else:
        os.environ.pop("DATABASE_URL", None)

    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except OSError:
            pass


def test_migration_reversible_lifecycle(migration_config):
    # Step 1: Upgrade to head
    command.upgrade(migration_config, "head")

    conn = sqlite3.connect(TEST_DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0] for row in cursor.fetchall()}
    assert "users" in tables
    assert "cases" in tables
    assert "documents" in tables
    assert "sources" in tables
    assert "rules" in tables
    assert "consents" in tables
    assert "audit_log" in tables
    # Sprint S1 & S2 Trust Kernel and Ingestion tables
    assert "trust_users" in tables
    assert "trust_devices" in tables
    assert "trust_consents" in tables
    assert "trust_audit_logs" in tables
    assert "trust_blocked_phone_hashes" in tables
    assert "ingestion_jobs" in tables
    # Sprint S3 Rules, Verifier, AI Gateway, Eval tables
    assert "rule_tests" in tables
    assert "prompts" in tables
    assert "ai_outputs" in tables
    assert "claim_links" in tables
    assert "eval_runs" in tables
    assert "eval_results" in tables
    # Sprint S4 Document Ingestion & Resumable Upload tables
    assert "document_uploads_resumable" in tables

    # Step 2: Seed data
    cursor.execute(
        "INSERT INTO users (id, phone, name, preferred_lang, numeral_style, status) VALUES (?, ?, ?, ?, ?, ?)",
        ("usr-001", "01711000000", "Advocate Test", "bn", "bn", "active"),
    )
    cursor.execute(
        "INSERT INTO cases (id, owner_id, title, case_type, status) VALUES (?, ?, ?, ?, ?)",
        ("cas-001", "usr-001", "Mirpur Rent Case", "tenancy", "intake"),
    )
    cursor.execute(
        "INSERT INTO trust_users (id, phone, name, preferred_lang, numeral_style, status, is_onboarded, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "usr-trust-001",
            "01722000000",
            "Citizen Kamal",
            "bn",
            "bn",
            "active",
            1,
            "2026-10-02T12:00:00Z",
        ),
    )
    cursor.execute(
        "INSERT INTO trust_audit_logs (id, at, actor_id, actor_role, action, object_type, object_id, ip, meta_json, prev_hash, hash) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "audit-000001",
            "2026-10-02T12:00:00Z",
            "usr-trust-001",
            "citizen",
            "test_action",
            "case",
            "cas-001",
            "127.0.0.1",
            "{}",
            "0000",
            "aaaa",
        ),
    )
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM users")
    assert cursor.fetchone()[0] == 1
    cursor.execute("SELECT COUNT(*) FROM cases")
    assert cursor.fetchone()[0] == 1
    cursor.execute("SELECT COUNT(*) FROM trust_users")
    assert cursor.fetchone()[0] == 1
    cursor.execute("SELECT COUNT(*) FROM trust_audit_logs")
    assert cursor.fetchone()[0] == 1
    conn.close()

    # Step 3: Downgrade to base
    command.downgrade(migration_config, "base")

    conn = sqlite3.connect(TEST_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name != 'alembic_version';"
    )
    remaining_tables = [row[0] for row in cursor.fetchall()]
    conn.close()

    assert len(remaining_tables) == 0, (
        f"Expected 0 tables after downgrade, found: {remaining_tables}"
    )

    # Step 4: Upgrade back to head
    command.upgrade(migration_config, "head")

    conn = sqlite3.connect(TEST_DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    recreated_tables = {row[0] for row in cursor.fetchall()}
    conn.close()

    assert "users" in recreated_tables
    assert "cases" in recreated_tables
    assert "audit_log" in recreated_tables
    assert "trust_users" in recreated_tables
    assert "trust_audit_logs" in recreated_tables
    assert "ingestion_jobs" in recreated_tables
    assert "rule_tests" in recreated_tables
    assert "ai_outputs" in recreated_tables
    assert "eval_runs" in recreated_tables
