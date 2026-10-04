import sqlite3


def compare_and_migrate():
    conn_old = sqlite3.connect("legal_saas.db")
    cur_old = conn_old.cursor()

    conn_new = sqlite3.connect("ain_ai.db")
    cur_new = conn_new.cursor()

    for table in ["organizations", "matters", "documents", "document_versions"]:
        cur_old.execute(f"PRAGMA table_info({table});")
        old_cols = [c[1] for c in cur_old.fetchall()]

        cur_new.execute(f"PRAGMA table_info({table});")
        new_cols = [c[1] for c in cur_new.fetchall()]

        common_cols = [c for c in old_cols if c in new_cols]
        cols_str = ", ".join(f'"{c}"' for c in common_cols)

        cur_old.execute(f"SELECT {cols_str} FROM \"{table}\";")
        old_rows = cur_old.fetchall()

        cur_new.execute(f"SELECT id FROM \"{table}\";")
        existing_new_ids = {r[0] for r in cur_new.fetchall()}

        migrated_count = 0
        for row in old_rows:
            row_id = row[common_cols.index("id")]
            if row_id not in existing_new_ids:
                placeholders = ", ".join("?" for _ in common_cols)
                cur_new.execute(f"INSERT INTO \"{table}\" ({cols_str}) VALUES ({placeholders});", row)
                migrated_count += 1

        print(f"Table '{table}': {len(old_rows)} rows in legal_saas.db. Newly migrated to ain_ai.db: {migrated_count}. Total in ain_ai.db: {len(existing_new_ids) + migrated_count}")

    conn_new.commit()
    conn_old.close()
    conn_new.close()

if __name__ == "__main__":
    compare_and_migrate()
