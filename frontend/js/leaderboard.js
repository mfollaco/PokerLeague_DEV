function formatMoney(x) {
  const n = Number(x || 0);
  return n.toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0
  });
}

// frontend/js/leaderboard.js

let playersRaw = [];
let playersView = []; // what we render (includes trend + computed ranks)
let currentSort = { key: "Rank", dir: "asc" }; // default display sort

// -------------------------
// Helpers
// -------------------------

function sum(arr) {
  return arr.reduce((a, b) => a + (Number(b) || 0), 0);
}

// Drop lowest 2 weekly scores (including 0s for absences)
// If fewer than 2 weeks, drop as many as exist (0..2).
function computeDrop2Total(weekly) {
  const clean = weekly.map(v => Number(v) || 0);
  const total = sum(clean);

  // copy + sort asc to find lowest weeks
  const sorted = [...clean].sort((a, b) => a - b);
  const dropCount = Math.min(2, sorted.length);
  const dropped = sum(sorted.slice(0, dropCount));

  return { drop2: total - dropped, total };
}

// Build weekly array "as of" a given weekIndex (1-based week number).
// weeklyPoints might be shorter than weekIndex → pad with 0.
function weeklyAsOf(weeklyPoints, weekIndex) {
  const wp = Array.isArray(weeklyPoints) ? weeklyPoints : [];
  const slice = wp.slice(0, weekIndex).map(v => Number(v) || 0);
  while (slice.length < weekIndex) slice.push(0);
  return slice;
}

// Ranking rules per your definition:
// 1) Drop2 descending
// 2) Total descending (tiebreaker)
// 3) Name ascending (stable deterministic tie-break so ranks are unique)
function buildRankMap(players, weekIndex) {
  const scored = players.map(p => {
    // CHANGE THESE TWO LINES IF YOUR JSON USES DIFFERENT FIELD NAMES:
    const name = p.Player ?? p.player_name ?? p.name ?? "Unknown";
    const weeklyPoints = p.WeeklyPoints ?? p.weekly_points ?? [];

    const weekly = weeklyAsOf(weeklyPoints, weekIndex);
    const { drop2, total } = computeDrop2Total(weekly);

    return {
      ...p,
      __name: name,
      __drop2_asof: drop2,
      __total_asof: total
    };
  });

  scored.sort((a, b) => {
    if (b.__drop2_asof !== a.__drop2_asof) return b.__drop2_asof - a.__drop2_asof;
    if (b.__total_asof !== a.__total_asof) return b.__total_asof - a.__total_asof;
    return a.__name.localeCompare(b.__name);
  });

  const map = new Map();
  scored.forEach((p, idx) => {
    const key = p.player_id ?? p.PlayerID ?? p.id ?? p.__name; // prefer an id, fallback to name
    map.set(key, idx + 1);
  });

  return map;
}

function getLatestWeek(players) {
  // latest week = max WeeklyPoints length across players
  let maxLen = 0;
  for (const p of players) {
    const wp = p.WeeklyPoints ?? p.weekly_points ?? [];
    if (Array.isArray(wp)) maxLen = Math.max(maxLen, wp.length);
  }
  return maxLen; // can be 0 if empty
}

function trendGlyph(delta) {
  if (delta > 0) return "▲";
  if (delta < 0) return "▼";
  return "—";
}

// -------------------------
// Core: compute current/prev ranks + trend ONCE
// -------------------------

function computeTrendsAndRanks(players) {
  const latestWeek = getLatestWeek(players);
  const prevWeek = Math.max(0, latestWeek - 1);

  const currentRankMap = buildRankMap(players, latestWeek);
  const prevRankMap = buildRankMap(players, prevWeek);

  const enriched = players.map(p => {
    const key = p.player_id ?? p.PlayerID ?? p.id ?? (p.Player ?? p.player_name ?? p.name);

    const currentRank = currentRankMap.get(key) ?? null;
    const prevRank = prevRankMap.get(key) ?? null;

    // If prevWeek is 0, prevRank will still exist (all totals=0) — that’s fine.
    const trend = (prevRank && currentRank) ? (prevRank - currentRank) : 0;

    return {
      ...p,
      Rank: currentRank,
      PrevRank: prevRank,
      Trend: trend,              // numeric (positive = up)
      TrendSymbol: trendGlyph(trend),
      TrendAbs: Math.abs(trend),
      __key: key
    };
  });

  return { enriched, latestWeek, prevWeek };
}

// -------------------------
// Rendering
// -------------------------

function renderTable(rows) {
  const tbody = document.querySelector("#leaderboardTable tbody");
  tbody.innerHTML = "";

  console.log("Leaderboard money check:",
  rows.slice(0,5).map(r => [r.Player, r.MoneyWonTotal])
  );

  rows.forEach((p) => {
    // CHANGE THESE IF YOUR FIELD NAMES DIFFER:
    const name = p.Player ?? p.player_name ?? p.name ?? "Unknown";
    const drop2 = p.SeasonPointsDrop2 ?? "";
    const total = p.SeasonPointsTotal ?? "";
    const weeks = p.WeeksInSeason ?? "";
    const wins = p.Wins ?? "";
    const avg = p.AvgFinish ?? "";
    const money = formatMoney(p.MoneyWonTotal ?? 0);

    let trendHtml = "—";
    let trendClass = "text-muted";

    if (p.Trend > 0) {
      trendHtml = `▲${Math.abs(p.Trend)}`;
      trendClass = "text-success";
    } else if (p.Trend < 0) {
      trendHtml = `▼${Math.abs(p.Trend)}`;
      trendClass = "text-danger";
    }

    const tr = document.createElement("tr");
    tr.innerHTML = `
        <td>${p.Rank ?? ""}</td>
        <td class="${trendClass} fw-bold">${trendHtml}</td>
        <td>${name}</td>
        <td>${drop2}</td>
        <td>${total}</td>
        <td>${money}</td>
        <td>${weeks}</td>
        <td>${wins}</td>
        <td>${avg}</td>
        `;
    tbody.appendChild(tr);
  });
}

