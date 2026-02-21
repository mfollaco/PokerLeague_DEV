# SPRING 2026 payout split: 45 / 35 / 20
# Do not change mid-season.

import math
import sqlite3
import os
from pathlib import Path

DB_PATH = Path(os.environ.get("POKERLEAGUE_DB", "backend/db/pokerleague.sqlite"))

# Ensure the directory exists (SQLite cannot create folders)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
SEASON_ID = "spring_2026"

# Match your build_all.py PAYOUT_SPLIT.
# Example: 50/30/20 — change if yours is different.
PAYOUT_SPLIT = [0.45, 0.35, 0.2]

assert len(PAYOUT_SPLIT) == 3, "PAYOUT_SPLIT must match top-3 payout logic"
assert abs(sum(PAYOUT_SPLIT) - 1.0) < 0.0001, "PAYOUT_SPLIT must sum to 1"

BUY_IN_PER_PLAYER = 20
ROUND_TO = 20  # payouts must be multiples of $20


def payouts_multiple_of_20(pot: float, percents: list[float], increment: int = 20) -> list[int]:
    raw_amounts = [pot * p for p in percents]
    rounded = [math.floor(x / increment) * increment for x in raw_amounts]
    remainder = int(round(pot - sum(rounded)))

    i = 0
    while remainder >= increment:
        rounded[i] += increment
        remainder -= increment
        i = (i + 1) % len(rounded)

    return rounded


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1) Pull weekly results (one row per player per week)
    rows = cur.execute(
        """
        SELECT week_num, player_id, finish_place, points
        FROM weekly_points
        WHERE season_id = ?
        ORDER BY week_num ASC, finish_place ASC
        """,
        (SEASON_ID,),
    ).fetchall()

    # Group by week_num
    by_week = {}
    for week_num, player_id, finish_place, points in rows:
        by_week.setdefault(int(week_num), []).append(
            {
                "player_id": int(player_id),
                "finish_place": int(finish_place),
                "points": float(points or 0),
            }
        )

    # 2) Wipe existing payouts for this season (rebuild-from-truth)
    cur.execute("DELETE FROM weekly_payouts WHERE season_key = ?", (SEASON_ID,))

    # 3) Compute + insert payouts per week
    for week_num in sorted(by_week.keys()):
        grp = by_week[week_num]
        player_count = len(grp)  # should already be unique per player/week
        pot = player_count * BUY_IN_PER_PLAYER

        # Top 3 by finish place (1,2,3) — this matches your existing pipeline
        top3 = sorted(grp, key=lambda r: r["finish_place"])[:3]
        if not top3:
            continue

        payouts = payouts_multiple_of_20(pot, PAYOUT_SPLIT, increment=ROUND_TO)

        labels = ["1st", "2nd", "3rd"]
        for i, r in enumerate(top3):
            amount = float(payouts[i]) if i < len(payouts) else 0.0
            if amount <= 0:
                continue

            cur.execute(
                """
                INSERT INTO weekly_payouts
                  (season_key, week_num, player_id, amount, payout_type, note)
                VALUES
                  (?, ?, ?, ?, ?, ?)
                """,
                (
                    SEASON_ID,
                    week_num,
                    r["player_id"],
                    amount,
                    labels[i],
                    f"Auto payout: pot=${pot}",
                ),
            )

    conn.commit()
    conn.close()
    print("✅ weekly_payouts rebuilt for", SEASON_ID)


if __name__ == "__main__":
    main()