import sqlite3


def check_counts():
    for db_name in ["legal_saas.db", "ain_ai.db"]:
        conn = sqlite3.connect(db_name)
        cur = conn.cursor()
        print(f"=== {db_name} ===")
        for tbl in ["organizations", "matters", "documents", "document_versions"]:
            cur.execute(f'SELECT count(*) FROM "{tbl}"')
            cnt = cur.fetchone()[0]
            print(f"  {tbl}: {cnt} rows")
        conn.close()


if __name__ == "__main__":
    check_counts()
