import csv
import sqlite3
from pathlib import Path

DB_PATH = Path("backend/db/pokerleague.sqlite")
CSV_PATH = Path("backend/data_raw/02.10.26 log.csv")  # <-- this file must exist
TOURNAMENT_ID = 1  # <-- the tournament_id you just created

def main():
    if not DB_PATH.exists():
        raise SystemExit(f"DB not found: {DB_PATH}")
    if not CSV_PATH.exists():
        raise SystemExit(f"CSV not found: {CSV_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Read CSV
    with open(CSV_PATH, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        raise SystemExit("CSV had no rows.")

    # Insert rows (raw, flexible)
    # We map whatever columns exist into a simple set.
    # If your CSV has different headers, we’ll adjust after the first run.
    inserted = 0
    for r in rows:
        event_ts = (r.get("Time") or "").strip()
        event_type = (r.get("Event") or "unknown").strip()
        player_name = (r.get("Players") or "").strip()
        eliminator_player_name = (r.get("Eliminated By") or "").strip()

        # If the Event text includes an eliminated player, we’ll parse later.
        # For now store nothing here.
        eliminated_player_name = ""

        # Keep extra columns in notes for now
        notes = (
            f"Level={r.get('Level','')}; "
            f"Chips={r.get('Chips','')}; "
            f"Amount={r.get('Amount','')}; "
            f"Table={r.get('Table','')}; "
            f"Position={r.get('Position','')}"
        )

        cur.execute(
            """
            INSERT INTO raw_log_events
              (tournament_id, event_ts, event_type, player_name, eliminated_player_name, eliminator_player_name, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (TOURNAMENT_ID, event_ts, event_type, player_name, eliminated_player_name, eliminator_player_name, notes),
        )
        inserted += 1

    conn.commit()

    # Verify count
    cur.execute("SELECT COUNT(*) FROM raw_log_events WHERE tournament_id = ?", (TOURNAMENT_ID,))
    count = cur.fetchone()[0]
    conn.close()

    print(f"✅ Inserted {inserted} rows. Total raw_log_events for tournament {TOURNAMENT_ID}: {count}")

if __name__ == "__main__":
    main()