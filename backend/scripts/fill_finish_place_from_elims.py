import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path("backend/db/pokerleague.sqlite")
SEASON_ID = "spring_2026"

def parse_dt(tournament_date: str, time_text: str) -> datetime:
    # tournament_date: "2026-02-10"
    # time_text: "8:15pm" or "8:15 pm"
    t = (time_text or "").strip().lower().replace(" ", "")
    # make "8:15pm" -> "8:15 PM"
    t = t[:-2] + " " + t[-2:] if len(t) >= 2 and t[-2:] in ("am", "pm") else t
    return datetime.strptime(f"{tournament_date} {t}", "%Y-%m-%d %I:%M %p")

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # For each tournament, compute finish places from elimination order
    cur.execute("""
        SELECT tournament_id, tournament_date
        FROM tournaments
        WHERE season_id = ?
        ORDER BY tournament_date
    """, (SEASON_ID,))
    tournaments = cur.fetchall()

    for tournament_id, tdate in tournaments:
        # get players in weekly_points for this tournament
        cur.execute("""
            SELECT wp.player_id, p.player_name
            FROM weekly_points wp
            JOIN players p ON p.player_id = wp.player_id
            WHERE wp.season_id = ? AND wp.tournament_id = ?
        """, (SEASON_ID, tournament_id))
        players = cur.fetchall()
        if not players:
            continue

        n_players = len(players)

        # pull elimination times
        cur.execute("""
            SELECT TRIM(player_name) AS eliminated_player, event_ts
            FROM raw_log_events
            WHERE tournament_id = ?
              AND event_type = 'Eliminated'
              AND player_name IS NOT NULL AND TRIM(player_name) <> ''
              AND event_ts IS NOT NULL AND TRIM(event_ts) <> ''
        """, (tournament_id,))
        elim_rows = cur.fetchall()

        elim_order = []
        for eliminated_player, event_ts in elim_rows:
            try:
                elim_order.append((eliminated_player, parse_dt(tdate, event_ts)))
            except Exception:
                # if a time is weird, skip it (we can fix later)
                continue

        # earliest elimination first
        elim_order.sort(key=lambda x: x[1])

        # map eliminated player -> finish_place
        # earliest out = last place (n), latest out = 2nd, winner = 1st
        finish_map = {}
        for idx, (name, _dt) in enumerate(elim_order):
            finish_map[name] = n_players - idx

        # winner = in roster but not eliminated
        eliminated_names = set(finish_map.keys())
        all_names = {name for _pid, name in players}
        winners = sorted(all_names - eliminated_names)

        # usually exactly 1 winner
        if len(winners) == 1:
            finish_map[winners[0]] = 1

        # write finish_place back to weekly_points
        for player_id, player_name in players:
            finish_place = finish_map.get(player_name)
            cur.execute("""
                UPDATE weekly_points
                SET finish_place = ?
                WHERE season_id = ? AND tournament_id = ? AND player_id = ?
            """, (finish_place, SEASON_ID, tournament_id, player_id))

        print(f"✅ tournament_id={tournament_id} date={tdate} players={n_players} elims={len(elim_order)} winner={winners}")

    conn.commit()
    conn.close()
    print("✅ Done filling finish_place from elimination order.")

if __name__ == "__main__":
    main()