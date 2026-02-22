# backend/scripts/compute_survival.py

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, date, timedelta
import pandas as pd


@dataclass(frozen=True)
class SurvivalConfig:
    season_id: str

    events_table: str = "raw_log_events"
    tournaments_table: str = "tournaments"

    # column names
    col_tournament_id: str = "tournament_id"
    col_event_ts: str = "event_ts"              # time-only like "7:13pm"
    col_event_type: str = "event_type"
    col_player_name: str = "player_name"
    col_eliminated_name: str = "eliminated_player_name"
    col_tournament_date: str = "tournament_date"  # YYYY-MM-DD

    # event types (confirmed from your DB)
    evt_tournament_start: str = "TOURNAMENT START"
    evt_tournament_end: str = "TOURNAMENT END"
    evt_eliminated: str = "Eliminated"
    evt_buyin: str = "BuyIn"


def _parse_tournament_date(d: str) -> date:
    return datetime.strptime(d.strip(), "%Y-%m-%d").date()


def _parse_time_ampm(t: str) -> datetime.time:
    s = t.strip().lower().replace(" ", "")
    return datetime.strptime(s, "%I:%M%p").time()


def _combine_dt(t_date: str, t_time: str) -> datetime:
    d = _parse_tournament_date(t_date)
    tm = _parse_time_ampm(t_time)
    return datetime.combine(d, tm)


def _minutes_between(a: datetime, b: datetime) -> float:
    return max(0.0, (b - a).total_seconds() / 60.0)


def compute_survival_weekly(conn: sqlite3.Connection, cfg: SurvivalConfig) -> pd.DataFrame:
    """
    Returns one row per (tournament_id, player_name) with:
      - tournament_minutes
      - minutes_survived
      - survival_percent

    Rules:
      - Participants = all BuyIn player_name for that tournament
      - Start = TOURNAMENT START timestamp (fallback to MIN event_dt)
      - End   = TOURNAMENT END timestamp (fallback to MAX event_dt)
      - Eliminated players: first Eliminated row for eliminated_player_name
      - Non-eliminated: full tournament duration
      - Handle midnight crossover: if end < start => end + 1 day
    """
    sql = f"""
    SELECT
        e.{cfg.col_tournament_id} AS tournament_id,
        t.{cfg.col_tournament_date} AS tournament_date,
        e.{cfg.col_event_ts} AS event_ts,
        e.{cfg.col_event_type} AS event_type,
        e.{cfg.col_player_name} AS player_name,
        CASE
            WHEN e.{cfg.col_event_type} = 'Eliminated'
                THEN COALESCE(
                    NULLIF(TRIM(e.{cfg.col_eliminated_name}), ''),
                    NULLIF(TRIM(e.{cfg.col_player_name}), '')
                    )
            ELSE NULL
            END AS eliminated_player_name
    FROM {cfg.events_table} e
    JOIN {cfg.tournaments_table} t
      ON t.{cfg.col_tournament_id} = e.{cfg.col_tournament_id}
    WHERE t.season_id = ?
      AND e.{cfg.col_event_ts} IS NOT NULL
    """
    df = pd.read_sql_query(sql, conn, params=(cfg.season_id,))

    if df.empty:
        return pd.DataFrame(columns=[
            "tournament_id", "player_name",
            "tournament_minutes", "minutes_survived", "survival_percent"
        ])

    # build real datetimes from tournament_date + event_ts
    df["event_dt"] = df.apply(lambda r: _combine_dt(r["tournament_date"], r["event_ts"]), axis=1)

    out_rows = []

    for tid, g in df.groupby("tournament_id", sort=True):
        # Tournament boundaries
        start_rows = g[g["event_type"] == cfg.evt_tournament_start]
        end_rows = g[g["event_type"] == cfg.evt_tournament_end]

        start_dt = start_rows["event_dt"].min() if not start_rows.empty else g["event_dt"].min()
        end_dt = end_rows["event_dt"].max() if not end_rows.empty else g["event_dt"].max()

        # Midnight crossover (keep consistent with old site)
        if end_dt < start_dt:
            end_dt = end_dt + timedelta(days=1)

        tournament_minutes = _minutes_between(start_dt, end_dt)

        # Participants = BuyIn player_name
        participants = (
            g.loc[g["event_type"] == cfg.evt_buyin, "player_name"]
             .dropna()
             .astype(str)
             .unique()
             .tolist()
        )

        # First elimination timestamp per eliminated player
        elim = g[g["event_type"] == cfg.evt_eliminated].copy()
        elim = elim.dropna(subset=["eliminated_player_name"])
        elim_first = elim.groupby("eliminated_player_name", as_index=True)["event_dt"].min()

        for player in participants:
            if player in elim_first.index:
                minutes_survived = _minutes_between(start_dt, elim_first[player])
                if tournament_minutes > 0:
                    minutes_survived = min(minutes_survived, tournament_minutes)
            else:
                minutes_survived = tournament_minutes

            survival_percent = (minutes_survived / tournament_minutes) if tournament_minutes > 0 else 0.0

            out_rows.append({
                "tournament_id": int(tid),
                "player_name": player,
                "tournament_minutes": round(tournament_minutes, 1),
                "minutes_survived": round(minutes_survived, 1),
                "survival_percent": round(survival_percent, 3),
            })

    return pd.DataFrame(out_rows)


def compute_survival_season(conn: sqlite3.Connection, cfg: SurvivalConfig) -> pd.DataFrame:
    """
    Aggregates weekly survival into season metrics per player:
      - weeks_played
      - avg_minutes_survived
      - avg_survival_percent
      - total_minutes_survived
    """
    weekly = compute_survival_weekly(conn, cfg)
    if weekly.empty:
        return pd.DataFrame(columns=[
            "player_name", "weeks_played",
            "avg_minutes_survived", "avg_survival_percent",
            "total_minutes_survived"
        ])

    season = (
        weekly.groupby("player_name", as_index=False)
              .agg(
                  weeks_played=("tournament_id", "nunique"),
                  avg_minutes_survived=("minutes_survived", "mean"),
                  avg_survival_percent=("survival_percent", "mean"),
                  total_minutes_survived=("minutes_survived", "sum"),
              )
    )

    season["avg_minutes_survived"] = season["avg_minutes_survived"].round(1)
    season["avg_survival_percent"] = season["avg_survival_percent"].round(3)
    season["total_minutes_survived"] = season["total_minutes_survived"].round(1)

    season = season.sort_values(
        ["avg_minutes_survived", "player_name"],
        ascending=[False, True]
    ).reset_index(drop=True)

    return season