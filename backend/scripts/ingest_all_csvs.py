import csv
import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path("backend/db/pokerleague.sqlite")
DATA_DIR = Path("backend/data_raw")
SEASON_ID = "spring_2026"


def filename_to_iso_date(filename: str) -> str:
    # "02.10.26 log.csv" -> "2026-02-10"
    base = filename.split(" ")[0]  # "02.10.26"
    dt = datetime.strptime(base, "%m.%d.%y")
    return dt.strftime("%Y-%m-%d")


def get_or_create_tournament(cur, season_id: str, iso_date: str, source_file: str) -> int:
    cur.execute(
        """
        INSERT OR IGNORE INTO tournaments (season_id, tournament_date, source_file)
        VALUES (?, ?, ?)
        """,
        (season_id, iso_date, source_file),
    )
    cur.execute(
        """
        SELECT tournament_id FROM tournaments
        WHERE season_id = ? AND tournament_date = ?
        """,
        (season_id, iso_date),
    )
    return int(cur.fetchone()[0])


def ingest_one_csv(cur, tournament_id: int, csv_path: Path) -> int:
    # wipe existing rows for this tournament (safe reruns)
    cur.execute("DELETE FROM raw_log_events WHERE tournament_id = ?", (tournament_id,))

    with open(csv_path, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    inserted = 0
    for r in rows:
        event_ts = (r.get("Time") or "").strip()
        event_type = (r.get("Event") or "unknown").strip()
        player_name = (r.get("Players") or "").strip()
        eliminator_player_name = (r.get("Eliminated By") or "").strip()
        eliminated_player_name = ""

        pos_text = (r.get("Position") or "").strip()
        position = int(pos_text) if pos_text.isdigit() else None

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
                (tournament_id, event_ts, event_type, player_name, eliminated_player_name, eliminator_player_name, notes, position)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (tournament_id, event_ts, event_type, player_name, eliminated_player_name, eliminator_player_name, notes, position),
        )
        inserted += 1

    return inserted


def main():
    if not DB_PATH.exists():
        raise SystemExit(f"DB not found: {DB_PATH}")
    if not DATA_DIR.exists():
        raise SystemExit(f"Data dir not found: {DATA_DIR}")

    csv_files = sorted([p for p in DATA_DIR.glob("*.csv") if "log.csv" in p.name])
    if not csv_files:
        raise SystemExit(f"No log CSV files found in {DATA_DIR}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ensure season exists
    cur.execute("INSERT OR IGNORE INTO seasons (season_id) VALUES (?)", (SEASON_ID,))

    for p in csv_files:
        iso_date = filename_to_iso_date(p.name)
        tournament_id = get_or_create_tournament(cur, SEASON_ID, iso_date, p.name)
        inserted = ingest_one_csv(cur, tournament_id, p)
        print(f"✅ {p.name} -> tournament_id={tournament_id} rows={inserted}")

    conn.commit()
    conn.close()
    print("✅ Done ingesting all log CSVs.")


if __name__ == "__main__":
    main()