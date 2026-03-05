# SPRING 2026 payout split: 45 / 35 / 20
# Do not change mid-season.

import math
import sqlite3
import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get("POKERLEAGUE_DB", "backend/db/pokerleague.sqlite"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Ensure the directory exists (SQLite cannot create folders)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
SEASON_ID = "spring_2026"

# Match your build_all.py PAYOUT_SPLIT.
# Example: 50/30/20 — change if yours is different.
PAYOUT_SPLIT = [0.50, 0.30, 0.20]

# Commissioner payout table for THIS season (fixed amounts by field size).
# Values are [1st, 2nd, 3rd] and must sum to (players * BUY_IN_PER_PLAYER).
PAYOUT_TABLE = {
    16: [160, 100, 60],
    15: [140, 100, 60],
    14: [120, 100, 60],
    13: [120, 80, 60],
    12: [120, 80, 40],
    11: [120, 60, 40],
    10: [100, 60, 40],
}

BUY_IN_PER_PLAYER = 20
ROUND_TO = 20  # payouts must be multiples of $20


def payouts_multiple_of_20(pot: float, percents: list[float], increment: int = 20) -> list[int]:
    raw_amounts = [pot * p for p in percents]

    # floor to nearest increment
    rounded = [math.floor(x / increment) * increment for x in raw_amounts]

    remainder = int(round(pot - sum(rounded)))

    # compute fractional parts so we give remainder to closest-to-round-up
    fractions = [raw - rnd for raw, rnd in zip(raw_amounts, rounded)]

    order = sorted(range(len(fractions)), key=lambda i: fractions[i], reverse=True)

    idx = 0
    while remainder >= increment:
        rounded[order[idx]] += increment
        remainder -= increment
        idx = (idx + 1) % len(order)

    return rounded


def main():
    conn = sqlite3.connect(str(DB_PATH))
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
        # Skip incomplete rows (finish_place not yet computed)
        if finish_place is None:
            continue

        by_week.setdefault(int(week_num), []).append(
            {
                "player_id": int(player_id),
                "finish_place": int(finish_place),
                "points": float(points or 0),
            }
        )

    # 2) Wipe existing payouts for this season (rebuild-from-truth)
    cur.execute("DELETE FROM weekly_payouts WHERE season_id = ?", (SEASON_ID,))

    # 3) Compute + insert payouts per week
    for week_num in sorted(by_week.keys()):
        grp = by_week[week_num]
        player_count = len(grp)  # should already be unique per player/week
        pot = player_count * BUY_IN_PER_PLAYER

        # Week 11 (Chip & A Chair) pays Top 6 by finish_place
        if week_num == 11:
            payout_amounts = [300, 260, 220, 160, 120, 60]
            topN = sorted(grp, key=lambda r: r["finish_place"])[:6]
            payout_type = "chip_and_chair"
            note = f"Chip & A Chair payout: pot=${pot} + season_pool"
        else:
            # Regular weeks pay Top 3 by finish_place
            payout_amounts = PAYOUT_TABLE.get(player_count)
            if payout_amounts is None:
                raise ValueError(f"No payout rule defined for {player_count} players")
            topN = sorted(grp, key=lambda r: r["finish_place"])[:3]
            payout_type = "weekly"
            note = f"Auto payout: pot=${pot}"

        payouts = PAYOUT_TABLE.get(player_count)

        if payouts is None:
            raise ValueError(f"No payout rule defined for {player_count} players")

        for i, r in enumerate(topN):
            amount = float(payout_amounts[i]) if i < len(payout_amounts) else 0.0
            if amount <= 0:
                continue

            cur.execute(
                """
                INSERT INTO weekly_payouts
                    (season_id, week_num, player_id, amount, payout_type, note)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    SEASON_ID,
                    week_num,
                    r["player_id"],
                    amount,
                    payout_type,
                    note,
                ),
            )

    
    # ----------------------------
    # Season Awards (Top 3) - Week 10 (fixed amounts for this season)
    # ----------------------------
    # Wipe any prior season_award rows so rebuilds are idempotent
    cur.execute("""
        DELETE FROM weekly_payouts
        WHERE season_id = ?
          AND week_num = 10
          AND payout_type = 'season_award'
    """, (SEASON_ID,))

    season_awards = [
        ("Bill B", 400.0),
        ("Steve C", 250.0),
        ("Todd L", 150.0),
    ]

    for player_name, amount in season_awards:
        row = cur.execute(
            "SELECT player_id FROM players WHERE player_name = ?",
            (player_name,)
        ).fetchone()
        if not row:
            raise ValueError(f"Season award player not found: {player_name}")
        player_id = int(row[0])

        cur.execute(
            """
            INSERT INTO weekly_payouts (season_id, week_num, player_id, amount, payout_type, note)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (SEASON_ID, 10, player_id, float(amount), "season_award", "Season awards (Top 3)"),
        )

    # ----------------------------
    # Chip & A Chair Tournament Payouts - Week 11 (Top 6 by finish_place)
    # ----------------------------
    # Only run if Week 11 exists for this season (prevents builds from failing before Week 11 happens)
    week11_exists = cur.execute("""
        SELECT 1
        FROM weekly_points
        WHERE season_id = ? AND week_num = 11
        LIMIT 1
    """, (SEASON_ID,)).fetchone()

    if week11_exists:
        # Wipe any prior chip_and_chair rows so rebuilds are idempotent
        cur.execute("""
            DELETE FROM weekly_payouts
            WHERE season_id = ?
              AND week_num = 11
              AND payout_type = 'chip_and_chair'
        """, (SEASON_ID,))

        chip_and_chair_amounts = [300.0, 260.0, 220.0, 160.0, 120.0, 60.0]

        # Get top 6 finishers from Week 11 (finish_place 1..6)
        top6 = cur.execute("""
            SELECT player_id
            FROM weekly_points
            WHERE season_id = ? AND week_num = 11
            ORDER BY finish_place ASC
            LIMIT 6
        """, (SEASON_ID,)).fetchall()

        if len(top6) != 6:
            raise ValueError(f"Week 11 exists but has {len(top6)} finishers; expected 6")

        for i, (player_id,) in enumerate(top6):
            cur.execute(
                """
                INSERT INTO weekly_payouts (season_id, week_num, player_id, amount, payout_type, note)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    SEASON_ID,
                    11,
                    int(player_id),
                    float(chip_and_chair_amounts[i]),
                    "chip_and_chair",
                    "Chip & A Chair tournament payout",
                ),
            )

    conn.commit()
    conn.close()
    print("✅ weekly_payouts rebuilt for", SEASON_ID)


if __name__ == "__main__":
    main()