import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get("POKERLEAGUE_DB", "backend/db/pokerleague.sqlite"))
SEASON_ID = "spring_2026"

def main():
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    tournament_ids = [
        r[0] for r in cur.execute(
            "SELECT DISTINCT tournament_id FROM weekly_points WHERE season_id = ?",
            (SEASON_ID,)
        ).fetchall()
    ]

    total_updated = 0

    for tid in tournament_ids:

        # Field (BuyIn players already seeded into weekly_points)
        field = [
            r[0] for r in cur.execute(
                "SELECT player_id FROM weekly_points WHERE season_id=? AND tournament_id=?",
                (SEASON_ID, tid)
            ).fetchall()
        ]

        field_size = len(field)
        if field_size == 0:
            continue

        # Eliminations ordered by time
        for tournament_id in tournament_ids:

            elim_rows = cur.execute(
                """
                SELECT
                COALESCE(
                    NULLIF(TRIM(r.eliminated_player_name), ''),
                    NULLIF(TRIM(r.player_name), '')
                ) AS eliminated_name
                FROM raw_log_events r
                WHERE r.tournament_id = ?
                AND r.event_type = 'Eliminated'
                ORDER BY r.raw_event_id
                """,
                (tournament_id,)
            ).fetchall()

            elim_player_ids = []
            for (name,) in elim_rows:
                if not name:
                    continue

                row = cur.execute(
                    "SELECT player_id FROM players WHERE TRIM(player_name) = TRIM(?)",
                    (name,)
                ).fetchone()

                if row:
                    elim_player_ids.append(int(row[0]))
        
        # Who played this tournament?
        participants = cur.execute(
            """
            SELECT player_id
            FROM weekly_points
            WHERE season_id = ? AND tournament_id = ?
            """,
            (SEASON_ID, tournament_id)
        ).fetchall()
        participant_ids = [int(r[0]) for r in participants]

        # winner = someone who is NOT in eliminated list
        eliminated_set = set(elim_player_ids)
        winners = [pid for pid in participant_ids if pid not in eliminated_set]

        if len(winners) != 1:
            # Can't determine a single winner; skip this tournament
            continue

        winner_id = winners[0]

        # finish places: last eliminated gets 2nd, ..., first eliminated gets Nth
        # Example: elim order = [A, B, C] means A out first => 4th, C out last => 2nd
        n = len(participant_ids)
        elim_count = len(elim_player_ids)

        # Update eliminated players
        for idx, pid in enumerate(elim_player_ids):
            finish_place = n - idx  # first eliminated -> n, last eliminated -> 2
            cur.execute(
                """
                UPDATE weekly_points
                SET finish_place = ?
                WHERE season_id = ? AND tournament_id = ? AND player_id = ?
                """,
                (finish_place, SEASON_ID, tournament_id, pid)
            )

        # Update winner
        cur.execute(
            """
            UPDATE weekly_points
            SET finish_place = 1
            WHERE season_id = ? AND tournament_id = ? AND player_id = ?
            """,
            (SEASON_ID, tournament_id, winner_id)
        )

    # (whatever your code does next to assign finish_place using elim_player_ids)

        # Assign finish places
        # First eliminated = last place (N)
        current_place = field_size

        for pid in elim_player_ids:
            cur.execute(
                """
                UPDATE weekly_points
                SET finish_place = ?
                WHERE season_id=? AND tournament_id=? AND player_id=?
                """,
                (current_place, SEASON_ID, tid, pid)
            )
            current_place -= 1
            total_updated += 1

        # Remaining player (not eliminated) = winner
        remaining = [pid for pid in field if pid not in elim_player_ids]
        if len(remaining) == 1:
            winner_pid = remaining[0]
            cur.execute(
                """
                UPDATE weekly_points
                SET finish_place = 1
                WHERE season_id=? AND tournament_id=? AND player_id=?
                """,
                (SEASON_ID, tid, winner_pid)
            )
            total_updated += 1

    conn.commit()

    nulls = cur.execute(
        "SELECT COUNT(*) FROM weekly_points WHERE season_id=? AND finish_place IS NULL",
        (SEASON_ID,)
    ).fetchone()[0]

    print(f"✅ fill_finish_place done. updated={total_updated} finish_place_null={nulls}")

    conn.close()

if __name__ == "__main__":
    main()