// Only sorts the already-computed rows. DOES NOT touch Trend.
function sortRows(rows, key, dir) {
  const mult = (dir === "asc") ? 1 : -1;

  return [...rows].sort((a, b) => {
    const av = a[key];
    const bv = b[key];

    // numeric vs string
    const aNum = Number(av);
    const bNum = Number(bv);

    if (!Number.isNaN(aNum) && !Number.isNaN(bNum)) {
      if (aNum !== bNum) return (aNum - bNum) * mult;
    } else {
      const aStr = String(av ?? "");
      const bStr = String(bv ?? "");
      const cmp = aStr.localeCompare(bStr);
      if (cmp !== 0) return cmp * mult;
    }

    // stable tiebreak
    const aName = (a.Player ?? a.player_name ?? a.name ?? "");
    const bName = (b.Player ?? b.player_name ?? b.name ?? "");
    return aName.localeCompare(bName);
  });
}

function wireSortHeaders() {
  // Example: <th data-sort="Rank">Rank</th>
  // Make sure your headers have data-sort attributes matching keys in the row objects.
  document.querySelectorAll("th[data-sort]").forEach(th => {
    th.addEventListener("click", () => {
      const key = th.dataset.sort;

      if (currentSort.key === key) {
        currentSort.dir = (currentSort.dir === "asc") ? "desc" : "asc";
      } else {
        currentSort.key = key;
        currentSort.dir = "asc";
      }

      const sorted = sortRows(playersView, currentSort.key, currentSort.dir);
      renderTable(sorted);
    });
  });
}

// -------------------------
// Boot
// -------------------------

async function initLeaderboard() {
  const res = await fetch("data/spring_2026.json");
  const data = await res.json();

// ---- season summary (drop2/total/weeks/wins/avgfinish) ----
// Find the first array in the JSON that contains objects with a "Player" field
// and at least one of the season summary fields.
let seasonSummary = null;

for (const [key, val] of Object.entries(data)) {
  if (Array.isArray(val) && val.length && typeof val[0] === "object") {
    const sample = val[0];
    const hasPlayer = "Player" in sample;
    const hasSeasonField =
      ("SeasonPointsDrop2" in sample) ||
      ("SeasonPointsTotal" in sample) ||
      ("WeeksInSeason" in sample) ||
      ("Wins" in sample) ||
      ("AvgFinish" in sample);

    if (hasPlayer && hasSeasonField) {
      seasonSummary = val;
      break;
    }
  }
}

const seasonByPlayer = new Map(
  (seasonSummary ?? []).map(p => [p.Player, p])
);

  // CHANGE THIS IF YOUR JSON NESTS PLAYERS DIFFERENTLY:
  // e.g. data.players or data.leaderboard
  
// Build playersRaw from flat WeeklyPoints array
const weeklyFlat = data.WeeklyPoints ?? [];

// Build distinct weeks played per player from the flat WeeklyPoints list
const weeksByPlayer = new Map();
weeklyFlat.forEach(row => {
  const name = row.Player;
  const week = row.Week;

  if (!weeksByPlayer.has(name)) weeksByPlayer.set(name, new Set());
  weeksByPlayer.get(name).add(week);
});

const playerMap = new Map();

// Group points by player
weeklyFlat.forEach(row => {
  const name = row.Player;
  const week = row.Week;
  const points = Number(row.Points) || 0;

  if (!playerMap.has(name)) {
    const summary = seasonByPlayer.get(name) ?? {};

    playerMap.set(name, {
    Player: name,
    WeeklyPoints: [],

    // carry season summary fields (these power your table columns)
    SeasonPointsDrop2: summary.SeasonPointsDrop2 ?? null,
    SeasonPointsTotal: summary.SeasonPointsTotal ?? null,
    WeeksInSeason: summary.WeeksInSeason ?? null,
    Wins: summary.Wins ?? null,
    AvgFinish: summary.AvgFinish ?? null,
    MoneyWonTotal: (summary.MoneyWonTotal ?? 0),
    });
  }

  const player = playerMap.get(name);

  // Ensure WeeklyPoints array is long enough
  while (player.WeeklyPoints.length < week) {
    player.WeeklyPoints.push(0);
  }

  player.WeeklyPoints[week - 1] = points;
});

playersRaw = Array.from(playerMap.values());

// Overwrite WeeksInSeason with true Weeks Played (based on actual participation)
playersRaw.forEach(p => {
  p.WeeksInSeason = weeksByPlayer.get(p.Player)?.size ?? 0;
});

  const { enriched, latestWeek, prevWeek } = computeTrendsAndRanks(playersRaw);

  playersView = enriched;

  // default render (Rank asc)
  const sorted = sortRows(playersView, "Rank", "asc");
  renderTable(sorted);

  wireSortHeaders();

  // optional: show "as of week" somewhere
  const stamp = document.getElementById("asOfWeekStamp");
  if (stamp) stamp.textContent = `As of Week ${latestWeek} (prev: Week ${prevWeek})`;
}

document.addEventListener("DOMContentLoaded", initLeaderboard);
