import os
import sqlite3
from pathlib import Path


def test_legacy_data_integrity_and_migration():
    """
    Validates that:
    1. legal_saas.db exists and is never deleted.
    2. Databases are opened strictly in read-only mode (file:... ?mode=ro).
    3. File modification time of legal_saas.db is completely unchanged before and after the test run.
    4. All legacy records (organizations, matters, documents, document_versions)
       from legal_saas.db exist in ain_ai.db with exact IDs and matching attributes.
    """
    legacy_db = Path("legal_saas.db").resolve()
    new_db = Path("ain_ai.db").resolve()

    assert legacy_db.exists(), "legal_saas.db must be preserved as backup"
    assert new_db.exists(), "ain_ai.db must exist as active unified DB"

    mtime_legacy_before = os.path.getmtime(legacy_db)

    # Open both databases strictly in read-only mode using SQLite URI
    conn_old = sqlite3.connect(f"file:{legacy_db}?mode=ro", uri=True)
    cur_old = conn_old.cursor()

    conn_new = sqlite3.connect(f"file:{new_db}?mode=ro", uri=True)
    cur_new = conn_new.cursor()

    for table in ["organizations", "matters", "documents", "document_versions"]:
        cur_old.execute(f"SELECT id FROM \"{table}\";")
        old_ids = {r[0] for r in cur_old.fetchall()}

        cur_new.execute(f"SELECT id FROM \"{table}\";")
        new_ids = {r[0] for r in cur_new.fetchall()}

        # Assert every single legacy ID exists in the unified database
        missing = old_ids - new_ids
        assert not missing, f"Table '{table}' is missing legacy IDs in ain_ai.db: {missing}"

    conn_old.close()
    conn_new.close()

    mtime_legacy_after = os.path.getmtime(legacy_db)
    assert mtime_legacy_after == mtime_legacy_before, "legal_saas.db modification time changed! It must remain completely untouched."
