# backend/chip_and_chair.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List

@dataclass(frozen=True)
class ChipAndChairRules:
    base_stack: int = 6500
    season_points_chip_multiplier: int = 150
    chip_per_total_elim: int = 50
    chip_per_repeat_elim: int = 100
    chip_per_hv_elim: int = 250
    hv_victim_rank_max: int = 3   # victim rank <= 3
    hv_eliminator_rank_min: int = 4  # eliminator rank > 3

def dense_ranks_by_drop2(season_totals: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Dense rank by SeasonPointsDrop2 desc (ties share rank).
    Returns { Player: rank_int }.
    """
    rows = []
    for r in season_totals:
        player = r.get("Player")
        drop2 = r.get("SeasonPointsDrop2")
        if player is None:
            continue
        drop2_num = float(drop2) if drop2 is not None else 0.0
        rows.append((player, drop2_num))

    # distinct scores, sorted desc
    distinct_scores = sorted({s for _, s in rows}, reverse=True)
    score_to_rank = {score: idx + 1 for idx, score in enumerate(distinct_scores)}

    return {player: score_to_rank[score] for player, score in rows}

def build_chip_and_chair(
    season_totals: List[Dict[str, Any]],
    eliminations: List[Dict[str, Any]],
    rules: ChipAndChairRules = ChipAndChairRules(),
) -> List[Dict[str, Any]]:
    """
    Backend version of old PowerQuery logic:
    - Season points chips = SeasonPointsDrop2 * multiplier
    - Total elims chips = count(elims by Eliminator) * chip_per_total_elim
    - Repeat elims: for each (Eliminator, Eliminated) pair: max(count-1,0), summed per Eliminator
    - High value elim: Victim rank <= 3 AND Eliminator rank > 3
    """
    ranks = dense_ranks_by_drop2(season_totals)

    # --- base output skeleton from SeasonTotals ---
    by_player: Dict[str, Dict[str, Any]] = {}
    for st in season_totals:
        p = st.get("Player")
        if not p:
            continue
        drop2 = float(st.get("SeasonPointsDrop2") or 0)
        by_player[p] = {
            "Player": p,
            "BaseStack": rules.base_stack,
            "ChipsFromSeasonPoints": int(round(drop2 * rules.season_points_chip_multiplier)),
            "TotalEliminations": 0,
            "ChipsFromTotalElims": 0,
            "RepeatElimCount": 0,
            "ChipsFromRepeatElims": 0,
            "HighValueElimCount": 0,
            "ChipsFromHighValueElims": 0,
            "TotalStack": 0,  # computed at end
        }

    # --- total eliminations ---
    # eliminations records expected: {"EliminatorPlayer": "...", "EliminatedPlayer": "...", ...}
    elim_counts: Dict[str, int] = {}
    pair_counts: Dict[tuple[str, str], int] = {}

    for e in eliminations or []:
        elim = (e.get("EliminatorPlayer") or "").strip()
        vict = (e.get("EliminatedPlayer") or "").strip()
        if not elim or not vict:
            continue

        elim_counts[elim] = elim_counts.get(elim, 0) + 1
        pair_counts[(elim, vict)] = pair_counts.get((elim, vict), 0) + 1

    # apply total elim chips
    for elim_player, cnt in elim_counts.items():
        if elim_player not in by_player:
            # in case eliminator isn't in season_totals list
            by_player[elim_player] = {
                "Player": elim_player,
                "BaseStack": rules.base_stack,
                "ChipsFromSeasonPoints": 0,
                "TotalEliminations": 0,
                "ChipsFromTotalElims": 0,
                "RepeatElimCount": 0,
                "ChipsFromRepeatElims": 0,
                "HighValueElimCount": 0,
                "ChipsFromHighValueElims": 0,
                "TotalStack": 0,
            }
        by_player[elim_player]["TotalEliminations"] = cnt
        by_player[elim_player]["ChipsFromTotalElims"] = cnt * rules.chip_per_total_elim

    # --- repeat elims (tiered per pair; NOT cumulative tiers) ---
    # Per (Eliminator, Victim) pair:
    #   1x => 50
    #   2x => 100
    #   3+ => 250
    #
    # RepeatElimCount stays as "repeat occurrences" (cnt-1) for display.
    # ChipsFromRepeatElims becomes sum of the capped bonus per pair.

    repeat_count_by_elim: Dict[str, int] = {}
    repeat_chips_by_elim: Dict[str, int] = {}

    tier1 = rules.chip_per_total_elim      # 50
    tier2 = rules.chip_per_repeat_elim     # 100
    tier3 = rules.chip_per_hv_elim         # 250

    for (elim_player, vict), cnt in pair_counts.items():
        # count repeats for display
        repeat_occurrences = max(cnt - 1, 0)
        if repeat_occurrences:
            repeat_count_by_elim[elim_player] = repeat_count_by_elim.get(elim_player, 0) + repeat_occurrences

        # tiered capped chips per pair
        if cnt <= 0:
            pair_bonus = 0
        elif cnt == 1:
            pair_bonus = tier1
        elif cnt == 2:
            pair_bonus = tier2
        else:
            pair_bonus = tier3

        repeat_chips_by_elim[elim_player] = repeat_chips_by_elim.get(elim_player, 0) + pair_bonus

    # write into by_player
    for elim_player in set(repeat_count_by_elim.keys()) | set(repeat_chips_by_elim.keys()):
        by_player.setdefault(elim_player, {
            "Player": elim_player,
            "BaseStack": rules.base_stack,
            "ChipsFromSeasonPoints": 0,
            "TotalEliminations": 0,
            "ChipsFromTotalElims": 0,
            "RepeatElimCount": 0,
            "ChipsFromRepeatElims": 0,
            "HighValueElimCount": 0,
            "ChipsFromHighValueElims": 0,
            "TotalStack": 0,
        })
        by_player[elim_player]["RepeatElimCount"] = repeat_count_by_elim.get(elim_player, 0)
        by_player[elim_player]["ChipsFromRepeatElims"] = repeat_chips_by_elim.get(elim_player, 0)

    # --- high value elims ---
    # victim rank <=3 and eliminator rank >3
    hv_by_elim: Dict[str, int] = {}
    for e in eliminations or []:
        elim_player = (e.get("EliminatorPlayer") or "").strip()
        vict = (e.get("EliminatedPlayer") or "").strip()
        if not elim_player or not vict:
            continue

        victim_rank = ranks.get(vict, 999)
        elim_rank = ranks.get(elim_player, 999)

        if victim_rank <= rules.hv_victim_rank_max and elim_rank >= rules.hv_eliminator_rank_min:
            hv_by_elim[elim_player] = hv_by_elim.get(elim_player, 0) + 1

    for elim_player, hv_cnt in hv_by_elim.items():
        by_player.setdefault(elim_player, {
            "Player": elim_player,
            "BaseStack": rules.base_stack,
            "ChipsFromSeasonPoints": 0,
            "TotalEliminations": 0,
            "ChipsFromTotalElims": 0,
            "RepeatElimCount": 0,
            "ChipsFromRepeatElims": 0,
            "HighValueElimCount": 0,
            "ChipsFromHighValueElims": 0,
            "TotalStack": 0,
        })
        by_player[elim_player]["HighValueElimCount"] = hv_cnt
        by_player[elim_player]["ChipsFromHighValueElims"] = hv_cnt * rules.chip_per_hv_elim

    # --- total stack ---
    for p, row in by_player.items():
        row["TotalStack"] = (
            int(row["BaseStack"])
            + int(row["ChipsFromSeasonPoints"])
            + int(row["ChipsFromTotalElims"])
            + int(row["ChipsFromRepeatElims"])
            + int(row["ChipsFromHighValueElims"])
        )

    # return sorted by TotalStack desc
    out = sorted(by_player.values(), key=lambda r: (-r["TotalStack"], r["Player"]))
    return out