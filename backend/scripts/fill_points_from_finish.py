import sqlite3
from pathlib import Path

DB_PATH = Path("backend/db/pokerleague.sqlite")
SEASON_ID = "spring_2026"

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # For each tournament, count players in weekly_points (that week’s players)
    cur.execute("""
        SELECT tournament_id, COUNT(*) as players_in_week
        FROM weekly_points
        WHERE season_id = ?
        GROUP BY tournament_id
    """, (SEASON_ID,))
    counts = dict(cur.fetchall())

    updated = 0
    for tournament_id, players_in_week in counts.items():
        # points = 0.5 * (players_in_week - finish_place + 1)
        cur.execute("""
            UPDATE weekly_points
            SET points = 0.5 * (? - finish_place + 1)
            WHERE season_id = ?
              AND tournament_id = ?
        """, (players_in_week, SEASON_ID, tournament_id))
        updated += cur.rowcount

    conn.commit()
    conn.close()
    print(f"✅ Filled points for {updated} rows.")

if __name__ == "__main__":
    main()