import sqlite3
from pathlib import Path

DB_PATH = Path("backend/db/pokerleague.sqlite")

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Insert player_name values found in raw events
    cur.execute("""
        INSERT OR IGNORE INTO players (player_name)
        SELECT DISTINCT TRIM(player_name)
        FROM raw_log_events
        WHERE player_name IS NOT NULL AND TRIM(player_name) <> ''
    """)

    # Also insert eliminators (often populated on elimination events)
    cur.execute("""
        INSERT OR IGNORE INTO players (player_name)
        SELECT DISTINCT TRIM(eliminator_player_name)
        FROM raw_log_events
        WHERE eliminator_player_name IS NOT NULL AND TRIM(eliminator_player_name) <> ''
    """)

    conn.commit()

    cur.execute("SELECT COUNT(*) FROM players;")
    count = cur.fetchone()[0]

    print(f"✅ players table populated. Total players: {count}")

    cur.execute("SELECT player_id, player_name FROM players ORDER BY player_name;")
    rows = cur.fetchall()
    for pid, name in rows:
        print(f"{pid}\t{name}")

    conn.close()

if __name__ == "__main__":
    main()