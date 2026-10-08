"""
Database Backup Utility (Sprint S9 Hardening)
Safely backups SQLite database using SQLite backup API / checkpoint,
computes SHA-256 verification hash, and logs operation.
"""

import hashlib
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def backup_database(db_path: Path | str, backup_dir: Path | str) -> dict:
    source_path = Path(db_path).resolve()
    target_dir = Path(backup_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    if not source_path.exists():
        raise FileNotFoundError(f"Source database file not found: {source_path}")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_file = target_dir / f"{source_path.stem}_backup_{timestamp}.db"
    checksum_file = target_dir / f"{source_path.stem}_backup_{timestamp}.sha256"

    # SQLite-safe online backup
    src_conn = sqlite3.connect(str(source_path))
    dst_conn = sqlite3.connect(str(backup_file))
    with dst_conn:
        src_conn.backup(dst_conn, pages=100)
    dst_conn.close()
    src_conn.close()

    # Calculate SHA-256
    sha256 = hashlib.sha256()
    with open(backup_file, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    digest = sha256.hexdigest()

    checksum_file.write_text(digest, encoding="utf-8")

    # Record row counts for verification
    verify_conn = sqlite3.connect(str(backup_file))
    cur = verify_conn.cursor()
    tables = [
        row[0]
        for row in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
        ).fetchall()
    ]
    table_counts = {
        tbl: cur.execute(f"SELECT COUNT(*) FROM {tbl};").fetchone()[0] for tbl in tables
    }
    verify_conn.close()

    return {
        "source": str(source_path),
        "backup_file": str(backup_file),
        "checksum_file": str(checksum_file),
        "sha256": digest,
        "timestamp": timestamp,
        "table_counts": table_counts,
    }


if __name__ == "__main__":
    db_env = os.environ.get("DB_PATH", "legal_saas_test.db")
    backup_target = os.environ.get("BACKUP_DIR", "storage/backups")
    result = backup_database(db_env, backup_target)
    print(f"Backup successful: {result['backup_file']}")
    print(f"SHA-256: {result['sha256']}")
    print(f"Tables: {result['table_counts']}")
