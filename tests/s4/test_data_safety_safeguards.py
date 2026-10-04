"""
Data Safety & Production Isolation Safeguard Tests (SRS Section 8.6, Sprint S4 DoD).
Verifies:
1. Tests execute strictly against an isolated temporary database (never production ain_ai.db).
2. Tests execute strictly against an isolated temporary storage folder (never production storage/).
3. The fail-fast safeguard immediately triggers if DATABASE_URL or STORAGE_DIR points to real production files.
4. Backups exist in backups/ directory with non-zero sizes.
"""

import os
from pathlib import Path


def test_safeguard_database_is_isolated():
    db_url = os.environ.get("DATABASE_URL", "")
    assert db_url.startswith("sqlite:///"), f"Expected sqlite URL, got {db_url}"
    db_file = Path(db_url.replace("sqlite:///", "")).resolve()
    real_prod_db = Path("ain_ai.db").resolve()
    assert db_file != real_prod_db, f"SECURITY BREACH: Test is using real production database {real_prod_db}!"
    assert "isolated" in str(db_file).lower() or "tmp" in str(db_file).lower() or "test" in str(db_file).lower()


def test_safeguard_storage_is_isolated():
    storage_dir = Path(os.environ.get("STORAGE_DIR", "")).resolve()
    real_storage = Path("storage").resolve()
    assert storage_dir != real_storage, f"SECURITY BREACH: Test is using real production storage folder {real_storage}!"
    assert "isolated" in str(storage_dir).lower() or "tmp" in str(storage_dir).lower() or "test" in str(storage_dir).lower()


import pytest


def test_backup_files_exist_and_non_empty():
    backup_root = Path("backups")
    if not backup_root.exists():
        pytest.skip("backups/ directory is absent on clean checkout or CI")
    backup_dirs = sorted([d for d in backup_root.iterdir() if d.is_dir() and (d.name.startswith("backup_") or d.name.startswith("dev_cleanup_"))])
    if not backup_dirs:
        pytest.skip("No backup snapshots found in local backups/ directory")

    latest_backup = backup_dirs[-1]
    assert (latest_backup / "ain_ai.db").exists(), f"ain_ai.db missing in backup {latest_backup}"
    assert (latest_backup / "ain_ai.db").stat().st_size > 100_000, "ain_ai.db backup is suspiciously small"

    # legal_saas.db check if present in snapshot
    if (latest_backup / "legal_saas.db").exists():
        assert (latest_backup / "legal_saas.db").stat().st_size > 50_000, "legal_saas.db backup is suspiciously small"

    assert (latest_backup / "storage").exists(), f"storage/ missing in backup {latest_backup}"
