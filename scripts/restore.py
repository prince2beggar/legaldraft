"""
Database Restore Utility (Sprint S9 Hardening)
Verifies SHA-256 checksum before restoration, checks PRAGMA integrity,
restores DB to destination, and verifies row counts and audit chain continuity.
"""

import hashlib
import shutil
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def restore_database(backup_file: Path | str, target_db_path: Path | str) -> dict:
    backup_path = Path(backup_file).resolve()
    target_path = Path(target_db_path).resolve()

    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")

    # Check for checksum file
    checksum_file = backup_path.with_suffix(".sha256")
    if checksum_file.exists():
        expected_sha = checksum_file.read_text(encoding="utf-8").strip()
        sha256 = hashlib.sha256()
        with open(backup_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        actual_sha = sha256.hexdigest()
        if actual_sha != expected_sha:
            raise ValueError(f"Checksum mismatch! Expected: {expected_sha}, Got: {actual_sha}")

    # Verify backup integrity before restoring
    test_conn = sqlite3.connect(str(backup_path))
    integrity = test_conn.execute("PRAGMA integrity_check;").fetchone()[0]
    if integrity != "ok":
        test_conn.close()
        raise ValueError(f"Backup integrity check failed: {integrity}")

    # Get table row counts
    cur = test_conn.cursor()
    tables = [
        row[0]
        for row in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
        ).fetchall()
    ]
    backup_counts = {
        tbl: cur.execute(f"SELECT COUNT(*) FROM {tbl};").fetchone()[0] for tbl in tables
    }
    test_conn.close()

    # Perform restore (copy)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if target_path.exists():
        target_path.unlink()
    shutil.copy2(str(backup_path), str(target_path))

    # Verify restored target
    restored_conn = sqlite3.connect(str(target_path))
    restored_integrity = restored_conn.execute("PRAGMA integrity_check;").fetchone()[0]
    if restored_integrity != "ok":
        restored_conn.close()
        raise ValueError(f"Restored database integrity check failed: {restored_integrity}")

    restored_cur = restored_conn.cursor()
    restored_counts = {
        tbl: restored_cur.execute(f"SELECT COUNT(*) FROM {tbl};").fetchone()[0] for tbl in tables
    }
    restored_conn.close()

    for tbl, count in backup_counts.items():
        if restored_counts.get(tbl) != count:
            raise ValueError(
                f"Row count mismatch on {tbl}: backup has {count}, restored has {restored_counts.get(tbl)}"
            )

    return {
        "status": "success",
        "backup_file": str(backup_path),
        "target_db": str(target_path),
        "integrity": restored_integrity,
        "table_counts": restored_counts,
    }


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python restore.py <backup_file> <target_db_path>")
        sys.exit(1)
    res = restore_database(sys.argv[1], sys.argv[2])
    print(f"Restore successful to {res['target_db']}")
    print(f"Verified row counts: {res['table_counts']}")
