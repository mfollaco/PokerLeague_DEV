import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get("POKERLEAGUE_DB", "backend/db/pokerleague.sqlite"))
SEASON_ID = "spring_2026"

def main():
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    # tournaments in season (we use these to scope updates)
    tournament_ids = [
        r[0] for r in cur.execute(
            """
            SELECT tournament_id
            FROM tournaments
            WHERE season_id = ?
            ORDER BY tournament_date
            """,
            (SEASON_ID,),
        ).fetchall()
    ]

    updated = 0

    for tid in tournament_ids:
        # Players who bought in / exist in weekly_points for this tournament
        players = cur.execute(
            """
            SELECT wp.player_id, p.player_name
            FROM weekly_points wp
            JOIN players p ON p.player_id = wp.player_id
            WHERE wp.season_id = ? AND wp.tournament_id = ?
            """,
            (SEASON_ID, tid),
        ).fetchall()

        if not players:
            continue

        n = len(players)
        name_to_pid = {name: int(pid) for pid, name in players}

        # Elimination order (player_name holds eliminated player in your logs)
        elim_names = cur.execute(
            """
            SELECT TRIM(player_name) AS eliminated_name
            FROM raw_log_events
            WHERE tournament_id = ?
              AND event_type = 'Eliminated'
              AND player_name IS NOT NULL
              AND TRIM(player_name) <> ''
            ORDER BY raw_event_id ASC
            """,
            (tid,),
        ).fetchall()

        # De-dupe while preserving order (sometimes logs repeat)
        seen = set()
        elim_order = []
        for (nm,) in elim_names:
            if nm not in seen:
                seen.add(nm)
                elim_order.append(nm)

        # Assign finish places:
        # elim_order[0] => place N, elim_order[1] => N-1, ..., last elim => 2
        for idx, nm in enumerate(elim_order):
            pid = name_to_pid.get(nm)
            if pid is None:
                continue  # name mismatch; ignore
            place = n - idx
            cur.execute(
                """
                UPDATE weekly_points
                SET finish_place = ?
                WHERE season_id = ? AND tournament_id = ? AND player_id = ?
                """,
                (place, SEASON_ID, tid, pid),
            )
            updated += cur.rowcount

        # Winner is the one player NOT eliminated
        eliminated_pids = {name_to_pid[nm] for nm in elim_order if nm in name_to_pid}
        winner_pids = [pid for pid, _name in players if int(pid) not in eliminated_pids]

        # If we have exactly one winner, set them to 1st
        if len(winner_pids) == 1:
            winner_pid = int(winner_pids[0])
            cur.execute(
                """
                UPDATE weekly_points
                SET finish_place = 1
                WHERE season_id = ? AND tournament_id = ? AND player_id = ?
                """,
                (SEASON_ID, tid, winner_pid),
            )
            updated += cur.rowcount

    conn.commit()

    finish_place_null = cur.execute(
        """
        SELECT COUNT(*)
        FROM weekly_points
        WHERE season_id = ? AND finish_place IS NULL
        """,
        (SEASON_ID,),
    ).fetchone()[0]

    print(f"✅ fill_finish_place done. updated={updated} finish_place_null={finish_place_null}")
    conn.close()


if __name__ == "__main__":
    main()