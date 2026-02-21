import sqlite3
from pathlib import Path

DB_PATH = Path("backend/db/pokerleague.sqlite")
SEASON_ID = "spring_2026"

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # wipe old derived rows for season (safe rerun)
    cur.execute("DELETE FROM weekly_points WHERE season_id = ?", (SEASON_ID,))

    # Build a week_num mapping by tournament_date order
    cur.execute("""
        SELECT tournament_id, tournament_date
        FROM tournaments
        WHERE season_id = ?
        ORDER BY tournament_date
    """, (SEASON_ID,))
    tournaments = cur.fetchall()

    week_map = {tid: i + 1 for i, (tid, _d) in enumerate(tournaments)}
    date_map = {tid: d for tid, d in tournaments}

    # Get distinct players per tournament from BuyIn events
    cur.execute("""
        SELECT DISTINCT r.tournament_id, TRIM(r.player_name) AS player_name
        FROM raw_log_events r
        JOIN tournaments t ON t.tournament_id = r.tournament_id
        WHERE t.season_id = ?
          AND r.event_type = 'BuyIn'
          AND r.player_name IS NOT NULL
          AND TRIM(r.player_name) <> ''
        ORDER BY r.tournament_id, player_name
    """, (SEASON_ID,))
    buyins = cur.fetchall()

    inserted = 0
    for tournament_id, player_name in buyins:
        # lookup player_id
        cur.execute("SELECT player_id FROM players WHERE player_name = ?", (player_name,))
        row = cur.fetchone()
        if not row:
            continue
        player_id = int(row[0])

        cur.execute("""
            INSERT OR REPLACE INTO weekly_points
              (season_id, tournament_id, week_num, tournament_date, player_id, finish_place, points, payout)
            VALUES (?, ?, ?, ?, ?, NULL, NULL, NULL)
        """, (
            SEASON_ID,
            tournament_id,
            week_map[tournament_id],
            date_map[tournament_id],
            player_id
        ))
        inserted += 1

    conn.commit()

    cur.execute("SELECT COUNT(*) FROM weekly_points WHERE season_id = ?", (SEASON_ID,))
    count = cur.fetchone()[0]

    print(f"✅ weekly_points built. Inserted {inserted}. Total rows for {SEASON_ID}: {count}")
    conn.close()

if __name__ == "__main__":
    main()