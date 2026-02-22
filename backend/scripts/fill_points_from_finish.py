import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get("POKERLEAGUE_DB", "backend/db/pokerleague.sqlite"))
SEASON_ID = "spring_2026"

# Your league scoring: 0.5 points per finishing position.
# For N players: 1st = N*0.5, last = 0.5
def points_for_finish(finish_place: int, field_size: int) -> float:
    return round((field_size - finish_place + 1) * 0.5, 2)

def main():
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    # For each tournament, compute field size from weekly_points rows and update points
    tournament_ids = [r[0] for r in cur.execute(
        "SELECT DISTINCT tournament_id FROM weekly_points WHERE season_id = ?",
        (SEASON_ID,)
    ).fetchall()]

    updated = 0
    for tid in tournament_ids:
        field_size = cur.execute(
            "SELECT COUNT(*) FROM weekly_points WHERE season_id = ? AND tournament_id = ?",
            (SEASON_ID, tid)
        ).fetchone()[0]

        rows = cur.execute(
            """
            SELECT weekly_points_id, finish_place
            FROM weekly_points
            WHERE season_id = ? AND tournament_id = ?
            """,
            (SEASON_ID, tid)
        ).fetchall()

        for wpid, fp in rows:
            if fp is None:
                continue
            pts = points_for_finish(int(fp), int(field_size))
            cur.execute(
                "UPDATE weekly_points SET points = ? WHERE weekly_points_id = ?",
                (pts, wpid)
            )
            updated += 1

    conn.commit()

    # quick stats
    total = cur.execute("SELECT COUNT(*) FROM weekly_points WHERE season_id = ?", (SEASON_ID,)).fetchone()[0]
    null_fp = cur.execute("SELECT COUNT(*) FROM weekly_points WHERE season_id = ? AND finish_place IS NULL", (SEASON_ID,)).fetchone()[0]
    zero_pts = cur.execute("SELECT COUNT(*) FROM weekly_points WHERE season_id = ? AND COALESCE(points,0)=0", (SEASON_ID,)).fetchone()[0]

    print(f"✅ fill_points_from_finish done. updated={updated} total={total} finish_place_null={null_fp} points_zero={zero_pts}")
    conn.close()

if __name__ == "__main__":
    main()