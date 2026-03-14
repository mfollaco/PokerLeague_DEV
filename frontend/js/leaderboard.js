import { getSeasonIdFromUrl } from "./core/season_config.js";
import { loadSeasonData } from "./core/data_loader.js";

// frontend/js/leaderboard.js

function formatMoney(value) {
  const amount = Number(value || 0);
  return amount.toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0
  });
}

let playersRaw = [];
let playersView = [];
let currentSort = { key: "Rank", dir: "asc" };

// -------------------------
// Helpers
// -------------------------

function sum(values) {
  return values.reduce((total, value) => total + (Number(value) || 0), 0);
}

function getPlayerName(player) {
  return player.Player ?? player.player_name ?? player.name ?? "Unknown";
}

function getPlayerKey(player) {
  return player.player_id ?? player.PlayerID ?? player.id ?? getPlayerName(player);
}

function getWeeklyPointsArray(player) {
  return Array.isArray(player.WeeklyPoints)
    ? player.WeeklyPoints
    : Array.isArray(player.weekly_points)
      ? player.weekly_points
      : [];
}

function computeDrop2Total(weeklyPoints) {
  const cleanPoints = weeklyPoints.map(value => Number(value) || 0);
  const total = sum(cleanPoints);

  const sortedAscending = [...cleanPoints].sort((a, b) => a - b);
  const dropCount = Math.min(2, sortedAscending.length);
  const dropped = sum(sortedAscending.slice(0, dropCount));

  return {
    total,
    drop2: total - dropped
  };
}

function weeklyAsOf(weeklyPoints, weekIndex) {
  const source = Array.isArray(weeklyPoints) ? weeklyPoints : [];
  const slice = source.slice(0, weekIndex).map(value => Number(value) || 0);

  while (slice.length < weekIndex) {
    slice.push(0);
  }

  return slice;
}

function getLatestWeek(players) {
  let maxLength = 0;

  for (const player of players) {
    const weeklyPoints = getWeeklyPointsArray(player);
    maxLength = Math.max(maxLength, weeklyPoints.length);
  }

  return maxLength;
}

function trendGlyph(delta) {
  if (delta > 0) return "▲";
  if (delta < 0) return "▼";
  return "—";
}

// Ranking rules:
// 1. Drop-2 descending
// 2. Total descending
// 3. Name ascending
function buildRankMap(players, weekIndex) {
  const scoredPlayers = players.map(player => {
    const name = getPlayerName(player);
    const weeklyPoints = getWeeklyPointsArray(player);
    const weekly = weeklyAsOf(weeklyPoints, weekIndex);
    const { drop2, total } = computeDrop2Total(weekly);

    return {
      ...player,
      __name: name,
      __drop2_asof: drop2,
      __total_asof: total
    };
  });

  scoredPlayers.sort((a, b) => {
    if (b.__drop2_asof !== a.__drop2_asof) {
      return b.__drop2_asof - a.__drop2_asof;
    }

    if (b.__total_asof !== a.__total_asof) {
      return b.__total_asof - a.__total_asof;
    }

    return a.__name.localeCompare(b.__name);
  });

  const rankMap = new Map();

  scoredPlayers.forEach((player, index) => {
    rankMap.set(getPlayerKey(player), index + 1);
  });

  return rankMap;
}

function sortSeasonAwardsRows(rows = []) {
  return [...rows].sort((a, b) => (Number(b.Amount) || 0) - (Number(a.Amount) || 0));
}

// -------------------------
// Trends / ranks
// -------------------------

