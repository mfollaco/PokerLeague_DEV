from curses import raw
from importlib.resources import files
from pathlib import Path
import pandas as pd
from datetime import datetime

DATA_DIR = Path("data")
OUT_DIR = Path("output")
TABLES_DIR = OUT_DIR / "tables"


from datetime import datetime

from zoneinfo import ZoneInfo

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
        out.loc[:, f"{c}_fmt"] = s_num.map(lambda x: "" if pd.isna(x) else f"{int(round(x)):,}")
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
        buyins.loc[:, "BuyInAmount"] = (
            buyins.loc[:, "Amount"]
                .astype(str)
                .str.replace("$", "", regex=False)
                .str.split()
                .str[0]
)

    buyins.loc[:, "BuyInAmount"] = pd.to_numeric(
        buyins.loc[:, "BuyInAmount"],
        errors="coerce"
    )

    buyins = buyins.loc[:, ~buyins.columns.duplicated()]

    # --- normalize Player column before groupby ---
    if "Player" not in buyins.columns:
        if "Players" in buyins.columns:
            buyins = buyins.rename(columns={"Players": "Player"})
        elif "player" in buyins.columns:
            buyins = buyins.rename(columns={"player": "Player"})
        else:
            raise KeyError(f"Buyins is missing 'Player'. Columns are: {list(buyins.columns)}")

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
        [["TournamentDate"]]
        .copy()
    )

    week_lookup.loc[:, "Week"] = range(1, len(week_lookup) + 1)

    # ---- WeeklyTournaments (start/end times from TOURNAMENT rows if present; optional) ----
    ev = raw.loc[:, :].copy()
    ev.loc[:, "EventClean"] = ev["Event"].astype(str).str.upper().str.strip()
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
    def _clean_col(c: object) -> str:
        s = str(c)
        # strip normal whitespace + remove common invisible junk
        return (
            s.replace("\ufeff", "")   # BOM
            .replace("\u200b", "")   # zero-width space
            .replace("\xa0", " ")    # NBSP -> space
            .strip()
        )

    elims = elims.rename(columns=_clean_col)
    print("ELIMS COLS:", list(elims.columns))

    if not elims.empty:
        elims = elims.rename(
            columns={
                "Players": "EliminatedPlayer",        # busted player
                "Eliminated By": "EliminatorPlayer",  # who busted them
                "Time": "EliminationTime",
            }
        )

        # build a sortable datetime for elimination order
        print("ELIMS COLS DEBUG:")
        for c in elims.columns:
            print(f"{repr(c)}  len={len(c)}  codepoints={[hex(ord(ch)) for ch in c]}")
        time_col = next(
            (c for c in elims.columns if c.lower() in ("time", "eliminationtime") or c.lower().endswith("time")),
            None
        )

        if time_col is None:
            raise KeyError(f"Elims is missing a Time column. Columns: {list(elims.columns)}")

        time_str = elims[time_col].astype(str).str.strip()

        elims = elims.copy()

        elims.loc[:, "EliminationDT"] = pd.to_datetime(
            elims["TournamentDate"].astype(str) + " " + time_str,
            format="%Y-%m-%d %H:%M:%S",
            errors="coerce",
        )

        # fallback if your time strings are like "7:09 AM" (no seconds, 12-hour)
        mask = elims["EliminationDT"].isna()
        if mask.any():
            elims.loc[mask, "EliminationDT"] = pd.to_datetime(
                elims.loc[mask, "TournamentDate"].astype(str)
                + " "
                + elims.loc[mask, time_col].astype(str).str.strip(),
                format="%Y-%m-%d %I:%M %p",
                errors="coerce",
            )

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
        fp = (
            elims.sort_values(
                ["SourceFile", "TournamentDate", "EliminationDT"],
                na_position="last"
            )
            .merge(weekly_summary, on=["SourceFile", "TournamentDate"], how="left")
            .copy()
        )

        fp.loc[:, "ElimOrder"] = fp.groupby(["SourceFile", "TournamentDate"]).cumcount() + 1
        fp.loc[:, "Place"] = fp["PlayersCount"] - fp["ElimOrder"] + 1

        finish_positions = fp[["SourceFile", "TournamentDate", "EliminatedPlayer", "Place", "PlayersCount"]] \
            .rename(columns={"EliminatedPlayer": "Player"})
    else:
        finish_positions = pd.DataFrame(columns=["SourceFile", "TournamentDate", "Player", "Place", "PlayersCount"])

    # Add winner rows (players who bought in but DO NOT appear in FinishPositions for THAT tournament)
    if not tournament_players.empty:
        left_df = tournament_players.loc[:, ["SourceFile", "TournamentDate", "Player"]].copy()
        right_df = finish_positions.loc[:, ["SourceFile", "TournamentDate", "Player"]].copy()

        # left-only without merge indicator (avoids pandas internal warning)
        right_keys = pd.MultiIndex.from_frame(right_df)
        left_keys = pd.MultiIndex.from_frame(left_df)

        winners = left_df.loc[~left_keys.isin(right_keys)].copy()

        winners = winners.merge(
            weekly_summary,
            on=["SourceFile", "TournamentDate"],
            how="left",
        )

        winners.loc[:, "Place"] = 1

        finish_positions = pd.concat(
            [finish_positions, winners[["SourceFile", "TournamentDate", "Player", "Place", "PlayersCount"]]],
            ignore_index=True,
        )
    else:
        winners = pd.DataFrame(columns=["SourceFile", "TournamentDate", "Player", "PlayersCount", "Place"])
    
        
    # final sort for readability
    finish_positions = finish_positions.sort_values(["SourceFile", "TournamentDate", "Place", "Player"]).reset_index(drop=True)

    # ---- Weekly points (0.5 per place; winner gets PlayersCount*0.5) ----
    if not finish_positions.empty:
        finish_positions.loc[:, "Points"] = (finish_positions["PlayersCount"] - finish_positions["Place"] + 1) * 0.5
    if not winners.empty:
        winners.loc[:, "Points"] = winners["PlayersCount"] * 0.5

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

    # ---- Player Weekly Metrics (analytics fact table) ----
    weeks = weekly_tournaments[["SourceFile", "TournamentDate"]].drop_duplicates()
    players = pd.DataFrame({"Player": pd.unique(tournament_players["Player"])}) if not tournament_players.empty else pd.DataFrame({"Player": []})

    players_k = players.copy()
    players_k.loc[:, "_k"] = 1

    weeks_k = weeks.copy()
    weeks_k.loc[:, "_k"] = 1

    scaffold = (
        players_k.merge(weeks_k, on="_k", how="inner")
        .drop(columns="_k")
        .copy()
    )

    player_weekly_metrics = scaffold.merge(
        weekly_points,
        on=["SourceFile", "TournamentDate", "Player"],
        how="left",
    )

    player_weekly_metrics = (
        scaffold.merge(
            weekly_points,
            on=["SourceFile", "TournamentDate", "Player"],
            how="left",
        )
        .copy()
    )

    # Finish Place: only assign ranks to players who played

    # Always work on a real copy if this came from merges/slices
    player_weekly_metrics = player_weekly_metrics.copy()

    # Ensure Points exists and is numeric-ish; missing -> 0
    player_weekly_metrics.loc[:, "Points"] = pd.to_numeric(
        player_weekly_metrics.get("Points", 0),
        errors="coerce",
    ).fillna(0.0)

    # Ensure Played exists (bool)
    if "Played" not in player_weekly_metrics.columns:
        player_weekly_metrics.loc[:, "Played"] = player_weekly_metrics["Points"].gt(0)

    mask = player_weekly_metrics["Played"].fillna(False)

    # Create Finish Place with a clean dtype strategy:
    # - keep numeric finish place in a numeric column
    player_weekly_metrics.loc[:, "Finish Place"] = pd.NA
    player_weekly_metrics.loc[mask, "Finish Place"] = (
        player_weekly_metrics.loc[mask]
        .groupby("TournamentDate")
        .cumcount()
        .add(1)
    )

    # Optional: if you really want "Did Not Play" in the same column,
    # convert at the end to string to avoid dtype warnings.
    player_weekly_metrics.loc[:, "Finish Place"] = (
        player_weekly_metrics["Finish Place"]
        .astype("Int64")  # keeps ints + NA
        .astype("string")
        .fillna("Did Not Play")
    )

    players_per_week = (
        player_weekly_metrics.loc[mask]
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
    # ---- Season totals (leaderboard) ----
    # Bottom-2-drop should consider ALL weeks so far (missed weeks = 0)

    wp_raw = weekly_points.copy()

    # Make Points numeric + fill missing
    wp_raw.loc[:, "Points"] = pd.to_numeric(wp_raw.get("Points", 0), errors="coerce").fillna(0.0)

    # Season weeks so far
    season_weeks = sorted(pd.Series(wp_raw.get("TournamentDate")).dropna().unique())

    # All players (for now: players seen in tournament_players)
    all_players = sorted(tournament_players.get("Player").dropna().astype(str).unique())

    # Scaffold: every Player x every TournamentDate
    wp_full = pd.MultiIndex.from_product(
        [all_players, season_weeks],
        names=["Player", "TournamentDate"],
    ).to_frame(index=False)

    # Bring in points; missing = 0
    wp_full = wp_full.merge(
        wp_raw.loc[:, ["Player", "TournamentDate", "Points"]],
        on=["Player", "TournamentDate"],
        how="left",
    )

    wp_full.loc[:, "Points"] = wp_full["Points"].fillna(0.0)
        # =========================
    # Season totals (Bottom-2-drop uses ALL weeks so far; missed weeks = 0)
    # =========================

    # wp_full already exists above this block in your script (scaffold + merge points)
    # Ensure wp_full is a real df (not a view)
    wp_full = wp_full.copy()

    # total points (zeros don't change totals)
    total_points = (
        wp_full.groupby("Player", as_index=False)["Points"]
        .sum()
        .rename(columns={"Points": "Total Points"})
    )

    # weeks played = weeks with >0 points
    wp_full.loc[:, "Played"] = wp_full["Points"].gt(0)

    weeks_played = (
        wp_full.groupby("Player", as_index=False)["Played"]
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

    season_totals.insert(0, "Season Rank", season_totals.index + 1)

    # =========================
    # Chip & Chair (build once)
    # =========================
    chip_and_chair = build_chip_and_chair(
        season_totals=season_totals,
        elims=elims,
        # keep your params here if your function accepts them:
        # chip_per_total_elim=50,
    )

    # =========================
    # Survival Season Averages
    # =========================
    survival = pd.DataFrame(
        columns=["Player", "WeeksPlayed", "AvgMinutesSurvived", "AvgSurvivalPercent"]
    )

    wt = weekly_tournaments.copy()
    if {"StartTime", "EndTime"}.issubset(set(wt.columns)) and (not wt.empty):
        wt = wt.copy()
        wt.loc[:, "TournamentDate"] = pd.to_datetime(wt["TournamentDate"], errors="coerce").dt.date

        wt.loc[:, "StartDT"] = pd.to_datetime(
            wt["TournamentDate"].astype(str) + " " + wt["StartTime"].astype(str),
            format="%Y-%m-%d %H:%M:%S",
            errors="coerce",
        )
        wt.loc[:, "EndDT"] = pd.to_datetime(
            wt["TournamentDate"].astype(str) + " " + wt["EndTime"].astype(str),
            format="%Y-%m-%d %H:%M:%S",
            errors="coerce",
        )
        wt.loc[:, "TournamentMinutes"] = (wt["EndDT"] - wt["StartDT"]).dt.total_seconds() / 60.0

        # --- Eliminated players survival rows
        if not elims.empty:
            e = elims.copy()
            e.loc[:, "TournamentDate"] = pd.to_datetime(e["TournamentDate"], errors="coerce").dt.date

            # NOTE: you standardized to EliminationTime earlier. Use that here.
            e.loc[:, "EliminationDT"] = pd.to_datetime(
                e["TournamentDate"].astype(str) + " " + e["EliminationTime"].astype(str),
                format="%Y-%m-%d %H:%M:%S",
                errors="coerce",
            )

            e = e.merge(
                wt[["SourceFile", "TournamentDate", "StartDT", "TournamentMinutes"]],
                on=["SourceFile", "TournamentDate"],
                how="left",
            ).copy()

            e.loc[:, "MinutesSurvived"] = (e["EliminationDT"] - e["StartDT"]).dt.total_seconds() / 60.0
            e.loc[:, "Player"] = e["EliminatedPlayer"]

            elim_surv = e[["TournamentDate", "Player", "MinutesSurvived", "TournamentMinutes"]].copy()
        else:
            elim_surv = pd.DataFrame(columns=["TournamentDate", "Player", "MinutesSurvived", "TournamentMinutes"])

        # --- Winners survival rows
        if not winners.empty:
            w = winners.copy()
            w.loc[:, "TournamentDate"] = pd.to_datetime(w["TournamentDate"], errors="coerce").dt.date

            w = w.merge(
                wt[["SourceFile", "TournamentDate", "TournamentMinutes"]],
                on=["SourceFile", "TournamentDate"],
                how="left",
            ).copy()

            w.loc[:, "MinutesSurvived"] = w["TournamentMinutes"]
            win_surv = w[["TournamentDate", "Player", "MinutesSurvived", "TournamentMinutes"]].copy()
        else:
            win_surv = pd.DataFrame(columns=["TournamentDate", "Player", "MinutesSurvived", "TournamentMinutes"])

        surv_rows = pd.concat([elim_surv, win_surv], ignore_index=True)

        if not surv_rows.empty:
            surv_rows = surv_rows.copy()
            surv_rows.loc[:, "SurvivalPercent"] = surv_rows["MinutesSurvived"] / surv_rows["TournamentMinutes"]

            # week_lookup must exist earlier in your function.
            surv_rows = surv_rows.merge(week_lookup, on="TournamentDate", how="left").copy()

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

            survival.loc[:, "AvgMinutesSurvived"] = survival["AvgMinutesSurvived"].round(1)
            survival.loc[:, "AvgSurvivalPercent"] = survival["AvgSurvivalPercent"].round(3)

            # Winners display without SourceFile (keep original winners for joins above)
            winners_display = (
                winners.drop(columns=["SourceFile"]) if ("SourceFile" in winners.columns) else winners
            )

            # =========================
            # Analytics: Points Consistency
            # =========================
            analytics_points = pd.DataFrame()
            if not weekly_points.empty:
                ap = weekly_points.copy()
                ap.loc[:, "Points"] = pd.to_numeric(ap["Points"], errors="coerce")

        analytics_points = (
            ap.groupby("Player", as_index=False)
            .agg(
                **{
                    "Weeks Played": ("Points", "count"),
                    "Avg Points": ("Points", "mean"),
                    "Points Std Dev": ("Points", lambda s: float(s.std()) if s.count() > 1 else 0.0),
                    "Best Week": ("Points", "max"),
                    "Worst Week": ("Points", "min"),
                }
            )
            .sort_values(by="Avg Points", ascending=False)
            .reset_index(drop=True)
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
        "AnalyticsPoints": analytics_points,
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
    Pandas 3.0 / Copy-on-Write safe: no chained assignment.
    """
    if season_totals is None or season_totals.empty:
        return pd.DataFrame()

    st = season_totals.copy()

    drop2_col = "Total Points (bottom 2 dropped)"
    if drop2_col not in season_totals.columns:
        raise ValueError(f"Expected '{drop2_col}' in SeasonTotals. Columns: {list(season_totals.columns)}")

    st = (
        st.loc[:, ["Player", drop2_col]]
        .rename(columns={drop2_col: "TotalPoints_drop2"})
        .copy()
    )
    # ---- SeasonPointsChips ----
    season_points_chips = st.loc[:, ["Player", "TotalPoints_drop2"]].copy()
    season_points_chips.loc[:, "SeasonPointsChips"] = (
        season_points_chips["TotalPoints_drop2"] * season_points_chip_multiplier
    )
    season_points_chips = season_points_chips.loc[:, ["Player", "SeasonPointsChips"]].copy()

    # ---- Elim_Counts (intended) ----
    # Total eliminations credited to EliminatorPlayer
    elim_counts = pd.DataFrame(columns=["Player", "TotalElimsCount", "ChipsFromTotalElims"])

    e_clean = pd.DataFrame()  # default so it's always defined

    if elims is not None and not elims.empty and "EliminatorPlayer" in elims.columns:
        e_clean = elims.copy()

        # Copy-on-Write safe column cleaning (NO .assign)
        e_clean.loc[:, "EliminatorPlayer"] = e_clean["EliminatorPlayer"].astype(str).str.strip()
        e_clean.loc[:, "EliminatedPlayer"] = e_clean["EliminatedPlayer"].astype(str).str.strip()

        # Filter out blanks/"nan"
        elim_ok = (
            e_clean["EliminatorPlayer"].ne("")
            & e_clean["EliminatorPlayer"].str.lower().ne("nan")
            & e_clean["EliminatedPlayer"].ne("")
            & e_clean["EliminatedPlayer"].str.lower().ne("nan")
        )
        e_clean = e_clean.loc[elim_ok].copy()

        if not e_clean.empty:
            elim_counts = (
                e_clean.groupby("EliminatorPlayer", as_index=False)
                    .size()
                    .rename(columns={"EliminatorPlayer": "Player", "size": "TotalElimsCount"})
            )
            elim_counts.loc[:, "ChipsFromTotalElims"] = (
                elim_counts["TotalElimsCount"] * chip_per_total_elim
            )

    # ---- Repeat_Elims ----
    repeat_elims = pd.DataFrame(columns=["Player", "RepeatElimTotalCount", "RepeatElimChips"])
    if elims is not None and not elims.empty:
        r = elims.loc[:, ["EliminatedPlayer", "EliminatorPlayer"]].copy()

        r.loc[:, "EliminatorPlayer"] = r["EliminatorPlayer"].astype(str).str.strip()
        r.loc[:, "EliminatedPlayer"] = r["EliminatedPlayer"].astype(str).str.strip()

        r = r[(r["EliminatorPlayer"] != "") & (r["EliminatorPlayer"].str.lower() != "nan")]
        r = r[(r["EliminatedPlayer"] != "") & (r["EliminatedPlayer"].str.lower() != "nan")]

        grouped = (
            r.groupby(["EliminatorPlayer", "EliminatedPlayer"], as_index=False)
             .size()
             .rename(columns={"size": "ElimCount"})
        )
        grouped.loc[:, "RepeatElimCount"] = (grouped["ElimCount"] - 1).clip(lower=0)

        repeat_elims = (
            grouped.groupby("EliminatorPlayer", as_index=False)
                   .agg(RepeatElimTotalCount=("RepeatElimCount", "sum"))
                   .rename(columns={"EliminatorPlayer": "Player"})
        )
        repeat_elims.loc[:, "RepeatElimChips"] = repeat_elims["RepeatElimTotalCount"] * chip_per_repeat_elim

    # ---- HV_Elims ----
    # Victim rank <= 3 AND eliminator rank > 3
    hv_elims = pd.DataFrame(columns=["Player", "HVElimTotalCount", "ChipsFromHVElims"])
    if elims is not None and not elims.empty:
        # Build rank lookup from drop2 standings (dense rank like PQ distinct list)
        rank_df = st.copy()
        # dense rank: ties share the same rank number
        rank_df.loc[:, "SeasonRank"] = (
            rank_df["TotalPoints_drop2"].rank(method="dense", ascending=False).astype(int)
        )
        rank_lookup = rank_df[["Player", "SeasonRank"]]

        hv = elims[["EliminatedPlayer", "EliminatorPlayer"]].copy()
        hv.loc[:, "EliminatorPlayer"] = hv["EliminatorPlayer"].astype(str).str.strip()
        hv.loc[:, "EliminatedPlayer"] = hv["EliminatedPlayer"].astype(str).str.strip()

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

        hv_elims.loc[:, "ChipsFromHVElims"] = hv_elims["HVElimTotalCount"] * chip_per_hv_elim

    # ---- Merge all together (like PQ) ----
    out = st.merge(season_points_chips, on="Player", how="left")
    out = out.merge(elim_counts, on="Player", how="left")
    out = out.merge(repeat_elims, on="Player", how="left")
    out = out.merge(hv_elims, on="Player", how="left")

    # fill nulls with 0 (like PQ ReplaceValue null -> 0)
    fill_cols = [
            "SeasonPointsChips", "TotalElimsCount", "ChipsFromTotalElims",
            "RepeatElimTotalCount", "RepeatElimChips", "HVElimTotalCount", "ChipsFromHVElims"
        ]
    present = [c for c in fill_cols if c in out.columns]
    if present:
        out = out.copy()
        out.loc[:, present] = out.loc[:, present].fillna(0)

    out.loc[:, "BaseChipAndChairStack"] = base_stack
    
    out.loc[:, "TotalChipAndChairStack"] = (
        out["BaseChipAndChairStack"]
        + out["SeasonPointsChips"]
        + out["ChipsFromTotalElims"]
        + out["RepeatElimChips"]
        + out["ChipsFromHVElims"]
    )

    # Sort like PQ: by TotalPoints_drop2 desc, then TotalElimsCount desc
    out = out.sort_values(["TotalPoints_drop2", "TotalElimsCount", "Player"], ascending=[False, False, True]).reset_index(drop=True)

    # Column order + final names (no weird indent bugs)
    col_order = [
        "SeasonRank",
        "Player",
        "TotalPoints_drop2",
        "SeasonPointsChips",
        "TotalElimsCount",
        "ChipsFromTotalElims",
        "RepeatElimTotalCount",
        "RepeatElimChips",
        "HVElimTotalCount",
        "ChipsFromHVElims",
        "BaseChipAndChairStack",
        "TotalChipAndChairStack",
    ]
    out = out[[c for c in col_order if c in out.columns]]

    out = out.rename(columns={
    "SeasonRank": "Season Rank",
    "TotalPoints_drop2": "Total Points (bottom 2 dropped)",
    "SeasonPointsChips": "Season Points Chips",
    "TotalElimsCount": "Total Eliminations",
    "ChipsFromTotalElims": "Chips From Total Elims",
    "RepeatElimTotalCount": "Repeat Elim Count",
    "RepeatElimChips": "Repeat Elim Chips",
    "HVElimTotalCount": "High Value Elim Count",
    "ChipsFromHVElims": "Chips From HV Elims",
    "BaseChipAndChairStack": "Base Stack",
    "TotalChipAndChairStack": "Total Stack",
})

    return out

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
    df.loc[:, "Finish Place"] = (
        df.groupby("TournamentDate")["Points"]
          .rank(method="first", ascending=False)
          .astype(int)
    )
    df = df[["TournamentDate", "Finish Place", "Player", "Points"]]

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
        wk = wk[["Finish Place","Player", "Points"]].copy()

        played = set(wk["Player"].dropna().astype(str))
        missing = [p for p in all_players if p not in played]

        if missing:
            wk = pd.concat(
                [wk, pd.DataFrame({"Player": missing, "Points": 0})],
                ignore_index=True,
            )
        wk = wk.sort_values(
            ["Finish Place", "Points", "Player"],
            ascending=[True, False, True],
        ).reset_index(drop=True)

        # Re-number finish places after sorting (1..N)
        wk["Finish Place"] = range(1, len(wk) + 1)

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
        wk = wk[["Finish Place", "Player", "Points"]].sort_values(
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
    OUT_DIR.mkdir(exist_ok=True)
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    # Write CSVs (keep this — it's useful for debugging + future plots)
    for name, df in tables.items():
        df.to_csv(TABLES_DIR / f"{name}.csv", index=False)

    # Build a simple static site (multi-page)
    SITE_DIR = OUT_DIR / "site"
    SITE_DIR.mkdir(parents=True, exist_ok=True)

    print("TABLE KEYS IN write_outputs:", sorted(tables.keys()))

    season = tables.get("SeasonTotals")
    weekly = tables.get("WeeklyPoints")
    survival = tables.get("Survival")
    winners = tables.get("Winners")
    chip_and_chair = tables.get("ChipAndChair")

    if chip_and_chair is not None:
            cols_to_format = [
                "Season Points Chips",
                "Total Eliminations",
                "Chips From Total Elims",
                "Repeat Elim Count",
                "Repeat Elim Chips",
                "High Value Elim Count",
                "Chips From HV Elims",
                "Base Stack",
                "Total Stack",
            ]

    chip_and_chair = format_int_cols_for_html(chip_and_chair.copy(), cols_to_format)
    chip_and_chair = chip_and_chair.rename(columns={"SeasonRank": "Season Rank"})

    if season is None:
        raise SystemExit("SeasonTotals missing from tables. Fix build_tables() return dict.")
    if weekly is None:
        raise SystemExit("WeeklyPoints missing from tables. Fix build_tables() return dict.")

    # ---------- shared helpers ----------
    def _df_html(df: pd.DataFrame | None) -> str:
        if df is None or df.empty:
            return "<p class='note'>No data yet.</p>"
        return df.to_html(index=False, escape=False)

    def _css() -> str:
        return """
  <style>
    body { font-family: -apple-system, system-ui, Arial; margin: 16px; }
    h1,h2 { margin: 10px 0; }
    .note { color:#666; font-size: 13px; margin: 8px 0 14px; }
    .nav { display:flex; gap:10px; flex-wrap:wrap; margin: 10px 0 18px; }
    .nav a { text-decoration:none; padding:8px 10px; border:1px solid #ddd; border-radius:10px; }
    .nav a:hover { background:#f7f7f7; }
    table { border-collapse: collapse; width: 100%; margin: 10px 0 24px; }
    th, td { border-bottom: 1px solid #ddd; padding: 8px; text-align: left; }
    th { position: sticky; top: 0; background: #f7f7f7; }
    details { margin: 12px 0; }
    summary { cursor: pointer; font-weight: bold; }
    code { background:#f5f5f5; padding:2px 6px; border-radius:6px; }
  </style>
"""

    def _nav() -> str:
        return """
  <div class="nav">
    <a href="index.html">Home</a>
    <a href="season-totals.html">Season Totals</a>
    <a href="weekly-points.html">Weekly Points</a>
    <a href="survival.html">Survival</a>
    <a href="winners.html">Winners</a>
    <a href="chip-and-chair.html">Chip &amp; Chair</a>
    <a href="analytics.html">Analytics</a>
  </div>
"""

    def _page(title: str, h2: str, body_html: str) -> str:
        return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{title}</title>
{_css()}
</head>
<body>
  <h1>PokerLeague Stats</h1>
  <p style="margin: 6px 0 6px; color: #666; font-size: 13px;">
  Updated: <strong>{BUILD_TS_EST}</strong>
</p>

<p style="margin: 0px 0 14px; color: #666; font-size: 13px;">
  Latest file: <strong>{last_source_file}</strong>
</p>

{_nav()}

<h2>{h2}</h2>
{body_html}
</body>
</html>
"""

    # ---------- write pages ----------
    # Home page: simple landing + links
    index_html = _page(
        title="PokerLeague Stats",
        h2="Dashboard",
        body_html=f"""
  <p class="note">Pick a page:</p>
  <ul>
    <li><a href="season-totals.html">Season Totals</a></li>
    <li><a href="weekly-points.html">Weekly Points</a></li>
    <li><a href="survival.html">Survival</a></li>
    <li><a href="winners.html">Winners</a></li>
    <li><a href="chip-and-chair.html">Chip &amp; Chair</a></li>
  </ul>
"""
    )
    (SITE_DIR / "index.html").write_text(index_html, encoding="utf-8")

    # Season Totals
    (SITE_DIR / "season-totals.html").write_text(
        _page("Season Totals", "Season Totals", _df_html(season)),
        encoding="utf-8",
    )

    # Weekly Points (keep your nice expandable week sections)
    (SITE_DIR / "weekly-points.html").write_text(
        _page("Weekly Points", "Weekly Points", build_weekly_section(weekly.copy())),
        encoding="utf-8",
    )

    # Survival
    (SITE_DIR / "survival.html").write_text(
        _page("Survival", "Survival", _df_html(survival)),
        encoding="utf-8",
    )

    # Winners
    (SITE_DIR / "winners.html").write_text(
        _page("Winners", "Winners", _df_html(winners)),
        encoding="utf-8",
    )

    # Analytics - Points
    analytics_points = tables.get("AnalyticsPoints", pd.DataFrame())
    (SITE_DIR / "analytics.html").write_text(
        _page("Analytics", "Analytics", _df_html(analytics_points)),
        encoding="utf-8",
    )

    # Chip & Chair
    (SITE_DIR / "chip-and-chair.html").write_text(
        _page("Chip & Chair", "Chip & Chair", _df_html(chip_and_chair)),
        encoding="utf-8",
    )

    # Optional: keep the old single-file dashboard.html as a redirect to the site home
    redirect = """<!doctype html><html><head>
<meta http-equiv="refresh" content="0; url=site/index.html">
</head><body>Redirecting…</body></html>"""
    (OUT_DIR / "dashboard.html").write_text(redirect, encoding="utf-8")

    print("✅ Built site:", SITE_DIR)

def main():
    raw, last_source_file = load_raw_events(DATA_DIR)
    tables = build_tables(raw)
    print("TABLE KEYS:", sorted(tables.keys()))
    write_outputs(tables, last_source_file)
    print("✅ Built outputs:")
    print(f"   - {TABLES_DIR.resolve()}")
    print(f"   - {(OUT_DIR / 'dashboard.html').resolve()}")
    print("✅ Built site: output/site")
    import shutil
    from pathlib import Path

    def sync_dir(src: Path, dst: Path) -> None:
        dst.mkdir(parents=True, exist_ok=True)
        for p in dst.iterdir():
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
        for p in src.iterdir():
            target = dst / p.name
            if p.is_dir():
                shutil.copytree(p, target)
            else:
                shutil.copy2(p, target)

    site_dir = Path("output/site")

    sync_dir(site_dir, Path("docs"))
    sync_dir(site_dir, Path("docs_local"))

    print("✅ Synced output/site -> docs and docs_local")

if __name__ == "__main__":
    main()