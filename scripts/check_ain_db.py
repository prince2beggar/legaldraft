"""
Inspects ain_ai.db to see if legacy matters exist.
Read-only script.
"""
import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "ain_ai.db"

def inspect():
    if not DB_PATH.exists():
        print("ain_ai.db does not exist")
        return
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cursor.fetchall()]
    print("Tables:", tables)

    for t in ["legacy_matters", "matters", "cases"]:
        if t in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {t}")
            cnt = cursor.fetchone()[0]
            print(f"Count in {t}: {cnt}")
    conn.close()

if __name__ == "__main__":
    inspect()