function computeTrendsAndRanks(players) {
  const latestWeek = getLatestWeek(players);
  const prevWeek = Math.max(0, latestWeek - 1);

  const currentRankMap = buildRankMap(players, latestWeek);
  const prevRankMap = buildRankMap(players, prevWeek);

  const enriched = players.map(player => {
    const key = getPlayerKey(player);
    const currentRank = currentRankMap.get(key) ?? null;
    const prevRank = prevRankMap.get(key) ?? null;
    const trend = (prevRank && currentRank) ? (prevRank - currentRank) : 0;

    return {
      ...player,
      Rank: currentRank,
      PrevRank: prevRank,
      Trend: trend,
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

function formatAvg(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "—";
  return Number.isInteger(num) ? num.toString() : num.toFixed(1);
}

function renderSeasonAwards(rows) {
  const card = document.getElementById("seasonAwardsCard");
  const host = document.getElementById("seasonAwardsBody");

  if (!card || !host) return;

  host.innerHTML = "";

  const sortedRows = sortSeasonAwardsRows(Array.isArray(rows) ? rows : []);
  const topThree = sortedRows.slice(0, 3);

  if (topThree.length === 0) {
    card.style.display = "none";
    return;
  }

  card.style.display = "";

  const titles = ["1st Place", "2nd Place", "3rd Place"];
  const medals = ["🥇", "🥈", "🥉"];

  topThree.forEach((row, index) => {
    const title = titles[index] ?? "Season Award";
    const medal = medals[index] ?? "🏅";
    const winner = getPlayerName(row);
    const amount = row.Amount != null ? `$${Number(row.Amount).toFixed(0)}` : "";

    const col = document.createElement("div");
    col.className = "col-12 col-md-6 col-lg-4";

    col.innerHTML = `
      <div class="p-3 rounded border border-gold bg-dark h-100">
        <div class="text-warning fw-semibold mb-1">${medal} ${title}</div>
        <div class="fs-5 fw-bold">${winner}</div>
        ${amount ? `<div class="text-muted small mt-1">${amount}</div>` : ""}
      </div>
    `;

    host.appendChild(col);
  });
}

function renderTable(rows) {
  const tbody = document.querySelector("#leaderboardTable tbody");
  if (!tbody) return;

  tbody.innerHTML = "";

  rows.forEach(player => {
    const name = getPlayerName(player);
    const drop2 = player.SeasonPointsDrop2 ?? "";
    const total = player.SeasonPointsTotal ?? "";
    const weeks = player.WeeksInSeason ?? "";
    const wins = player.Wins ?? "";
    const avg = formatAvg(player.AvgFinish);
    const money = formatMoney(player.MoneyWonTotal ?? 0);

    let trendHtml = "—";
    let trendClass = "text-muted";

    if (player.Trend > 0) {
      trendHtml = `▲${Math.abs(player.Trend)}`;
      trendClass = "text-success";
    } else if (player.Trend < 0) {
      trendHtml = `▼${Math.abs(player.Trend)}`;
      trendClass = "text-danger";
    }

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${player.Rank ?? ""}</td>
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

function sortRows(rows, key, dir) {
  const multiplier = dir === "asc" ? 1 : -1;

  return [...rows].sort((a, b) => {
    const aValue = a[key];
    const bValue = b[key];

    const aNum = Number(aValue);
    const bNum = Number(bValue);

    if (!Number.isNaN(aNum) && !Number.isNaN(bNum)) {
      if (aNum !== bNum) {
        return (aNum - bNum) * multiplier;
      }
    } else {
      const aStr = String(aValue ?? "");
      const bStr = String(bValue ?? "");
      const compare = aStr.localeCompare(bStr);

      if (compare !== 0) {
        return compare * multiplier;
      }
    }

    return getPlayerName(a).localeCompare(getPlayerName(b));
  });
}

function wireSortHeaders() {
  document.querySelectorAll("th[data-sort]").forEach(th => {
    th.addEventListener("click", () => {
      const key = th.dataset.sort;

      if (currentSort.key === key) {
        currentSort.dir = currentSort.dir === "asc" ? "desc" : "asc";
      } else {
        currentSort.key = key;
        currentSort.dir = "asc";
      }

      renderTable(sortRows(playersView, currentSort.key, currentSort.dir));
    });
  });
}

// -------------------------
// Boot
// -------------------------

async function initLeaderboard() {
  try {
    const seasonId = getSeasonIdFromUrl() || "spring_2026";
    const { data, season, source } = await loadSeasonData(seasonId);

    renderSeasonAwards(data.SeasonAwards ?? []);

    let seasonSummary = null;

    for (const [, value] of Object.entries(data)) {
      if (!Array.isArray(value) || !value.length || typeof value[0] !== "object") {
        continue;
      }

      const sample = value[0];
      const hasPlayer = "Player" in sample;
      const hasSeasonField =
        "SeasonPointsDrop2" in sample ||
        "SeasonPointsTotal" in sample ||
        "WeeksInSeason" in sample ||
        "Wins" in sample ||
        "AvgFinish" in sample;

      if (hasPlayer && hasSeasonField) {
        seasonSummary = value;
        break;
      }
    }

    const seasonByPlayer = new Map(
      (seasonSummary ?? []).map(player => [player.Player, player])
    );

    const weeklyFlat = data.WeeklyPoints ?? [];
    const weeksByPlayer = new Map();
    const playerMap = new Map();

    weeklyFlat.forEach(row => {
      const name = row.Player;
      const week = row.Week;
      const points = Number(row.Points) || 0;

      if (!weeksByPlayer.has(name)) {
        weeksByPlayer.set(name, new Set());
      }
      weeksByPlayer.get(name).add(week);

      if (!playerMap.has(name)) {
        const summary = seasonByPlayer.get(name) ?? {};

        playerMap.set(name, {
          Player: name,
          WeeklyPoints: [],
          SeasonPointsDrop2: summary.SeasonPointsDrop2 ?? null,
          SeasonPointsTotal: summary.SeasonPointsTotal ?? null,
          WeeksInSeason: summary.WeeksInSeason ?? null,
          Wins: summary.Wins ?? null,
          AvgFinish: summary.AvgFinish ?? null,
          MoneyWonTotal: summary.MoneyWonTotal ?? 0
        });
      }

      const player = playerMap.get(name);

      while (player.WeeklyPoints.length < week) {
        player.WeeklyPoints.push(0);
      }

      player.WeeklyPoints[week - 1] = points;
    });

    playersRaw = Array.from(playerMap.values());

    playersRaw.forEach(player => {
      player.WeeksInSeason = weeksByPlayer.get(player.Player)?.size ?? 0;
    });

    const { enriched, latestWeek, prevWeek } = computeTrendsAndRanks(playersRaw);
    playersView = enriched;

    renderTable(sortRows(playersView, "Rank", "asc"));
    wireSortHeaders();

    const stamp = document.getElementById("asOfWeekStamp");
    if (stamp) {
      stamp.textContent = `As of Week ${latestWeek} (prev: Week ${prevWeek})`;
    }
  } catch (err) {
    console.error("Failed to initialize leaderboard:", err);

    const tbody = document.querySelector("#leaderboardTable tbody");
    if (tbody) {
      tbody.innerHTML = `
        <tr>
          <td colspan="9" class="text-center text-danger py-4">
            Failed to load leaderboard.<br>
            <small>${err?.message || String(err)}</small>
          </td>
        </tr>
      `;
    }
  }
}

document.addEventListener("DOMContentLoaded", initLeaderboard);
