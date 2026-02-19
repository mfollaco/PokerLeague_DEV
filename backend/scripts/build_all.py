from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import math

import pandas as pd

from source_files import latest_log_filename


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


    return rounded


def parse_dt_series(s: pd.Series) -> pd.Series:
    """
    Warning-free datetime parsing for strings that may:
    - have or not have seconds
    - have AM/PM attached (e.g., '7:05PM')
    """
    s = (
        s.astype("string")
         .str.strip()
         .str.replace(r"\s+", " ", regex=True)
         .str.replace(r"(?i)(\d)(am|pm)$", r"\1 \2", regex=True)
         .str.upper()
    )

    dt_no_sec = pd.to_datetime(s, format="%m/%d/%y %I:%M %p", errors="coerce")
    dt_with_sec = pd.to_datetime(s, format="%m/%d/%y %I:%M:%S %p", errors="coerce")

    return dt_no_sec.fillna(dt_with_sec)


# --- project paths ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "backend" / "data_raw"
PROCESSED_DIR = PROJECT_ROOT / "backend" / "data_processed"
TABLES_DIR = PROCESSED_DIR / "tables"

FRONTEND_DATA_DIR = PROJECT_ROOT / "frontend" / "data"
FRONTEND_DATA_DIR.mkdir(parents=True, exist_ok=True)
JSON_OUTPUT_PATH = FRONTEND_DATA_DIR / "spring_2026.json"

