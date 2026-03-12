import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get("POKERLEAGUE_DB", "backend/db/pokerleague.sqlite"))
SEASON_ID = "spring_2026"


def points_for_finish(finish_place: int | None) -> float:
    """
    League rule:
    - 1st place = 8.0
    - each lower place drops by 0.5
    - DNP / no finish place = 0.0

    Examples:
    1  -> 8.0
    2  -> 7.5
    14 -> 1.5
    15 -> 1.0
    16 -> 0.5
    None -> 0.0
    """
    if finish_place is None:
        return 0.0

    return max(0.0, round(8.5 - (0.5 * int(finish_place)), 2))


def main():
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    rows = cur.execute(
        """
        SELECT weekly_points_id, finish_place
        FROM weekly_points
        WHERE season_id = ?
        """,
        (SEASON_ID,)
    ).fetchall()

    updated = 0

    for weekly_points_id, finish_place in rows:
        points = points_for_finish(finish_place)

        cur.execute(
            """
            UPDATE weekly_points
            SET points = ?
            WHERE weekly_points_id = ?
            """,
            (points, weekly_points_id)
        )
        updated += 1

    conn.commit()

    total = cur.execute(
        "SELECT COUNT(*) FROM weekly_points WHERE season_id = ?",
        (SEASON_ID,)
    ).fetchone()[0]

    null_finish_place = cur.execute(
        """
        SELECT COUNT(*)
        FROM weekly_points
        WHERE season_id = ?
          AND finish_place IS NULL
        """,
        (SEASON_ID,)
    ).fetchone()[0]

    zero_points = cur.execute(
        """
        SELECT COUNT(*)
        FROM weekly_points
        WHERE season_id = ?
          AND COALESCE(points, 0) = 0
        """,
        (SEASON_ID,)
    ).fetchone()[0]

    print(
        f"✅ fill_points_from_finish done. "
        f"updated={updated} total={total} "
        f"finish_place_null={null_finish_place} points_zero={zero_points}"
    )

    conn.close()


if __name__ == "__main__":
    main()