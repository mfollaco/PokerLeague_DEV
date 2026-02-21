import json
import sqlite3
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from chip_and_chair import build_chip_and_chair, ChipAndChairRules
from compute_survival import compute_survival_season, SurvivalConfig

DB_PATH = Path("backend/db/pokerleague.sqlite")
OUT_PATH = Path("frontend/data/spring_2026.json")
SEASON_ID = "spring_2026"

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Season totals
    season_totals = cur.execute("""
        SELECT p.player_name,
        p.player_id,
        st.season_points_total,
        st.season_points_drop2,
        st.weeks_played,
        st.weeks_in_season,
        COALESCE(pss.wins, 0) AS wins,
        pss.avg_finish AS avg_finish
    FROM season_totals st
    JOIN players p ON p.player_id = st.player_id
    LEFT JOIN player_season_stats pss
    ON pss.season_id = st.season_id
    AND pss.player_id = st.player_id
    WHERE st.season_id = ?
    ORDER BY st.season_points_drop2 DESC, st.season_points_total DESC, p.player_name ASC
    """, (SEASON_ID,)).fetchall()

    # Total payouts per player (season total)
    payout_by_player = cur.execute("""
        SELECT player_id, SUM(amount) AS money_total
        FROM weekly_payouts
        WHERE season_id = ?
        GROUP BY player_id
    """, (SEASON_ID,)).fetchall()

    money_map = { int(pid): float(total or 0) for (pid, total) in payout_by_player }

    season_totals_rows = [
        {
            "Player": name,
            "PlayerID": int(player_id),
            "SeasonPointsTotal": float(total or 0),
            "SeasonPointsDrop2": float(drop2 or 0),
            "WeeksPlayed": int(played or 0),
            "WeeksInSeason": int(wks or 0),
            "Wins": int(wins or 0),
            "AvgFinish": (None if avg_finish is None else float(avg_finish)),
            "MoneyWonTotal": float(money_map.get(int(player_id), 0)),
        }
        for (name, player_id, total, drop2, played, wks, wins, avg_finish) in season_totals
    ]

        # Weekly payouts (sum per week per player)
    payout_totals = cur.execute("""
        SELECT season_id, week_num, player_id, SUM(amount) AS payout_total
        FROM weekly_payouts
        WHERE season_id = ?
        GROUP BY season_id, week_num, player_id
    """, (SEASON_ID,)).fetchall()

    payout_map = {
        (row[1], row[2]): float(row[3] or 0)   # key: (week_num, player_id)
        for row in payout_totals
    }


    money_map = { int(pid): float(total or 0) for (pid, total) in payout_by_player }

    weekly = cur.execute("""
    SELECT wp.week_num, wp.tournament_date, p.player_name, wp.player_id,
           wp.finish_place, wp.points
    FROM weekly_points wp
    JOIN players p ON p.player_id = wp.player_id
    WHERE wp.season_id = ?
    ORDER BY wp.week_num ASC, wp.finish_place ASC, p.player_name ASC
""", (SEASON_ID,)).fetchall()

    weekly_rows = [
        {
            "Week": int(week),
            "TournamentDate": tdate,
            "Player": name,
            "PlayerID": int(player_id),
            "FinishPlace": int(fp),
            "Points": float(pts or 0),
            "Payout": float(payout_map.get((int(week), int(player_id)), 0)),
        }
        for (week, tdate, name, player_id, fp, pts) in weekly
    ]

    build_ts = datetime.now(ZoneInfo("America/New_York")).strftime("%b %d, %Y %I:%M %p %Z")


    # ----------------------------
    # Survival Analytics (backend truth)
    # ----------------------------
    survival_df = compute_survival_season(conn, SurvivalConfig(season_id=SEASON_ID))

    survival_rows = [
        {
            "Player": r["player_name"],
            "WeeksPlayed": int(r["weeks_played"]),
            "AvgMinutesSurvived": float(r["avg_minutes_survived"]),
            "AvgSurvivalPercent": float(r["avg_survival_percent"]),
            "TotalMinutesSurvived": float(r["total_minutes_survived"]),
        }
        for r in survival_df.to_dict(orient="records")
    ]

    # ----------------------------
    # Chip & A Chair (backend truth)
    # ----------------------------
    rules = ChipAndChairRules(
        base_stack=6500,
        season_points_chip_multiplier=150,
        chip_per_total_elim=50,
        chip_per_repeat_elim=100,
        chip_per_hv_elim=250,
    )

    # --- Eliminations (from SQLite raw_log_events) ---
    # Your raw_log_events uses:
    #   event_type = 'Eliminated'
    #   player_name = eliminated player
    #   eliminator_player_name = eliminator
    #
    # eliminated_player_name is empty in your data, so DO NOT use it.

    # Build a rank map from SeasonTotals (Drop-2 points desc)
    # (rank 1 = best)
    sorted_totals = sorted(
        season_totals_rows,
        key=lambda r: (float(r.get("SeasonPointsDrop2") or 0), float(r.get("SeasonPointsTotal") or 0)),
        reverse=True,
    )
    rank_by_player = {r["Player"]: i + 1 for i, r in enumerate(sorted_totals)}

    # Get tournament_ids that belong to this season.
    # Option A (most likely): tournaments has season_id
    tournament_ids = [
        row[0]
        for row in conn.execute(
            "SELECT tournament_id FROM tournaments WHERE season_id = ?",
            (SEASON_ID,),
        ).fetchall()
    ]

    # If tournament_ids comes back empty, your schema probably links differently.
    # In that case, we’ll adjust, but try this first.

    eliminations_rows = []
    if tournament_ids:
        qmarks = ",".join(["?"] * len(tournament_ids))
        sql = f"""
            SELECT
                tournament_id,
                event_ts,
                player_name AS eliminated_player,
                eliminator_player_name AS eliminator_player
            FROM raw_log_events
            WHERE event_type = 'Eliminated'
            AND tournament_id IN ({qmarks})
            AND COALESCE(player_name,'') <> ''
            AND COALESCE(eliminator_player_name,'') <> ''
        """
        for tid, event_ts, eliminated, eliminator in conn.execute(sql, tournament_ids).fetchall():
            eliminations_rows.append({
                "TournamentID": tid,
                "EventTS": event_ts,
                "EliminatedPlayer": eliminated,
                "EliminatorPlayer": eliminator,
                "VictimRank": rank_by_player.get(eliminated),
                "EliminatorRank": rank_by_player.get(eliminator),
            })

        chip_and_chair_rows = build_chip_and_chair(
            season_totals=season_totals_rows,
            eliminations=eliminations_rows,
            rules=rules,
        )

    payload = {
        "season_id": SEASON_ID,
        "build_ts": build_ts,
        "SeasonTotals": season_totals_rows,
        "WeeklyPoints": weekly_rows,
        "Survival": survival_rows,
        "ChipAndChairRules": rules.__dict__,
        "ChipAndChair": chip_and_chair_rows,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    conn.close()
print(f"✅ Wrote JSON: {OUT_PATH}")

if __name__ == "__main__":
    main()