BUILD_TS_EST = datetime.now(ZoneInfo("America/New_York")).strftime("%b %d, %Y %I:%M %p %Z")
def format_int_cols_for_html(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """
    For HTML rendering only: format specified columns as whole numbers with thousands separators.
    Leaves the original df untouched (returns a copy).
    Accepts numeric or string inputs (e.g., "3,450"). Non-parsable values become blank in HTML ("").
    """
    if df is None or df.empty:
        return df

    out = df.copy()

    for c in cols:
        if c not in out.columns:
            continue

        # Convert to numeric safely even if the column already contains commas/strings
        s = (
            out[c]
            .astype("string")
            .str.replace(",", "", regex=False)
            .str.strip()
        )
        s_num = pd.to_numeric(s, errors="coerce")

        # Whole numbers with commas; blanks for NaN
        out[c] = s_num.map(lambda x: "" if pd.isna(x) else f"{int(round(x)):,}")

    return out

LAST_SOURCE_FILE = "N/A"

def load_raw_events(data_dir: Path) -> tuple[pd.DataFrame, str]:
    # Grab all CSVs
    files = sorted(data_dir.glob("*.csv"))

    # Keep only weekly log files (ignore roster.csv)
    log_files = [p for p in files if p.name.lower().endswith(" log.csv")]

    if not log_files:
        raise SystemExit(f"No log CSV files found in {data_dir.resolve()}")

    # Pick newest by modified time
    log_files.sort(key=lambda p: p.stat().st_mtime)

    files = log_files

    
    global LAST_SOURCE_FILE
    LAST_SOURCE_FILE = files[-1].name

    dfs = []
    for f in files:
        date_text = f.stem.split()[0]
        tournament_date = pd.to_datetime(date_text, format="%m.%d.%y", errors="coerce").date()

        df = pd.read_csv(f)
        df["SourceFile"] = f.name
        df["TournamentDate"] = tournament_date
        dfs.append(df)

    raw = pd.concat(dfs, ignore_index=True)
    return raw, LAST_SOURCE_FILE

def build_tables(raw: pd.DataFrame) -> dict[str, pd.DataFrame]:
    # ---- TournamentPlayers (from BuyIn events) ----
    buyins = raw.loc[raw["Event"].astype(str).str.upper().str.strip() == "BUYIN"].copy()

    if not buyins.empty:
        buyins["BuyInAmount"] = (
            buyins["Amount"]
            .astype(str)
            .str.replace("$", "", regex=False)
            .str.split()
            .str[0]
        )
        buyins["BuyInAmount"] = pd.to_numeric(buyins["BuyInAmount"], errors="coerce")
        buyins = buyins.rename(columns={"Players": "Player"})
        buyins = buyins[["SourceFile", "TournamentDate", "Player", "BuyInAmount", "Time"]].rename(
            columns={"Time": "BuyInTime"}
        )
    else:
        buyins = pd.DataFrame(columns=["SourceFile", "TournamentDate", "Player", "BuyInAmount", "BuyInTime"])

    buyins = buyins.loc[:, ~buyins.columns.duplicated()]

    tournament_players = (
        buyins.groupby(["SourceFile", "TournamentDate", "Player"], as_index=False)["BuyInAmount"].max()
    )

    weekly_summary = (
        tournament_players.groupby(["SourceFile", "TournamentDate"], as_index=False)
        .agg(PlayersCount=("Player", "count"))
    )

    # ---- Week lookup (TournamentDate -> Week #) ----
    week_lookup = (
        weekly_summary.sort_values("TournamentDate")
        .drop_duplicates("TournamentDate")
        .assign(Week=lambda df: range(1, len(df) + 1))
        [["TournamentDate", "Week"]]
    )

    # ---- WeeklyTournaments (start/end times from TOURNAMENT rows if present; optional) ----
    ev = raw.copy()
    ev["EventClean"] = ev["Event"].astype(str).str.upper().str.strip()
    trows = ev[ev["EventClean"].str.contains("TOURNAMENT", na=False)].copy()

    if not trows.empty:
        start = (
            trows[trows["EventClean"].str.contains("START", na=False)]
            .groupby("SourceFile", as_index=False)
            .agg(StartTime=("Time", "min"))
        )
        end = (
            trows[trows["EventClean"].str.contains("END", na=False)]
            .groupby("SourceFile", as_index=False)
            .agg(EndTime=("Time", "max"))
        )
        weekly_tournaments = pd.merge(start, end, on="SourceFile", how="left")
        weekly_tournaments = pd.merge(
            weekly_tournaments,
            weekly_summary[["SourceFile", "TournamentDate"]],
            on="SourceFile",
            how="left",
        )
    else:
        weekly_tournaments = weekly_summary[["SourceFile", "TournamentDate"]].copy()
        weekly_tournaments["StartTime"] = pd.NaT
        weekly_tournaments["EndTime"] = pd.NaT

    # ---- Eliminations ----
    elims = raw.loc[raw["Event"].astype(str).str.upper().str.strip() == "ELIMINATED"].copy()

    if not elims.empty:
        elims = elims.rename(
            columns={
                "Players": "EliminatedPlayer",        # busted player
                "Eliminated By": "EliminatorPlayer",  # who busted them
                "Time": "EliminationTime",
            }
        )

        # build a sortable datetime for elimination order
        elims["EliminationDT"] = parse_dt_series(elims["TournamentDate"].astype(str) + " " + elims["EliminationTime"].astype(str))

        elims = elims[["SourceFile", "TournamentDate", "EliminationTime", "EliminationDT",
                    "EliminatedPlayer", "EliminatorPlayer"]]

        # VERY IMPORTANT: one row per eliminated player per tournament (prevents duplicates blowing up places)
        elims = elims.sort_values(["SourceFile", "TournamentDate", "EliminationDT"], na_position="last")
        elims = elims.drop_duplicates(subset=["SourceFile", "TournamentDate", "EliminatedPlayer"], keep="first")
    else:
        elims = pd.DataFrame(
            columns=["SourceFile", "TournamentDate", "EliminationTime", "EliminationDT",
                    "EliminatedPlayer", "EliminatorPlayer"]
        )

    # ---- FinishPositions (place = reverse elimination order; winner = not eliminated) ----
    if not elims.empty:
        fp = elims.sort_values(["SourceFile", "TournamentDate", "EliminationDT"], na_position="last").copy()
        fp = fp.merge(weekly_summary, on=["SourceFile", "TournamentDate"], how="left")

        fp["ElimOrder"] = fp.groupby(["SourceFile", "TournamentDate"]).cumcount() + 1
        fp["Place"] = fp["PlayersCount"] - fp["ElimOrder"] + 1

        finish_positions = fp[["SourceFile", "TournamentDate", "EliminatedPlayer", "Place", "PlayersCount"]] \
            .rename(columns={"EliminatedPlayer": "Player"})
    else:
        finish_positions = pd.DataFrame(columns=["SourceFile", "TournamentDate", "Player", "Place", "PlayersCount"])

    # Add winner rows (players who bought in but do NOT appear in FinishPositions for THAT tournament)
    if not tournament_players.empty:
        winners = pd.merge(
            tournament_players[["SourceFile", "TournamentDate", "Player"]],
            finish_positions[["SourceFile", "TournamentDate", "Player"]],
            on=["SourceFile", "TournamentDate", "Player"],
            how="left",
            indicator=True,
        )

        winners = winners[winners["_merge"] == "left_only"].drop(columns=["_merge"])

        winners = pd.merge(
            winners,
            weekly_summary,
            on=["SourceFile", "TournamentDate"],
            how="left"
        )

        winners["Place"] = 1

        finish_positions = pd.concat(
            [finish_positions, winners[["SourceFile", "TournamentDate", "Player", "Place", "PlayersCount"]]],
            ignore_index=True
        )
    else:
        winners = pd.DataFrame(columns=["SourceFile", "TournamentDate", "Player", "PlayersCount", "Place"])

    # final sort for readability
    finish_positions = finish_positions.sort_values(["SourceFile", "TournamentDate", "Place", "Player"]).reset_index(drop=True)

    # ---- Weekly points (0.5 per place; winner gets PlayersCount*0.5) ----
    if not finish_positions.empty:
        finish_positions["Points"] = (finish_positions["PlayersCount"] - finish_positions["Place"] + 1) * 0.5
    if not winners.empty:
        winners["Points"] = winners["PlayersCount"] * 0.5

    # ---- Weekly points (0.5 per place; winner gets PlayersCount*0.5) ----
    finish_points = finish_positions[["SourceFile", "TournamentDate", "Player", "Points"]].copy()

    # wi0nners may be empty OR may not have Points depending on earlier logic
    if winners is None or winners.empty:
        winners_points = pd.DataFrame(columns=["SourceFile", "TournamentDate", "Player", "Points"])
    else:
        # if somehow Points is missing, create it (keeps code from blowing up)
        if "Points" not in winners.columns:
            winners["Points"] = winners.get("PlayersCount", 0) * 0.5
        winners_points = winners[["SourceFile", "TournamentDate", "Player", "Points"]].copy()

    weekly_points = pd.concat([finish_points, winners_points], ignore_index=True)

    if not weekly_points.empty:
        weekly_points = (
            weekly_points.groupby(["SourceFile", "TournamentDate", "Player"], as_index=False)["Points"].max()
        )
    
            # --- Weekly payouts (top 3) ---
   
    PAYOUT_SPLIT = [0.45, 0.35, 0.2]

    weekly_points["Payout"] = 0

    # We assume weekly_points already has a rank column called "Finish Place"
    # and one row per player per week.
    weekly_points["Finish Place"] = weekly_points.groupby(["SourceFile","TournamentDate"])["Points"].rank(ascending=False, method="first").astype(int)
    for (sf, dt), grp in weekly_points.groupby(["SourceFile", "TournamentDate"]):
        pot = grp["Player"].nunique() * 20  # $20 per player buy-in; adjust if different
        top3 = grp.sort_values("Points", ascending=False).head(3)
        if len(top3) == 0:
            continue

        payouts = payouts_multiple_of_20(pot, PAYOUT_SPLIT, increment=20)

        # Assign payouts to finish places 1/2/3 if present
        for i, (_, row) in enumerate(top3.iterrows()):
            weekly_points.loc[row.name, "Payout"] = payouts[i]

    # ---- Player Weekly Metrics (analytics fact table) ----
    weeks = weekly_tournaments[["SourceFile", "TournamentDate"]].drop_duplicates()
    players = pd.DataFrame({"Player": pd.unique(tournament_players["Player"])}) if not tournament_players.empty else pd.DataFrame({"Player": []})

    scaffold = (
        players.assign(_k=1)
        .merge(weeks.assign(_k=1), on="_k")
        .drop(columns="_k")
    )

    player_weekly_metrics = scaffold.merge(
        weekly_points,
        on=["SourceFile", "TournamentDate", "Player"],
        how="left",
    )

    player_weekly_metrics["Points"] = player_weekly_metrics["Points"].fillna(0)
    player_weekly_metrics["Played"] = player_weekly_metrics["Points"] > 0

    player_weekly_metrics = player_weekly_metrics.sort_values(
        ["TournamentDate", "Points", "Player"],
        ascending=[True, False, True],
    )

    # Finish Place: only assign ranks to players who played
    player_weekly_metrics["Finish Place"] = None
    mask = player_weekly_metrics["Played"]
    player_weekly_metrics.loc[mask, "Finish Place"] = (
        player_weekly_metrics.loc[mask]
        .groupby("TournamentDate")
        .cumcount()
        .add(1)
        .astype(int)
    )
    player_weekly_metrics["Finish Place"] = player_weekly_metrics["Finish Place"].fillna("Did Not Play")

    players_per_week = (
        player_weekly_metrics[mask]
        .groupby("TournamentDate")["Player"]
        .nunique()
        .rename("PlayersCount")
        .reset_index()
    )

    player_weekly_metrics = player_weekly_metrics.merge(players_per_week, on="TournamentDate", how="left")

    def finish_percentile(row):
        if row["Finish Place"] == "Did Not Play":
            return None
        pc = row["PlayersCount"]
        if pd.isna(pc) or pc <= 1:
            return 1.0
        return 1 - ((int(row["Finish Place"]) - 1) / (pc - 1))

    player_weekly_metrics["Finish Percentile"] = player_weekly_metrics.apply(finish_percentile, axis=1)

    # ---- Season totals (leaderboard) ----
  
    # Bottom-2-drop should consider ALL weeks so far (missed weeks = 0)
    wp_raw = weekly_points.copy()
    wp_raw["Points"] = pd.to_numeric(wp_raw["Points"], errors="coerce").fillna(0.0)

    # season weeks so far
    season_weeks = sorted(wp_raw["TournamentDate"].dropna().unique())

    # all players (use roster if you want later; for now, players seen in data)
    all_players = sorted(tournament_players["Player"].dropna().astype(str).unique())

    # scaffold: every player x every week date
    wp_full = (
        pd.DataFrame({"Player": all_players})
        .assign(_k=1)
        .merge(pd.DataFrame({"TournamentDate": season_weeks}).assign(_k=1), on="_k")
        .drop(columns="_k")
    )

    # bring in points; missing = 0
    wp_full = wp_full.merge(
        wp_raw[["Player", "TournamentDate", "Points"]],
        on=["Player", "TournamentDate"],
        how="left",
    )
    wp_full["Points"] = wp_full["Points"].fillna(0.0)

    # total points (zeros don't change totals)
    total_points = (
        wp_full.groupby("Player", as_index=False)["Points"]
        .sum()
        .rename(columns={"Points": "Total Points"})
    )

    # weeks played = weeks with >0 points
    weeks_played = (
        wp_full.assign(Played=wp_full["Points"] > 0)
        .groupby("Player", as_index=False)["Played"]
        .sum()
        .rename(columns={"Played": "Total Weeks Played"})
    )

    def bottom2_dropped_sum(s: pd.Series) -> float:
        vals = sorted([float(v) for v in s.fillna(0.0).tolist()])  # includes zeros for missed weeks
        if len(vals) <= 2:
            return float(sum(vals))
        return float(sum(vals[2:]))

    dropped = (
        wp_full.groupby("Player")["Points"]
        .apply(bottom2_dropped_sum)
        .reset_index()
        .rename(columns={"Points": "Total Points (bottom 2 dropped)"})
    )

    season_totals = (
        total_points
        .merge(dropped, on="Player", how="left")
        .merge(weeks_played, on="Player", how="left")
        .sort_values(
            ["Total Points (bottom 2 dropped)", "Total Points", "Total Weeks Played", "Player"],
            ascending=[False, False, False, True],
        )
        .reset_index(drop=True)
    )
    # --- Add total money won (from weekly payouts) ---
    money_won = (
        weekly_points.groupby("Player", as_index=False)["Payout"]
        .sum()
        .rename(columns={"Payout": "MoneyWon"})
    )

    season_totals = season_totals.merge(money_won, on="Player", how="left")
    season_totals["MoneyWon"] = season_totals["MoneyWon"].fillna(0).astype(int)


    season_totals.insert(0, "Season Rank", season_totals.index + 1)

    chip_and_chair = build_chip_and_chair(
    season_totals=season_totals,
    elims=elims,  # your eliminations dataframe inside build_tables
    chip_per_total_elim=50,  # <-- adjust if your rule isn't 50 per elim
)

    # ---- Survival Season Averages (Avg minutes survived) ----
    survival = pd.DataFrame(columns=["Player", "WeeksPlayed", "AvgMinutesSurvived", "AvgSurvivalPercent"])

    # We can only compute if TOURNAMENT start/end exists
    wt = weekly_tournaments.copy()
    if ("StartTime" in wt.columns) and ("EndTime" in wt.columns) and (not wt.empty):
        wt["TournamentDate"] = parse_dt_series(wt["TournamentDate"]).dt.date
        wt["StartDT"] = parse_dt_series(wt["TournamentDate"].astype(str) + " " + wt["StartTime"].astype(str))


        wt["EndDT"] = parse_dt_series(wt["TournamentDate"].astype(str) + " " + wt["EndTime"].astype(str))

        # If the tournament crosses midnight, EndDT will parse earlier than StartDT
        mask = wt["EndDT"].notna() & wt["StartDT"].notna() & (wt["EndDT"] < wt["StartDT"])
        wt.loc[mask, "EndDT"] = wt.loc[mask, "EndDT"] + pd.Timedelta(days=1)

        wt["TournamentMinutes"] = (wt["EndDT"] - wt["StartDT"]).dt.total_seconds() / 60.0

        elim_surv = pd.DataFrame(columns=["TournamentDate", "Player", "MinutesSurvived", "TournamentMinutes"])
        if not elims.empty:
            e = elims.copy()
            e["TournamentDate"] = parse_dt_series(e["TournamentDate"]).dt.date
            e["EliminationDT"] = parse_dt_series(
                e["TournamentDate"].astype(str) + " " + e["EliminationTime"].astype(str))
            
            e = e.merge(wt[["SourceFile", "TournamentDate", "StartDT", "TournamentMinutes"]], on=["SourceFile", "TournamentDate"], how="left")
            e["MinutesSurvived"] = (e["EliminationDT"] - e["StartDT"]).dt.total_seconds() / 60.0
            e["Player"] = e["EliminatedPlayer"]
            elim_surv = e[["TournamentDate", "Player", "MinutesSurvived", "TournamentMinutes"]].copy()

        win_surv = pd.DataFrame(columns=["TournamentDate", "Player", "MinutesSurvived", "TournamentMinutes"])
        if not winners.empty:
            w = winners.copy()
            w["TournamentDate"] = parse_dt_series(w["TournamentDate"]).dt.date
            w = w.merge(wt[["SourceFile", "TournamentDate", "TournamentMinutes"]], on=["SourceFile", "TournamentDate"], how="left")
            w["MinutesSurvived"] = w["TournamentMinutes"]
            win_surv = w[["TournamentDate", "Player", "MinutesSurvived", "TournamentMinutes"]].copy()

        surv_rows = pd.concat([elim_surv, win_surv], ignore_index=True)
        if not surv_rows.empty:
            surv_rows["SurvivalPercent"] = surv_rows["MinutesSurvived"] / surv_rows["TournamentMinutes"]
            surv_rows["TournamentDate"] = pd.to_datetime(surv_rows["TournamentDate"], errors="coerce").dt.date
            week_lookup["TournamentDate"] = pd.to_datetime(week_lookup["TournamentDate"], errors="coerce").dt.date
            surv_rows = surv_rows.assign(TournamentDate=pd.to_datetime(surv_rows["TournamentDate"], errors="coerce").dt.normalize())
            week_lookup = week_lookup.assign(TournamentDate=pd.to_datetime(week_lookup["TournamentDate"], errors="coerce").dt.normalize())
            surv_rows = surv_rows.merge(week_lookup, on="TournamentDate", how="left")

            survival = (
                surv_rows.groupby("Player", as_index=False)
                .agg(
                    WeeksPlayed=("Week", "nunique"),
                    AvgMinutesSurvived=("MinutesSurvived", "mean"),
                    AvgSurvivalPercent=("SurvivalPercent", "mean"),
                )
                .sort_values(["AvgMinutesSurvived", "Player"], ascending=[False, True])
                .reset_index(drop=True)
            )
            survival["AvgMinutesSurvived"] = survival["AvgMinutesSurvived"].round(1)
            survival["AvgSurvivalPercent"] = survival["AvgSurvivalPercent"].round(3)

    # Winners display without SourceFile (but keep original winners for joins already done)
    winners_display = winners.drop(columns=["SourceFile"]) if ("SourceFile" in winners.columns) else winners

    chip_and_chair = build_chip_and_chair(
        season_totals=season_totals,
        elims=elims,
    )

    return {
        "Raw_LogEvents": raw,
        "Buyins": buyins,
        "TournamentPlayers": tournament_players,
        "WeeklySummary": weekly_summary,
        "WeeklyTournaments": weekly_tournaments,
        "Eliminations": elims,
        "FinishPositions": finish_positions,
        "WeeklyPoints": weekly_points,
        "PlayerWeeklyMetrics": player_weekly_metrics,
        "SeasonTotals": season_totals,
        "Survival": survival,
        "Winners": winners_display,
        "ChipAndChair": chip_and_chair,
    }
def build_chip_and_chair(
    season_totals: pd.DataFrame,
    elims: pd.DataFrame,
    season_points_chip_multiplier: int = 150,
    chip_per_total_elim: int = 50,   # <-- if your rule is different, change this one number
    chip_per_repeat_elim: int = 100,
    chip_per_hv_elim: int = 250,
    base_stack: int = 6500,
) -> pd.DataFrame:
    """
    Replicates the Power Query Chip & a Chair dashboard logic.
    """

    # ---- SeasonTotals_Drop2 equivalent ----
    # Expect season_totals has:
    # - Player
    # - Total Points (bottom 2 dropped)
    # - Season Rank (may be non-dense; we'll recompute dense rank like PQ)
    if season_totals is None or season_totals.empty:
        return pd.DataFrame()

    st = season_totals.copy()

    drop2_col = "Total Points (bottom 2 dropped)"
    if drop2_col not in st.columns:
        raise ValueError(f"Expected '{drop2_col}' in SeasonTotals.")

    st = st[["Player", drop2_col]].rename(columns={drop2_col: "TotalPoints_drop2"})

    # ---- SeasonPointsChips ----
    season_points_chips = st.copy()
    season_points_chips["SeasonPointsChips"] = season_points_chips["TotalPoints_drop2"] * season_points_chip_multiplier
    season_points_chips = season_points_chips[["Player", "SeasonPointsChips"]]

    # ---- Elim_Counts (intended) ----
    # Total eliminations credited to EliminatorPlayer
    elim_counts = pd.DataFrame(columns=["Player", "TotalElimsCount", "ChipsFromTotalElims"])
    if elims is not None and not elims.empty and "EliminatorPlayer" in elims.columns:
        e = elims.copy()

        # filter blanks/nulls like PQ
        e["EliminatorPlayer"] = e["EliminatorPlayer"].astype(str).str.strip()
        e["EliminatedPlayer"] = e["EliminatedPlayer"].astype(str).str.strip()

        e = e[(e["EliminatorPlayer"] != "") & (e["EliminatorPlayer"].str.lower() != "nan")]
        e = e[(e["EliminatedPlayer"] != "") & (e["EliminatedPlayer"].str.lower() != "nan")]

        elim_counts = (
            e.groupby("EliminatorPlayer", as_index=False)
             .size()
             .rename(columns={"EliminatorPlayer": "Player", "size": "TotalElimsCount"})
        )
        elim_counts["ChipsFromTotalElims"] = elim_counts["TotalElimsCount"] * chip_per_total_elim

    # ---- Repeat_Elims ----
    repeat_elims = pd.DataFrame(columns=["Player", "RepeatElimTotalCount", "RepeatElimChips"])
    if elims is not None and not elims.empty:
        r = elims[["EliminatedPlayer", "EliminatorPlayer"]].copy()

        r["EliminatorPlayer"] = r["EliminatorPlayer"].astype(str).str.strip()
        r["EliminatedPlayer"] = r["EliminatedPlayer"].astype(str).str.strip()

        r = r[(r["EliminatorPlayer"] != "") & (r["EliminatorPlayer"].str.lower() != "nan")]
        r = r[(r["EliminatedPlayer"] != "") & (r["EliminatedPlayer"].str.lower() != "nan")]

        grouped = (
            r.groupby(["EliminatorPlayer", "EliminatedPlayer"], as_index=False)
             .size()
             .rename(columns={"size": "ElimCount"})
        )
        grouped["RepeatElimCount"] = grouped["ElimCount"].apply(lambda x: x - 1 if x > 1 else 0)

        repeat_elims = (
            grouped.groupby("EliminatorPlayer", as_index=False)
                   .agg(RepeatElimTotalCount=("RepeatElimCount", "sum"))
                   .rename(columns={"EliminatorPlayer": "Player"})
        )
        repeat_elims["RepeatElimChips"] = repeat_elims["RepeatElimTotalCount"] * chip_per_repeat_elim

    # ---- HV_Elims ----
    # Victim rank <= 3 AND eliminator rank > 3
    hv_elims = pd.DataFrame(columns=["Player", "HVElimTotalCount", "ChipsFromHVElims"])
    if elims is not None and not elims.empty:
        # Build rank lookup from drop2 standings (dense rank like PQ distinct list)
        rank_df = st.copy()
        # dense rank: ties share the same rank number
        rank_df["SeasonRank"] = rank_df["TotalPoints_drop2"].rank(method="dense", ascending=False).astype(int)
        rank_lookup = rank_df[["Player", "SeasonRank"]]

        hv = elims[["EliminatedPlayer", "EliminatorPlayer"]].copy()
        hv["EliminatorPlayer"] = hv["EliminatorPlayer"].astype(str).str.strip()
        hv["EliminatedPlayer"] = hv["EliminatedPlayer"].astype(str).str.strip()

        hv = hv[(hv["EliminatorPlayer"] != "") & (hv["EliminatorPlayer"].str.lower() != "nan")]
        hv = hv[(hv["EliminatedPlayer"] != "") & (hv["EliminatedPlayer"].str.lower() != "nan")]

        # victim rank
        hv = hv.merge(rank_lookup, left_on="EliminatedPlayer", right_on="Player", how="left")
        hv = hv.rename(columns={"SeasonRank": "VictimRank"}).drop(columns=["Player"])

        # keep victims rank <= 3
        hv = hv[hv["VictimRank"].fillna(999) <= 3]

        # eliminator rank
        hv = hv.merge(rank_lookup, left_on="EliminatorPlayer", right_on="Player", how="left")
        hv = hv.rename(columns={"SeasonRank": "EliminatorRank"}).drop(columns=["Player"])

        # keep eliminators rank > 3
        hv = hv[hv["EliminatorRank"].fillna(0) > 3]

        hv_elims = (
            hv.groupby("EliminatorPlayer", as_index=False)
              .size()
              .rename(columns={"EliminatorPlayer": "Player", "size": "HVElimTotalCount"})
        )
        hv_elims["ChipsFromHVElims"] = hv_elims["HVElimTotalCount"] * chip_per_hv_elim

    # ---- Merge all together (like PQ) ----
    out = st.merge(season_points_chips, on="Player", how="left")
    out = out.merge(elim_counts, on="Player", how="left")
    out = out.merge(repeat_elims, on="Player", how="left")
    out = out.merge(hv_elims, on="Player", how="left")

    # fill nulls with 0 (like PQ ReplaceValue null -> 0)
    for c in ["SeasonPointsChips", "TotalElimsCount", "ChipsFromTotalElims",
              "RepeatElimTotalCount", "RepeatElimChips", "HVElimTotalCount", "ChipsFromHVElims"]:
        if c in out.columns:
            out[c] = out[c].fillna(0)

    out["BaseChipAndChairStack"] = base_stack
    out["TotalChipAndChairStack"] = (
        out["BaseChipAndChairStack"]
        + out["SeasonPointsChips"]
        + out["ChipsFromTotalElims"]
        + out["RepeatElimChips"]
        + out["ChipsFromHVElims"]
    )

    # Sort like PQ: by TotalPoints_drop2 desc, then TotalElimsCount desc
    out = out.sort_values(["TotalPoints_drop2", "TotalElimsCount", "Player"], ascending=[False, False, True]).reset_index(drop=True)

    # Recompute SeasonRank like PQ: dense rank off distinct TotalPoints_drop2
    out["SeasonRank"] = out["TotalPoints_drop2"].rank(method="dense", ascending=False).astype(int)

    # Nice column order
    col_order = [
    "Player",
    "TotalChipAndChairStack",
    "BaseChipAndChairStack",
    "SeasonPointsChips",
    "TotalElimsCount",
    "ChipsFromTotalElims",
    "RepeatElimTotalCount",
    "RepeatElimChips",
    "HVElimTotalCount",
    "ChipsFromHVElims",
    ]

    out = out.sort_values("TotalChipAndChairStack", ascending=False).reset_index(drop=True)
    out = out[[c for c in col_order if c in out.columns]]

    out = out.rename(columns={
    
    "SeasonPointsChips": "Chips From Season Points",
    "TotalElimsCount": "Total Eliminations",
    "ChipsFromTotalElims": "Chips From Total Elims",
    "RepeatElimTotalCount": "Repeat Elim Count",
    "RepeatElimChips": "Chips From Repeat Elims",
    "HVElimTotalCount": "High Value Elim Count",
    "ChipsFromHVElims": "Chips From High Value Elims",
    "BaseChipAndChairStack": "Base Stack",
    "TotalChipAndChairStack": "Total Stack",
})

    # --- Format chip columns as whole numbers with commas ---
    chip_cols = [
        "Total Stack",
        "Chips From Season Points",
        "Chips From Total Elims",
        "Chips From Repeat Elims",
        "Chips From High Value Elims",
]

    for col in chip_cols:
        if col in out.columns:
            out[col] = out[col].apply(
                lambda x: "" if pd.isna(x) else f"{int(x):,}"
            )

    return out

def write_season_json(tables: dict, out_path: Path):
    """
    Convert the full league state into a single JSON file
    that your new website can consume.
    """

    # --- Extract tables from build_tables() ---
    raw = tables["Raw_LogEvents"]
    season_totals = tables["SeasonTotals"]
    chip_and_chair = tables["ChipAndChair"]
    weekly_points = tables["WeeklyPoints"]
    finish_positions = tables["FinishPositions"]
    eliminations = tables["Eliminations"]
    weekly_summary = tables["WeeklySummary"]
    weekly_tournaments = tables["WeeklyTournaments"]

    # --- Build events array ---
    events = []
    for (sf, dt), grp in finish_positions.groupby(["SourceFile", "TournamentDate"]):
        dt_str = str(dt)

        # players in this event
        players = sorted(grp["Player"].unique())

        # finish order
        results = (
            grp.sort_values("Place")
               .assign(Points=lambda df: df["Points"])
               [["Place", "Player", "Points"]]
               .to_dict(orient="records")
        )

        # eliminations
        elim_rows = eliminations[
            (eliminations["SourceFile"] == sf) &
            (eliminations["TournamentDate"] == dt)
        ].sort_values("EliminationDT")

        elim_list = elim_rows.assign(
            order=lambda df: range(1, len(df) + 1)
        )[["order", "EliminatedPlayer", "EliminatorPlayer", "EliminationTime"]] \
         .rename(columns={
             "EliminatedPlayer": "player",
             "EliminatorPlayer": "eliminated_by",
             "EliminationTime": "time"
         }).to_dict(orient="records")

        # payouts
        payouts = (
            weekly_points[(weekly_points["SourceFile"] == sf) &
                          (weekly_points["TournamentDate"] == dt)]
            .sort_values("Finish Place")
            .head(3)[["Finish Place", "Player", "Payout"]]
            .rename(columns={"Finish Place": "place", "Player": "player", "Payout": "amount"})
            .to_dict(orient="records")
        )

        events.append({
            "source_file": sf,
            "date": dt_str,
            "total_players": len(players),
            "players": players,
            "results": results,
            "eliminations": elim_list,
            "payouts": payouts,
            "winner": results[0]["Player"] if results else None
        })

    # --- Season Totals ---
    season_totals_json = season_totals.rename(columns={
        "Season Rank": "rank",
        "Player": "player",
        "Total Points": "total_points",
        "Total Points (bottom 2 dropped)": "total_points_drop2",
        "Total Weeks Played": "weeks_played",
        "MoneyWon": "money_won"
    }).to_dict(orient="records")

    # --- Chip & Chair ---
    chip_json = chip_and_chair.rename(columns={
        "Player": "player",
        "Total Stack": "total_stack",
        "Base Stack": "base_stack",
        "Chips From Season Points": "chips_from_season_points",
        "Total Eliminations": "total_eliminations",
        "Chips From Total Elims": "chips_from_total_elims",
        "Repeat Elim Count": "repeat_elim_count",
        "Chips From Repeat Elims": "chips_from_repeat_elims",
        "High Value Elim Count": "high_value_elim_count",
        "Chips From High Value Elims": "chips_from_high_value_elims"
    }).to_dict(orient="records")

    # --- Analytics placeholder ---
    analytics = {
        "most_points": season_totals_json[0]["player"] if season_totals_json else None,
        "events_played": len(events),
        "average_field_size": float(weekly_summary["PlayersCount"].mean())
    }

    # --- Final JSON structure ---
    out = {
        "season_id": "spring_2026",
        "season_name": "Spring Season 2026",
        "last_updated": BUILD_TS_EST,
        "latest_source_file": LAST_SOURCE_FILE,
        "events": events,
        "weekly_points": events,
        "season_totals": season_totals_json,
        "chip_and_chair": chip_json,
        "analytics": analytics
    }

    out_path.write_text(json.dumps(out, indent=2))

def build_weekly_section(weekly: pd.DataFrame) -> str:
    """Return HTML for clickable week sections (no SourceFile)."""
    if weekly is None or weekly.empty:
        return "<p class='note'>No weekly points yet.</p>"

    from pathlib import Path

    df = weekly.copy()

    # Drop SourceFile from display
    # Sort within each week so finish place is deterministic
    df = df.sort_values(
        ["TournamentDate", "Points", "Player"],
        ascending=[True, False, True],
    )

    # Finish Place per week: 1 = highest points
    df["Finish Place"] = (
        df.groupby("TournamentDate")["Points"]
          .rank(method="first", ascending=False)
          .astype(int)
    )
    df = df[["TournamentDate", "Finish Place", "Player", "Points", "Payout"]]

    if "SourceFile" in df.columns:
        df = df.drop(columns=["SourceFile"])

    if "TournamentDate" not in df.columns:
        return df.to_html(index=False, escape=False)

    # --- Load full league roster (so non-players can appear with 0 points) ---
    roster_path = (Path(__file__).resolve().parent.parent / "data" / "roster.csv")

    if roster_path.exists():
        roster = pd.read_csv(roster_path)
        all_players = sorted(roster["Player"].dropna().astype(str).unique())
    else:
        # fallback: only players seen in data
        all_players = sorted(df["Player"].dropna().astype(str).unique())

# --- Rebuild df week-by-week, adding missing players with 0 points and Finish Place ---
    rows = []
    for date, wk in df.groupby("TournamentDate"):
        wk = wk[["Finish Place","Player", "Points", "Payout"]].copy()

        played = set(wk["Player"].dropna().astype(str))
        missing = [p for p in all_players if p not in played]

        if missing:
            wk = pd.concat(
            [wk, pd.DataFrame({"Finish Place": 999, "Player": missing, "Points": 0, "Payout": 0})],
                ignore_index=True,
            )
        wk = wk.sort_values(
            ["Finish Place", "Points", "Player"],
            ascending=[True, False, True],
        ).reset_index(drop=True)

        # Re-number finish places after sorting (1..N)
        # Re-number finish places cleanly after sorting (1..N)
        wk["Finish Place"] = range(1, len(wk) + 1)

        # Format payout as currency and hide zeros (HTML display only)
        wk["Payout"] = wk["Payout"].apply(
            lambda x: f"${int(x):,}" if pd.notna(x) and x > 0 else ""
        )

        # Label non-players cleanly
        

        wk.insert(0, "TournamentDate", date)

        rows.append(wk)

    df = pd.concat(rows, ignore_index=True)

    dates = sorted(df["TournamentDate"].dropna().unique())
    week_num = {d: i + 1 for i, d in enumerate(dates)}

    nav_links = []
    for d in reversed(dates):
        wn = week_num[d]
        nav_links.append(f"<a href='#week{wn}'>Week {wn}</a>")

    nav_html = "<div class='weeknav'><strong>Jump to:</strong> " + " | ".join(nav_links) + "</div>"

    sections = []
    for d in reversed(dates):
        wn = week_num[d]
        wk = df[df["TournamentDate"] == d].copy()
        wk = wk[["Finish Place", "Player", "Points", "Payout"]].sort_values(
            ["Finish Place", "Points", "Player"], ascending=[True, False, True]
        )

        sections.append(
            f"""
<details id="week{wn}">
  <summary><strong>Week {wn} Results</strong> ({d})</summary>
  {wk.to_html(index=False, escape=False)}
</details>
"""
        )

    return nav_html + "\n" + "\n".join(sections)


def write_outputs(tables: dict, last_source_file: str) -> None:
    """
    Backend responsibility:
      - write processed CSV tables for debugging / analytics
      - DO NOT generate HTML (frontend owns UI)
    """
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    for name, df in tables.items():
        try:
            df.to_csv(TABLES_DIR / f"{name}.csv", index=False)
        except Exception as e:
            print(f"⚠️ Skipped CSV for {name}: {e}")

    print(f"✅ Wrote CSV tables to: {TABLES_DIR}")
    print(f"Latest source file: {last_source_file}")


def main():
    raw, last_source_file = load_raw_events(DATA_DIR)
    tables = build_tables(raw)

    write_season_json(tables, JSON_OUTPUT_PATH)
    write_outputs(tables, last_source_file)


if __name__ == "__main__":
    main()