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

    for t in ["case_facts", "case_events", "templates", "drafts", "consents"]:
        if t in tables:
            cursor.execute(f"PRAGMA table_info({t});")
            cols = [r[1] for r in cursor.fetchall()]
            print(f"Columns in {t}: {cols}")
    conn.close()


if __name__ == "__main__":
    inspect()
