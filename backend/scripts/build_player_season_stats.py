import sqlite3
from pathlib import Path

DB_PATH = Path("backend/db/pokerleague.sqlite")
SEASON_ID = "spring_2026"

def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    # Create table if missing
    cur.execute("""
    CREATE TABLE IF NOT EXISTS player_season_stats (
      season_id TEXT NOT NULL,
      player_id INTEGER NOT NULL,
      wins INTEGER NOT NULL DEFAULT 0,
      avg_finish REAL,
      PRIMARY KEY (season_id, player_id)
    );
    """)

    # Build stats from weekly_points
    cur.execute("""
    INSERT INTO player_season_stats (season_id, player_id, wins, avg_finish)
    SELECT
      season_id,
      player_id,
      SUM(CASE WHEN finish_place = 1 THEN 1 ELSE 0 END) AS wins,
      AVG(CAST(finish_place AS REAL)) AS avg_finish
    FROM weekly_points
    WHERE season_id = ?
      AND finish_place IS NOT NULL
    GROUP BY season_id, player_id
    ON CONFLICT(season_id, player_id) DO UPDATE SET
      wins = excluded.wins,
      avg_finish = excluded.avg_finish;
    """, (SEASON_ID,))

    con.commit()

    # Print top 10 as a quick check
    rows = cur.execute("""
    SELECT p.player_name, s.wins, ROUND(s.avg_finish, 2) AS avg_finish
    FROM player_season_stats s
    JOIN players p ON p.player_id = s.player_id
    WHERE s.season_id = ?
    ORDER BY s.wins DESC, s.avg_finish ASC, p.player_name ASC
    LIMIT 10;
    """, (SEASON_ID,)).fetchall()

    print("✅ player_season_stats updated. Sample:")
    for r in rows:
        print(r)

    con.close()

if __name__ == "__main__":
    main()