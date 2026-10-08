"""
Reset Development Database Script (scripts/reset_dev_db.py).
Safely resets the local development environment:
1. Prompts for confirmation (or accepts --yes).
2. Backs up current ain_ai.db and storage/ to backups/dev_cleanup_<timestamp>/.
3. Moves polluted files to backups (preserves everything, never deletes).
4. Creates fresh empty storage/ directory.
5. Runs Alembic migrations (upgrade head) to create fresh schema in ain_ai.db.
6. Migrates clean legacy baseline from legal_saas.db (read-only source).
7. Verifies and displays row counts before and after.
"""

import argparse
import datetime
import os
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def get_table_counts(db_path: Path | str) -> dict[str, int]:
    if not os.path.exists(db_path):
        return {}
    conn = sqlite3.connect(f"file:{Path(db_path).resolve()}?mode=ro", uri=True)
    cur = conn.cursor()
    counts = {}
    for table in ["organizations", "matters", "documents", "document_versions"]:
        try:
            cur.execute(f'SELECT count(*) FROM "{table}"')
            counts[table] = cur.fetchone()[0]
        except Exception:
            counts[table] = 0
    conn.close()
    return counts


def reset_dev_db(skip_confirm: bool = False) -> None:
    ain_ai_db = REPO_ROOT / "ain_ai.db"
    storage_dir = REPO_ROOT / "storage"
    backups_root = REPO_ROOT / "backups"

    if not skip_confirm:
        print("=" * 65)
        print("  WARNING: This will reset ain_ai.db and storage/ to a clean state.")
        print("  Existing files will be safely moved to backups/.")
        print("  legal_saas.db will NOT be touched (it is read-only).")
        print("=" * 65)
        ans = input("Are you sure you want to proceed? [y/N]: ").strip().lower()
        if ans not in ("y", "yes"):
            print("Aborted by user.")
            sys.exit(0)

    # 1. Capture before counts
    before_counts = get_table_counts(ain_ai_db)
    print("\n[STEP 1] Current row counts in ain_ai.db before reset:")
    for tbl, count in before_counts.items():
        print(f"  - {tbl}: {count}")

    # 2. Timestamped backup destination
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_target = backups_root / f"dev_cleanup_{timestamp}"
    backup_target.mkdir(parents=True, exist_ok=True)

    # 3. Move polluted ain_ai.db
    if ain_ai_db.exists():
        dest_db = backup_target / "ain_ai.db"
        shutil.move(str(ain_ai_db), str(dest_db))
        print(f"\n[STEP 2] Moved existing ain_ai.db to: {dest_db}")

    # 4. Move polluted storage/
    if storage_dir.exists():
        dest_storage = backup_target / "storage"
        shutil.move(str(storage_dir), str(dest_storage))
        print(f"[STEP 3] Moved existing storage/ to: {dest_storage}")

    # Re-create fresh clean storage directories
    storage_dir.mkdir(parents=True, exist_ok=True)
    (storage_dir / "documents").mkdir(parents=True, exist_ok=True)
    (storage_dir / "screenshots").mkdir(parents=True, exist_ok=True)
    print("[STEP 4] Created fresh clean storage/ directory.")

    # 5. Run Alembic migrations to create fresh clean ain_ai.db schema
    print("\n[STEP 5] Applying Alembic migrations (alembic upgrade head)...")
    alembic_ini = REPO_ROOT / "services" / "api" / "alembic.ini"
    res = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(alembic_ini), "upgrade", "head"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        print(f"Alembic migration failed:\n{res.stderr}")
        sys.exit(1)
    print("  [OK] Alembic migrations successfully applied to new ain_ai.db.")

    # Initialize legacy tables and Trust Kernel schema extensions
    if str(REPO_ROOT / "backend") not in sys.path:
        sys.path.insert(0, str(REPO_ROOT / "backend"))
    import app.models  # noqa: F401
    from app.core.database import Base as LegacyBase
    from sqlalchemy import create_engine

    from packages.trust_kernel.db import DatabaseManager

    db_eng = create_engine(f"sqlite:///{ain_ai_db}")
    LegacyBase.metadata.create_all(bind=db_eng)
    dm = DatabaseManager(f"sqlite:///{ain_ai_db}")
    dm.init_schema()

    # 6. Migrate clean legacy baseline from legal_saas.db
    print("\n[STEP 6] Migrating baseline legacy data from legal_saas.db...")
    from scripts.migrate_legacy_data import compare_and_migrate

    compare_and_migrate()

    # 7. Capture after counts
    after_counts = get_table_counts(ain_ai_db)
    print("\n[STEP 7] Final row counts in fresh ain_ai.db after reset:")
    for tbl, count in after_counts.items():
        print(f"  - {tbl}: {count}")

    # Verify that exactly the legacy rows are present
    assert after_counts.get("matters") == 15, (
        f"Expected 15 matters, got {after_counts.get('matters')}"
    )
    assert after_counts.get("documents") == 5, (
        f"Expected 5 documents, got {after_counts.get('documents')}"
    )
    assert after_counts.get("organizations") == 1, (
        f"Expected 1 organization, got {after_counts.get('organizations')}"
    )
    assert after_counts.get("document_versions") == 5, (
        f"Expected 5 document_versions, got {after_counts.get('document_versions')}"
    )
    print(
        "\n[SUCCESS] Clean dev database verified! Exactly 15 matters, 5 documents, 1 organization, 5 document_versions present."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reset dev database and storage safely.")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation prompt.")
    args = parser.parse_args()
    reset_dev_db(skip_confirm=args.yes)
