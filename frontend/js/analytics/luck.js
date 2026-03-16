import { injectAnalyticsShell } from "./layout.js";
import { loadSeason } from "../core/season.js";

let currentSortKey = "LRI";
let currentSortDir = "desc";
let luckSkillChart = null;

function mean(values) {
  if (!values.length) return 0;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function standardDeviation(values) {
  if (!values.length) return 0;

  const avg = mean(values);
  const variance =
    values.reduce((sum, value) => sum + Math.pow(value - avg, 2), 0) / values.length;

  return Math.sqrt(variance);
}

function getSortIndicator(key) {
  if (currentSortKey !== key) return "";
  return currentSortDir === "asc" ? " ▲" : " ▼";
}

function sortRows(rows) {
  const dir = currentSortDir === "asc" ? 1 : -1;

  return [...rows].sort((a, b) => {
    const valueA = a[currentSortKey];
    const valueB = b[currentSortKey];

    if (currentSortKey === "Signal") {
      const signalRank = {
        "🔥 Red Hot": 4,
        "Heating Up": 3,
        "Stable": 2,
        "Cooling Down": 1,
        "❄ Ice Cold": 0
      };
      return ((signalRank[valueA] ?? -1) - (signalRank[valueB] ?? -1)) * dir;
    }

    if (currentSortKey === "Profile") {
      const profileRank = {
        "Running Hot": 3,
        "Grinding": 2,
        "Running Cold": 1,
        "Below Trend": 0
      };
      return ((profileRank[valueA] ?? -1) - (profileRank[valueB] ?? -1)) * dir;
    }

    if (typeof valueA === "string" && typeof valueB === "string") {
      return valueA.localeCompare(valueB) * dir;
    }

    return ((valueA ?? 0) - (valueB ?? 0)) * dir;
  });
}

function getSignalFromPressure(z) {
  if (z >= 1.5) return "🔥 Red Hot";
  if (z >= 0.75) return "Heating Up";
  if (z > -0.75) return "Stable";
  if (z > -1.5) return "Cooling Down";
  return "❄ Ice Cold";
}

function buildEliminationTotals(pairCounts) {
  const totals = {};

  for (const row of pairCounts || []) {
    const killer = row.Killer;
    const count = Number(row.Count) || 0;
    if (!killer) continue;

    totals[killer] = (totals[killer] || 0) + count;
  }

  return totals;
}

function buildLuckSkillRows(seasonData) {
  const seasonTotals = Array.isArray(seasonData.SeasonTotals) ? seasonData.SeasonTotals : [];
  const survivalRows = Array.isArray(seasonData.Survival) ? seasonData.Survival : [];
  const eliminationPairs = Array.isArray(seasonData.EliminationsPairCounts)
    ? seasonData.EliminationsPairCounts
    : [];

  const eliminationTotals = buildEliminationTotals(eliminationPairs);

  const survivalByPlayer = Object.fromEntries(
    survivalRows.map((row) => [row.Player, row])
  );

  return seasonTotals.map((row) => {
    const player = row.Player;
    const survival = survivalByPlayer[player] || {};

    return {
      Player: player,
      AvgFinish: Number(row.AvgFinish) || 0,
      Wins: Number(row.Wins) || 0,
      WeeksPlayed: Number(row.WeeksPlayed) || 0,
      SeasonPointsDrop2: Number(row.SeasonPointsDrop2) || 0,
      TotalEliminations: eliminationTotals[player] || 0,
      AvgSurvivalPercent: Number(survival.AvgSurvivalPercent) || 0,
      AvgMinutesSurvived: Number(survival.AvgMinutesSurvived) || 0
    };
  });
}

function normalizeScores(rows, field, invert = false) {
  const values = rows.map((row) => row[field]);
  const min = Math.min(...values);
  const max = Math.max(...values);

  return rows.map((row) => {
    if (max === min) {
      row[`${field}Score`] = 50;
      return row;
    }

    let score = (row[field] - min) / (max - min);
    if (invert) score = 1 - score;

    row[`${field}Score`] = score * 100;
    return row;
  });
}

function getProfile(skill, luck, avgSkill, avgLuck) {
  if (skill >= avgSkill && luck >= avgLuck) {
    return { label: "Running Hot", class: "bg-warning text-dark" };
  }

  if (skill < avgSkill && luck >= avgLuck) {
    return { label: "Grinding", class: "bg-success text-white" };
  }

  if (skill >= avgSkill && luck < avgLuck) {
    return { label: "Running Cold", class: "bg-info text-dark" };
  }

  return { label: "Below Trend", class: "bg-secondary text-white" };
}

function mountPageSkeleton() {
  const root = document.getElementById("page-root");
  if (!root) return;

  root.innerHTML = `

    <div class="card bg-dark border-warning-subtle shadow-sm mb-4">
      <div class="card-body">
        <h2 class="h5 text-warning mb-3">Luck vs Skill Map</h2>
        <canvas id="luckSkillChart" height="120"></canvas>
      </div>
    </div>

    <div class="card bg-dark border-warning-subtle shadow-sm mb-4">
      <div class="card-body">
        <h2 class="h5 text-warning mb-3">Luck vs Skill Rankings</h2>
        <div id="luckSkillTable"></div>
      </div>
    </div>

  `;
}

function renderChart(rows, avgSkill, avgLuck) {
  const canvas = document.getElementById("luckSkillChart");
  if (!canvas) return;

  if (luckSkillChart) {
    luckSkillChart.destroy();
  }

  const data = rows.map((row) => ({
    x: row.SkillScore,
    y: row.LuckScore,
    label: row.Player
  }));

  const quadrantPlugin = {
    id: "quadrants",
    beforeDraw(chart) {
      const { ctx, chartArea } = chart;
      if (!chartArea) return;

      const { left, right, top, bottom } = chartArea;
      const midX = chart.scales.x.getPixelForValue(avgSkill);
      const midY = chart.scales.y.getPixelForValue(avgLuck);

      ctx.save();
      ctx.font = "600 15px sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";

      ctx.fillStyle = "rgba(40,167,69,0.35)";
      ctx.fillText("GRINDING", left + (midX - left) / 2, top + (midY - top) / 2);

      ctx.fillStyle = "rgba(255,193,7,0.35)";
      ctx.fillText("RUNNING HOT", midX + (right - midX) / 2, top + (midY - top) / 2);

      ctx.fillStyle = "rgba(180,180,180,0.35)";
      ctx.fillText("BELOW TREND", left + (midX - left) / 2, midY + (bottom - midY) / 2);

      ctx.fillStyle = "rgba(13,202,240,0.35)";
      ctx.fillText("RUNNING COLD", midX + (right - midX) / 2, midY + (bottom - midY) / 2);

      ctx.restore();
    }
  };

  const labelPlugin = {
    id: "pointLabels",
    afterDatasetsDraw(chart) {
      const { ctx } = chart;

      chart.data.datasets.forEach((dataset, datasetIndex) => {
        const meta = chart.getDatasetMeta(datasetIndex);

        meta.data.forEach((point, index) => {
          const player = dataset.data[index].label;
          const isRightEdge = point.x > chart.chartArea.right - 60;

          ctx.save();
          ctx.fillStyle = "#e0e0e0";
          ctx.font = "11px sans-serif";
          ctx.textAlign = isRightEdge ? "right" : "left";
          ctx.fillText(player, isRightEdge ? point.x - 8 : point.x + 8, point.y - 8);
          ctx.restore();
        });
      });
    }
  };

  luckSkillChart = new Chart(canvas, {
    type: "scatter",
    data: {
      datasets: [
        {
          label: "Players",
          data,
          backgroundColor: "#f5c542",
          pointRadius: 6,
          pointHoverRadius: 8
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label(context) {
              const row = rows[context.dataIndex];
              return `${row.Player} | Skill ${row.SkillScore.toFixed(1)} | Luck ${row.LuckScore.toFixed(1)}`;
            }
          }
        }
      },
      scales: {
        x: {
          min: 0,
          max: 120,
          grid: {
            color: "rgba(255,255,255,0.08)"
          },
          ticks: {
            color: "rgba(255,255,255,0.85)"
          },
          title: {
            display: true,
            text: "Skill",
            color: "#f0b90b",
            font: {
              size: 14,
              weight: "bold"
            }
          }
        },
        y: {
          min: 0,
          max: 120,
          grid: {
            color: "rgba(255,255,255,0.08)"
          },
          ticks: {
            color: "rgba(255,255,255,0.85)"
          },
          title: {
            display: true,
            text: "Luck",
            color: "#f0b90b",
            font: {
              size: 14,
              weight: "bold"
            }
          }
        }
      }
    },
    plugins: [quadrantPlugin, labelPlugin]
  });
}

