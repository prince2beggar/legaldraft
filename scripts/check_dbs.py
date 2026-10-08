import os
import sqlite3


def inspect_db(db_path):
    print(f"=== Database: {db_path} ===")
    if not os.path.exists(db_path):
        print("  FILE NOT FOUND")
        return
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cur.fetchall()]
    for t in tables:
        cur.execute(f'SELECT COUNT(*) FROM "{t}";')
        cnt = cur.fetchone()[0]
        print(f"  Table '{t}': {cnt} rows")
    conn.close()


if __name__ == "__main__":
    inspect_db("legal_saas.db")
    inspect_db("ain_ai.db")
