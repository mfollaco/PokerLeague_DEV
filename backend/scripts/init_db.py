import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get("POKERLEAGUE_DB", "backend/db/pokerleague.sqlite"))
SCHEMA_PATH = Path("backend/sql/schema.sql")

def main():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # 👇 ADD THIS
    print("Schema path:", SCHEMA_PATH.resolve())

    schema = SCHEMA_PATH.read_text(encoding="utf-8")

    # 👇 ADD THIS
    print("Schema length:", len(schema))

    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.executescript(schema)
        conn.commit()
        print(f"Initialized schema in {DB_PATH}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()