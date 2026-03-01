import { byId, setHtml, show, hide, renderAlert, escapeHtml } from "../core/dom_utils.js";
import { getSeasonIdFromUrl, resolveSeason, SEASONS } from "../core/season_config.js";
import { loadSeasonData, clearSeasonCache } from "../core/data_loader.js";

/* -----------------------------
   Season helpers
----------------------------- */

function buildSeasonOptions(currentId) {
  return Object.keys(SEASONS)
    .map((id) => {
      const s = SEASONS[id];
      const selected = id === currentId ? "selected" : "";
      return `<option value="${escapeHtml(s.id)}" ${selected}>${escapeHtml(s.name)}</option>`;
    })
    .join("");
}

function navigateWithSeason(seasonId) {
  const url = new URL(window.location.href);
  url.searchParams.set("season", seasonId);
  window.location.href = url.toString();
}

function getWeekCount(data) {
  // Prefer a real "weeks" list if you ever add one in your JSON
  const explicit =
    Array.isArray(data?.Weeks) ? data.Weeks.length :
    Array.isArray(data?.WeekList) ? data.WeekList.length :
    null;
  if (explicit != null) return explicit;

  // Try WeeklyPoints: count distinct week keys if present
  const rows = Array.isArray(data?.WeeklyPoints) ? data.WeeklyPoints : [];
  if (rows.length) {
    const weekKey =
      ("Week" in rows[0]) ? "Week" :
      ("WeekNum" in rows[0]) ? "WeekNum" :
      ("WeekNumber" in rows[0]) ? "WeekNumber" :
      ("week" in rows[0]) ? "week" :
      null;

    if (weekKey) {
      const set = new Set(rows.map(r => r?.[weekKey]).filter(v => v != null));
      if (set.size) return set.size;
    }

    // Fallback: if rows have a Date-like field, count distinct values
    const dateKey =
      ("Date" in rows[0]) ? "Date" :
      ("date" in rows[0]) ? "date" :
      null;

    if (dateKey) {
      const set = new Set(rows.map(r => r?.[dateKey]).filter(v => v != null));
      if (set.size) return set.size;
    }
  }

  // Final fallback: try other arrays that might be per-week
  const wk =
    Array.isArray(data?.WeeklyResults) ? data.WeeklyResults.length :
    Array.isArray(data?.WeeksSummary) ? data.WeeksSummary.length :
    null;

  return wk;
}

function getPlayerCount(data) {
  return Array.isArray(data?.SeasonTotals) ? data.SeasonTotals.length : null;
}

/* -----------------------------
   UI rendering
----------------------------- */

function tileLive({ seasonId, href, badge = "Live", title, desc }) {
  const qs = `?season=${encodeURIComponent(seasonId)}`;

  return `
    <div class="col-12 col-md-6 col-xl-4">
      <a class="text-decoration-none d-block h-100" href="${href}${qs}">
        <div class="card vegas-card h-100 analytics-tile hub-tile">
          <div class="card-body d-flex flex-column">
            <div class="d-flex align-items-start justify-content-between mb-2">
              <div class="neon-subtitle mb-0">${escapeHtml(badge)}</div>
              <i class="bi bi-chevron-right text-warning"></i>
            </div>

            <h5 class="card-title mb-2 hub-tile-title">${escapeHtml(title)}</h5>
            <div class="hub-tile-desc flex-grow-1">${escapeHtml(desc)}</div>

            <div class="mt-3 text-warning fw-semibold tile-action">
              Open <i class="bi bi-arrow-right-short"></i>
            </div>
          </div>
        </div>
      </a>
    </div>
  `;
}

function tileDisabled({ badge = "Coming Soon", title, desc }) {
  return `
    <div class="col-12 col-md-6 col-xl-4">
      <div class="card vegas-card h-100 analytics-tile hub-tile hub-tile--disabled">
        <div class="card-body d-flex flex-column">
          <div class="d-flex align-items-start justify-content-between mb-2">
            <div class="neon-subtitle mb-0">${escapeHtml(badge)}</div>
            <span class="badge text-bg-secondary">Coming Soon</span>
          </div>

          <h5 class="card-title mb-2 hub-tile-title">${escapeHtml(title)}</h5>
          <div class="hub-tile-desc flex-grow-1">${escapeHtml(desc)}</div>
        </div>
      </div>
    </div>
  `;
}

function renderTiles(seasonId) {
  return `
    <div class="row g-3">

      ${tileLive({
        seasonId,
        href: "/analytics/survival.html",
        title: "Survival",
        desc: "Time survived, deep runs, and percentile views."
      })}

      ${tileLive({
        seasonId,
        href: "/analytics/eliminations.html",
        title: "Eliminations",
        desc: "Kill matrix, repeat eliminations, and net dominance."
      })}

      ${tileLive({
        seasonId,
        href: "/analytics/nemesis.html",
        title: "Nemesis",
        desc: "Net results, top victims, and worst matchups."
      })}

      ${tileDisabled({
        title: "Player Trends",
        desc: "Form curves, streaks, consistency, and momentum."
      })}

    </div>
  `;
}

