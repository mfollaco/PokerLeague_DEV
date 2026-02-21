import sqlite3
from pathlib import Path

DB_PATH = Path("backend/db/pokerleague.sqlite")
SEASON_ID = "spring_2026"
DROPS = 2

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Weeks in season
    cur.execute("""
        SELECT COUNT(*) FROM tournaments
        WHERE season_id = ?
    """, (SEASON_ID,))
    weeks_in_season = int(cur.fetchone()[0])

    # list of tournament_ids for the season
    cur.execute("""
        SELECT tournament_id
        FROM tournaments
        WHERE season_id = ?
        ORDER BY tournament_date
    """, (SEASON_ID,))
    tournament_ids = [r[0] for r in cur.fetchall()]

    # all players (roster for season would be better later; for now: all players table)
    cur.execute("SELECT player_id FROM players")
    player_ids = [r[0] for r in cur.fetchall()]

    # wipe season totals
    cur.execute("DELETE FROM season_totals WHERE season_id = ?", (SEASON_ID,))

    # Build totals per player
    for pid in player_ids:
        week_points = []
        weeks_played = 0

        for tid in tournament_ids:
            cur.execute("""
                SELECT points
                FROM weekly_points
                WHERE season_id = ? AND tournament_id = ? AND player_id = ?
            """, (SEASON_ID, tid, pid))
            row = cur.fetchone()
            pts = float(row[0]) if row and row[0] is not None else 0.0
            week_points.append(pts)
            if row and row[0] is not None:
                weeks_played += 1

        total = round(sum(week_points), 2)

        # drop lowest DROPS scores (including zeros for absences)
        sorted_pts = sorted(week_points)
        kept = sorted_pts[DROPS:] if len(sorted_pts) > DROPS else []
        drop2 = round(sum(kept), 2)

        cur.execute("""
            INSERT INTO season_totals
              (season_id, player_id, season_points_total, season_points_drop2, weeks_in_season, weeks_played)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (SEASON_ID, pid, total, drop2, weeks_in_season, weeks_played))

    conn.commit()

    # Show top 10 by drop2
    rows = cur.execute("""
        SELECT p.player_name, st.season_points_drop2, st.season_points_total, st.weeks_played, st.weeks_in_season
        FROM season_totals st
        JOIN players p ON p.player_id = st.player_id
        WHERE st.season_id = ?
        ORDER BY st.season_points_drop2 DESC, st.season_points_total DESC, p.player_name ASC
        LIMIT 10
    """, (SEASON_ID,)).fetchall()

    print("✅ Top 10 (Drop 2)")
    for name, drop2, total, played, wks in rows:
        print(f"{name}\tdrop2={drop2}\ttotal={total}\tplayed={played}/{wks}")

    conn.close()

if __name__ == "__main__":
    main()