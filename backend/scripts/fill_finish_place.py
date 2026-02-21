import sqlite3
from pathlib import Path

DB_PATH = Path("backend/db/pokerleague.sqlite")
SEASON_ID = "spring_2026"

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Set finish_place from Eliminated events where position exists
    cur.execute("""
        UPDATE weekly_points
        SET finish_place = (
            SELECT r.position
            FROM raw_log_events r
            JOIN tournaments t ON t.tournament_id = r.tournament_id
            WHERE t.season_id = weekly_points.season_id
              AND r.tournament_id = weekly_points.tournament_id
              AND TRIM(r.player_name) = (SELECT player_name FROM players WHERE player_id = weekly_points.player_id)
              AND r.event_type = 'Eliminated'
              AND r.position IS NOT NULL
            LIMIT 1
        )
        WHERE season_id = ?
    """, (SEASON_ID,))

    # Winner: has BuyIn but no Eliminated row => finish_place = 1
    cur.execute("""
        UPDATE weekly_points
        SET finish_place = 1
        WHERE season_id = ?
          AND finish_place IS NULL
          AND EXISTS (
            SELECT 1 FROM raw_log_events r
            WHERE r.tournament_id = weekly_points.tournament_id
              AND r.event_type = 'BuyIn'
              AND TRIM(r.player_name) = (SELECT player_name FROM players WHERE player_id = weekly_points.player_id)
          )
          AND NOT EXISTS (
            SELECT 1 FROM raw_log_events r
            WHERE r.tournament_id = weekly_points.tournament_id
              AND r.event_type = 'Eliminated'
              AND TRIM(r.player_name) = (SELECT player_name FROM players WHERE player_id = weekly_points.player_id)
          )
    """, (SEASON_ID,))

    conn.commit()

    # quick sanity: show winners per week
    rows = cur.execute("""
        SELECT week_num, tournament_date, p.player_name
        FROM weekly_points wp
        JOIN players p ON p.player_id = wp.player_id
        WHERE wp.season_id = ?
          AND wp.finish_place = 1
        ORDER BY wp.week_num
    """, (SEASON_ID,)).fetchall()

    print("✅ Winners by week (finish_place=1):")
    for w, d, name in rows:
        print(f"Week {w} ({d}) - {name}")

    conn.close()

if __name__ == "__main__":
    main()