function renderHubScaffold(root) {
  root.innerHTML = `
    <div id="data-status" class="mb-3"></div>

    <!-- Loading -->
    <div id="loading-row" class="card vegas-card mb-3">
      <div class="card-body d-flex align-items-center gap-3">
        <div class="spinner-border" role="status" aria-label="Loading"></div>
        <div class="text-muted">Loading season data…</div>
      </div>
    </div>

    <!-- Content -->
    <div id="content-row" class="d-none">

      <div class="analytics-hub-header text-center">
        <p class="lead hero-tagline mb-3">
          Crushed dreams, quantified.
        </p>

        <div class="page-title">Analytics Hub</div>
        <div class="page-subtitle mb-3">Season snapshot and analytics modules.</div>

        <div class="d-flex justify-content-center gap-3 flex-wrap">
          <span class="badge badge-vegas-gold fs-6">Spring Season 2026</span>
          <span class="badge badge-vegas-outline fs-6">Analytics Lab</span>
        </div>
      </div>

      <!-- KPIs + Overview -->
      <div class="row g-3 mb-3">

        <div class="col-12 col-md-6 col-xl-3">
          <div class="card vegas-card h-100">
            <div class="card-body">
              <div class="d-flex align-items-center justify-content-between">
                <div class="neon-subtitle mb-0">Weeks</div>
                <i class="bi bi-calendar-week text-warning"></i>
              </div>
              <div class="display-6 fw-bold mt-1" id="kpi-weeks">—</div>
              <div class="small text-muted-vegas">Weeks with recorded results.</div>
            </div>
          </div>
        </div>

        <div class="col-12 col-md-6 col-xl-3">
          <div class="card vegas-card h-100">
            <div class="card-body">
              <div class="d-flex align-items-center justify-content-between">
                <div class="neon-subtitle mb-0">Players</div>
                <i class="bi bi-people-fill text-warning"></i>
              </div>
              <div class="display-6 fw-bold mt-1" id="kpi-players">—</div>
              <div class="small text-muted-vegas">Players tracked this season.</div>
            </div>
          </div>
        </div>

        <div class="col-12 col-xl-6">
          <div class="card vegas-card h-100">
            <div class="card-body">
              <div class="d-flex align-items-center justify-content-between">
                <div class="neon-subtitle mb-0">Overview</div>
                <i class="bi bi-graph-up-arrow text-warning"></i>
              </div>
              <h5 class="card-title mt-2 mb-2">Start here</h5>
              <div class="text-muted-vegas">
                Choose a module below to explore the season. New modules will appear as they go live.
              </div>
            </div>
          </div>
        </div>

      </div>

      <!-- Tiles -->
      <div id="analytics-tiles"></div>
    </div>
  `;
}

/* -----------------------------
   Init
----------------------------- */

async function init() {
  const root = document.getElementById("page-root");
  if (!root) return;

  const seasonIdFromUrl = getSeasonIdFromUrl();
  const season = resolveSeason(seasonIdFromUrl);

  renderHubScaffold(root);

  // Season controls (shell may hide them; harmless if missing)
  const seasonSelect = byId("season-select");
  const reloadBtn = byId("reload-data-btn");

  if (seasonSelect) {
    setHtml(seasonSelect, buildSeasonOptions(season.id));
    seasonSelect.addEventListener("change", (e) => navigateWithSeason(e.target.value));
  }

  if (reloadBtn) {
    reloadBtn.addEventListener("click", () => {
      clearSeasonCache(season.id);
      navigateWithSeason(season.id);
    });
  }

  const loadingRow = byId("loading-row");
  const contentRow = byId("content-row");
  const statusEl = byId("data-status");
  const tilesEl = byId("analytics-tiles");

  show(loadingRow);
  hide(contentRow);

  try {
    const { data } = await loadSeasonData(season.id);

    const weeks = getWeekCount(data);
    const players = getPlayerCount(data);

    setHtml(byId("kpi-weeks"), weeks == null ? "—" : String(weeks));
    setHtml(byId("kpi-players"), players == null ? "—" : String(players));

    setHtml(statusEl, "");
    setHtml(tilesEl, renderTiles(season.id));
  } catch (err) {
    setHtml(
      statusEl,
      renderAlert({
        type: "danger",
        title: "Failed to load season data",
        message: err?.message || String(err)
      })
    );
  } finally {
    hide(loadingRow);
    show(contentRow);
  }
}

document.addEventListener("DOMContentLoaded", init);