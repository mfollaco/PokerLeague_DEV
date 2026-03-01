import { setHtml, escapeHtml } from "../core/dom_utils.js";
import { formatNumber } from "../core/formatters.js";
import { initAnalyticsPage } from "../core/page_bootstrap.js";
import { createBarChart, setActiveBar } from "../core/chart_utils.js";
import { getPlayerColor } from "../core/player_colors.js";

// ---------- UI helpers ----------
function renderTable(rows) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return `<div class="text-muted">No Survival rows found.</div>`;
  }

  return `
    <table class="table table-dark table-striped align-middle mb-0">
      <thead>
        <tr>
          <th style="width: 34px;">#</th>
          <th>Player</th>
          <th class="text-end">Weeks</th>
          <th class="text-end col-minutes">Avg Minutes</th>
          <th class="text-end">Avg Survival %</th>
        </tr>
      </thead>
      <tbody>
        ${rows.map((r, idx) => {
          const pct = r.AvgSurvivalPercent == null ? null : (Number(r.AvgSurvivalPercent) * 100);
          return `
            <tr class="player-row" data-player="${escapeHtml(r.Player ?? "")}" style="cursor:pointer;">
              <td class="text-muted">${idx + 1}</td>
              <td>${escapeHtml(r.Player ?? "—")}</td>
              <td class="text-end">${r.WeeksPlayed ?? "—"}</td>
              <td class="text-end col-minutes">${formatNumber(r.AvgMinutesSurvived, 1)}</td>
              <td class="text-end">${pct == null ? "—" : `${formatNumber(pct, 1)}%`}</td>
            </tr>
          `;
        }).join("")}
      </tbody>
    </table>
  `;
}

function showPlayerDetail(row, rank) {
  const detailEl = document.getElementById("player-detail");
  const titleEl = document.getElementById("player-detail-title");
  const metricsEl = document.getElementById("player-detail-metrics");
  if (!detailEl || !titleEl || !metricsEl) return;

  const pct = row.AvgSurvivalPercent == null ? null : Number(row.AvgSurvivalPercent) * 100;

  titleEl.textContent = row.Player ?? "—";
  metricsEl.innerHTML = `
    <div><strong>Rank:</strong> #${rank}</div>
    <div><strong>Weeks Played:</strong> ${row.WeeksPlayed ?? "—"}</div>
    <div><strong>Avg Minutes Survived:</strong> ${formatNumber(row.AvgMinutesSurvived, 1)}</div>
    <div><strong>Avg Survival %:</strong> ${pct == null ? "—" : `${formatNumber(pct, 1)}%`}</div>
  `;

  detailEl.classList.remove("d-none");
}

function hidePlayerDetail() {
  const detailEl = document.getElementById("player-detail");
  if (detailEl) detailEl.classList.add("d-none");
}

function wireDetailClose() {
  const btn = document.getElementById("player-detail-close");
  if (!btn) return;
  btn.addEventListener("click", hidePlayerDetail);
}

// ---------- Main render ----------
initAnalyticsPage({
  render: async (data) => {
    wireDetailClose();

    // 1) Pull survival rows
    const rows = Array.isArray(data?.Survival) ? data.Survival : [];

    // 2) Single source of truth ordering (used by table + chart + rank)
    const sorted = [...rows].sort((a, b) =>
      (b.AvgSurvivalPercent ?? 0) - (a.AvgSurvivalPercent ?? 0)
    );

    // 3) Table
    const tableHost = document.getElementById("survival-table");
    if (!tableHost) throw new Error("Missing #survival-table");
    setHtml(tableHost, renderTable(sorted));

    // 4) Wire row clicks -> detail
    document.querySelectorAll("#survival-table .player-row").forEach((tr) => {
      tr.addEventListener("click", () => {
        const playerName = tr.getAttribute("data-player") || "";
        const idx = sorted.findIndex(r => (r.Player ?? "") === playerName);
        if (idx >= 0) showPlayerDetail(sorted[idx], idx + 1);
      });
    });

    // 5) Chart inputs from the same sorted rows
    const labels = sorted.map(r => r.Player ?? "—");
    const values = sorted.map(r => {
      const pct = r.AvgSurvivalPercent == null ? null : (Number(r.AvgSurvivalPercent) * 100);
      return pct == null ? 0 : Number(pct.toFixed(1));
    });
    const colors = sorted.map(r => getPlayerColor(r.Player ?? ""));

    // 6) Chart
    const canvas = document.getElementById("survival-chart");
    if (!canvas) throw new Error("Missing <canvas id='survival-chart'> in survival.html");

    const chart = createBarChart(canvas, {
      labels,
      values,
      colors,
      yLabel: "Avg Survival %",
      valueSuffix: "%"
    });

    // 7) Click bar -> detail + highlight
    canvas.onclick = (evt) => {
      const points = chart.getElementsAtEventForMode(evt, "nearest", { intersect: true }, true);
      if (!points.length) return;

      const i = points[0].index;
      showPlayerDetail(sorted[i], i + 1);
      setActiveBar(chart, i);
    };
  }
});