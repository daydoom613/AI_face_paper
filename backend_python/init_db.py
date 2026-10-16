"""
Small helper script to initialize the SQLite database using schema.sql.
Run once before first use:

    python init_db.py
"""

import os
import sqlite3

from config import DB_PATH


def main() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    schema_path = os.path.join(os.path.dirname(__file__), "..", "database", "schema.sql")
    schema_path = os.path.abspath(schema_path)

    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(schema_sql)
        conn.commit()
        print(f"Database initialized at {DB_PATH}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