function getSignalClass(signal) {
  if (signal === "🔥 Red Hot") return "text-danger fw-bold";
  if (signal === "Heating Up") return "text-warning fw-semibold";
  if (signal === "Cooling Down") return "fw-semibold";
  if (signal === "❄ Ice Cold") return "text-info fw-semibold";
  return "text-muted";
}

function renderTable(rows, avgSkill, avgLuck) {
  const el = document.getElementById("luckSkillTable");
  if (!el) return;

  const displayRows = rows.map((row) => {
    const profile = getProfile(row.SkillScore, row.LuckScore, avgSkill, avgLuck);
    return {
      ...row,
      Profile: profile.label,
      ProfileClass: profile.class
    };
  });

  const sortedRows = sortRows(displayRows);

  const tableRows = sortedRows
    .map((row) => {
      const badge = row.Signal ?? "Stable";
      const badgeClass = getSignalClass(badge);

      return `
        <tr>
          <td>${row.Player}</td>
          <td class="text-end">${row.SkillScore.toFixed(1)}</td>
          <td class="text-end">${row.LuckScore.toFixed(1)}</td>
          <td class="text-end">${row.LRI.toFixed(1)}</td>
          <td class="text-center" style="width: 190px;">
            <span class="${badgeClass}" style="white-space: nowrap;">
              ${badge}
            </span>
          </td>
          <td>
            <span class="badge ${row.ProfileClass}">
              ${row.Profile}
            </span>
          </td>
        </tr>
      `;
    })
    .join("");

  el.innerHTML = `
    <div class="table-responsive">
      <table class="table table-dark table-striped table-hover mb-0">
        <thead>
          <tr>
            <th data-sort="Player" style="cursor: pointer;">Player${getSortIndicator("Player")}</th>
            <th data-sort="SkillScore" class="text-end" style="cursor: pointer;">Skill${getSortIndicator("SkillScore")}</th>
            <th data-sort="LuckScore" class="text-end" style="cursor: pointer;">Luck${getSortIndicator("LuckScore")}</th>
            <th data-sort="LRI" class="text-end" style="cursor: pointer;">LRI${getSortIndicator("LRI")}</th>
            <th data-sort="Signal" class="text-center" style="width: 190px; cursor: pointer;">Signal${getSortIndicator("Signal")}</th>
            <th data-sort="Profile" style="cursor: pointer;">Profile${getSortIndicator("Profile")}</th>
          </tr>
        </thead>
        <tbody>
          ${tableRows}
        </tbody>
      </table>
    </div>
  `;

  el.querySelectorAll("th[data-sort]").forEach((th) => {
    th.addEventListener("click", () => {
      const key = th.dataset.sort;

      if (currentSortKey === key) {
        currentSortDir = currentSortDir === "asc" ? "desc" : "asc";
      } else {
        currentSortKey = key;
        currentSortDir = key === "Player" ? "asc" : "desc";
      }

      renderTable(rows, avgSkill, avgLuck);
    });
  });
}

