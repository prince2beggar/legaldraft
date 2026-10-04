import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "ain_ai.db"

conn = sqlite3.connect(str(DB_PATH))
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(matters);")
cols = [r[1] for r in cursor.fetchall()]
print("Columns in matters:", cols)

cursor.execute("SELECT id, title, client_name, matter_type, status, user_id FROM matters LIMIT 3;")
print("Sample rows:", cursor.fetchall())
conn.close()