async function init() {
  injectAnalyticsShell({
    title: "Luck vs Skill",
    active: "luck",
    showBackToHub: false,
    showSeasonControls: false,
    hubHref: "/analytics/analytics_index.html",
    homeHref: "index.html"
  });

  mountPageSkeleton();

  try {
    const { seasonId, data: seasonData } = await loadSeason();

    let rows = buildLuckSkillRows(seasonData);

    rows = normalizeScores(rows, "AvgFinish", true);
    rows = normalizeScores(rows, "TotalEliminations");
    rows = normalizeScores(rows, "Wins");
    rows = normalizeScores(rows, "AvgSurvivalPercent");

    rows.forEach((row) => {
      row.SkillScore =
        row.AvgFinishScore * 0.55 +
        row.TotalEliminationsScore * 0.35 +
        row.WinsScore * 0.10;

      row.LuckScore = row.AvgSurvivalPercentScore;
      row.LRI = row.LuckScore - row.SkillScore;
    });

    const lriValues = rows.map((row) => row.LRI);
    const meanLRI = mean(lriValues);
    const sdLRI = standardDeviation(lriValues);

    rows.forEach((row) => {
      const pressure = sdLRI === 0 ? 0 : (row.LRI - meanLRI) / sdLRI;
      row.Pressure = pressure;
      row.Signal = getSignalFromPressure(pressure);
    });

    const avgSkill = mean(rows.map((row) => row.SkillScore));
    const avgLuck = mean(rows.map((row) => row.LuckScore));

    renderChart(rows, avgSkill, avgLuck);
    renderTable(rows, avgSkill, avgLuck);
  } catch (error) {
    console.error(error);

    const root = document.getElementById("page-root");
    if (root) {
      root.innerHTML = `
        <div class="alert alert-danger">
          Failed to load Luck vs Skill page: ${error.message}
        </div>
      `;
    }
  }
}

init();