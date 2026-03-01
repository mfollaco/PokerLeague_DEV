// frontend/js/pages/eliminations.js
// Eliminations (LAB): Leaderboard + Filter-by-Killer + Filter-by-Victim + Breakdown + Net Dominance
//
// - Removed Repeat Eliminations section
// - Removed search-by-victim + clear
// - Added: Filter by Killer (shows that killer's prey list)
// - Added: Filter by Victim (shows who killed them + counts)

import { initAnalyticsPage } from "../core/page_bootstrap.js";
import { escapeHtml as esc } from "../core/dom_utils.js";

initAnalyticsPage({
  render: async (data) => {
    const root = document.getElementById("page-root");
    if (!root) throw new Error("Missing #page-root in eliminations.html");

    root.innerHTML = `
      <div class="subtle-help mb-3">Kill matrix, drilldowns, and net dominance.</div>

      <div id="elimKpis" class="d-flex flex-wrap gap-2 mb-3"></div>

      <!-- Leaderboard -->
      <div class="card vegas-card mb-3">
        <div class="card-body">
          <div class="km-title text-center mb-3">Eliminations Leaderboard</div>
          <div id="leaderboardWrap"><div class="text-muted">Loading…</div></div>
        </div>
      </div>

      <!-- Filters -->
      <div class="card vegas-card mb-3">
        <div class="card-body">
          <div class="km-title text-center mb-3">Drilldowns</div>

          <div class="row g-3">
            <div class="col-12 col-lg-6">
              <div class="neon-subtitle mb-2">Filter by Killer</div>
              <label class="form-label text-muted mb-1">Killer</label>
              <select id="killerFilter" class="form-select form-select-sm">
                <option value="">Select a killer…</option>
              </select>

              <div class="mt-3">
                <div id="killerBreakdownWrap"><div class="text-muted">Select a killer to see their prey.</div></div>
              </div>
            </div>

            <div class="col-12 col-lg-6">
              <div class="neon-subtitle mb-2">Filter by Victim</div>
              <label class="form-label text-muted mb-1">Victim</label>
              <select id="victimFilter" class="form-select form-select-sm">
                <option value="">Select a victim…</option>
              </select>

              <div class="mt-3">
                <div id="victimBreakdownWrap"><div class="text-muted">Select a victim to see who eliminated them.</div></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Net Dominance -->
      <div class="card vegas-card">
        <div class="card-body">
          <div class="km-title text-center mb-2">Net Dominance</div>
          <div class="text-muted small mb-3">
            Net Dominance = eliminations made minus times eliminated. Positive means they eliminate more than they get eliminated.
          </div>
          <div id="netWrap"><div class="text-muted">Loading…</div></div>
        </div>
      </div>
    `;

    const pairRows = Array.isArray(data?.EliminationsPairCounts) ? data.EliminationsPairCounts : [];
    if (!pairRows.length) {
      setWrap("leaderboardWrap", `<div class="text-muted">No elimination data found (EliminationsPairCounts missing/empty).</div>`);
      setWrap("killerBreakdownWrap", "");
      setWrap("victimBreakdownWrap", "");
      setWrap("netWrap", "");
      setWrap("elimKpis", "");
      return;
    }

    const model = buildElimModel(pairRows);

    renderKpis(model);
    renderLeaderboard(model);
    renderNetDominance(pairRows);

    populateKillerFilter(model);
    populateVictimFilter(model);

    const killerSel = document.getElementById("killerFilter");
    const victimSel = document.getElementById("victimFilter");

    killerSel?.addEventListener("change", () => {
      const killer = killerSel.value || "";
      renderKillerBreakdown(model, killer);
    });

    victimSel?.addEventListener("change", () => {
      const victim = victimSel.value || "";
      renderVictimBreakdown(model, victim);
    });

    // initial blank state
    renderKillerBreakdown(model, "");
    renderVictimBreakdown(model, "");
  },
});

/* ===============================
   Helpers
================================ */
function setWrap(id, html) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = html;
}

function badge(label, value) {
  return `<span class="badge bg-warning text-dark">${esc(label)}: ${esc(String(value))}</span>`;
}

/* ===============================
   Model
================================ */
function buildElimModel(pairRows) {
  const killerTotals = new Map();   // killer -> total kills
  const victimTotals = new Map();   // victim -> total deaths
  const killerVictims = new Map();  // killer -> Map(victim -> count)
  const victimKillers = new Map();  // victim -> Map(killer -> count)

  const players = new Set();
  let totalElims = 0;

  for (const r of pairRows) {
    const k = (r?.Killer ?? "").trim();
    const v = (r?.Victim ?? "").trim();
    const c = Number(r?.Count ?? 0) || 0;
    if (!k || !v || c <= 0) continue;

    totalElims += c;
    players.add(k);
    players.add(v);

    killerTotals.set(k, (killerTotals.get(k) || 0) + c);
    victimTotals.set(v, (victimTotals.get(v) || 0) + c);

    if (!killerVictims.has(k)) killerVictims.set(k, new Map());
    const vm = killerVictims.get(k);
    vm.set(v, (vm.get(v) || 0) + c);

    if (!victimKillers.has(v)) victimKillers.set(v, new Map());
    const km = victimKillers.get(v);
    km.set(k, (km.get(k) || 0) + c);
  }

  const killerList = [...killerTotals.entries()]
    .map(([killer, total]) => ({ killer, total }))
    .sort((a, b) => (b.total - a.total) || a.killer.localeCompare(b.killer));

  const victimList = [...victimTotals.entries()]
    .map(([victim, total]) => ({ victim, total }))
    .sort((a, b) => (b.total - a.total) || a.victim.localeCompare(b.victim));

  return {
    pairRows,
    killerTotals,
    victimTotals,
    killerVictims,
    victimKillers,
    killerList,
    victimList,
    totalElims,
    players,
  };
}

/* ===============================
   KPIs
================================ */
function renderKpis(model) {
  const { totalElims, killerList, victimList } = model;

  const topKiller = killerList[0] || null;
  const mostEliminated = victimList[0] || null;

  let html = "";
  html += badge("Total Eliminations", totalElims);
  html += badge("Killers", killerList.length);

  if (topKiller) html += badge("Top Killer", `${topKiller.killer} (${topKiller.total})`);

  setWrap("elimKpis", html);
}

/* ===============================
   Leaderboard (Killers)
================================ */
function renderLeaderboard(model) {
  const wrap = document.getElementById("leaderboardWrap");
  if (!wrap) return;

  const rows = model.killerList.map(r => {
    const victimsMap = model.killerVictims.get(r.killer) || new Map();
    const uniqueVictims = victimsMap.size;

    return {
      Killer: r.killer,
      Total: r.total,
      UniqueVictims: uniqueVictims,
    };
  });

  let html = `
    <div class="table-responsive">
      <table class="table table-dark table-striped table-hover align-middle mb-0">
        <thead>
          <tr>
            <th class="text-warning">Killer</th>
            <th class="text-warning text-end">Total Kills</th>
            <th class="text-warning text-end">Unique Victims</th>
          </tr>
        </thead>
        <tbody>
  `;

  for (const r of rows) {
    html += `
      <tr>
        <td>${esc(r.Killer)}</td>
        <td class="text-end fw-semibold">${esc(String(r.Total))}</td>
        <td class="text-end">${esc(String(r.UniqueVictims))}</td>
      </tr>
    `;
  }

  html += `</tbody></table></div>`;
  wrap.innerHTML = html;
}

/* ===============================
   Filter by Killer -> Prey breakdown
================================ */
function populateKillerFilter(model) {
  const sel = document.getElementById("killerFilter");
  if (!sel) return;

  const opts = model.killerList.map(x =>
    `<option value="${esc(x.killer)}">${esc(x.killer)} (${x.total})</option>`
  );

  sel.innerHTML = `<option value="">Select a killer…</option>` + opts.join("");
}

function renderKillerBreakdown(model, killer) {
  const wrap = document.getElementById("killerBreakdownWrap");
  if (!wrap) return;

  if (!killer) {
    wrap.innerHTML = `<div class="text-muted">Select a killer to see their prey.</div>`;
    return;
  }

  const victimsMap = model.killerVictims.get(killer);
  if (!victimsMap || victimsMap.size === 0) {
    wrap.innerHTML = `<div class="text-muted">No victim data found for ${esc(killer)}.</div>`;
    return;
  }

  const victims = [...victimsMap.entries()]
    .map(([victim, count]) => ({ victim, count }))
    .sort((a, b) => (b.count - a.count) || a.victim.localeCompare(b.victim));

  const totalKills = victims.reduce((s, x) => s + x.count, 0);

  let html = `
    <div class="d-flex flex-wrap gap-2 mb-2">
      ${badge("Killer", killer)}
      ${badge("Total Kills", totalKills)}
      ${badge("Unique Victims", victims.length)}
    </div>

    <div class="table-responsive">
      <table class="table table-dark table-striped table-hover align-middle mb-0">
        <thead>
          <tr>
            <th class="text-warning">Victim</th>
            <th class="text-warning text-end">Times</th>
          </tr>
        </thead>
        <tbody>
  `;

  for (const v of victims) {
    html += `
      <tr>
        <td>${esc(v.victim)}</td>
        <td class="text-end fw-semibold">${esc(String(v.count))}</td>
      </tr>
    `;
  }

  html += `</tbody></table></div>`;
  wrap.innerHTML = html;
}

/* ===============================
   Filter by Victim -> Killer breakdown
================================ */
function populateVictimFilter(model) {
  const sel = document.getElementById("victimFilter");
  if (!sel) return;

  const opts = model.victimList.map(x =>
    `<option value="${esc(x.victim)}">${esc(x.victim)} (${x.total})</option>`
  );

  sel.innerHTML = `<option value="">Select a victim…</option>` + opts.join("");
}

function renderVictimBreakdown(model, victim) {
  const wrap = document.getElementById("victimBreakdownWrap");
  if (!wrap) return;

  if (!victim) {
    wrap.innerHTML = `<div class="text-muted">Select a victim to see who eliminated them.</div>`;
    return;
  }

  const killersMap = model.victimKillers.get(victim);
  if (!killersMap || killersMap.size === 0) {
    wrap.innerHTML = `<div class="text-muted">No killer data found for ${esc(victim)}.</div>`;
    return;
  }

  const killers = [...killersMap.entries()]
    .map(([killer, count]) => ({ killer, count }))
    .sort((a, b) => (b.count - a.count) || a.killer.localeCompare(b.killer));

  const totalDeaths = killers.reduce((s, x) => s + x.count, 0);

  let html = `
    <div class="d-flex flex-wrap gap-2 mb-2">
      ${badge("Victim", victim)}
      ${badge("Total Eliminated", totalDeaths)}
      ${badge("Unique Killers", killers.length)}
    </div>

    <div class="table-responsive">
      <table class="table table-dark table-striped table-hover align-middle mb-0">
        <thead>
          <tr>
            <th class="text-warning">Killer</th>
            <th class="text-warning text-end">Times</th>
          </tr>
        </thead>
        <tbody>
  `;

  for (const k of killers) {
    html += `
      <tr>
        <td>${esc(k.killer)}</td>
        <td class="text-end fw-semibold">${esc(String(k.count))}</td>
      </tr>
    `;
  }

  html += `</tbody></table></div>`;
  wrap.innerHTML = html;
}

/* ===============================
   Net Dominance
================================ */
function renderNetDominance(rows) {
  const wrap = document.getElementById("netWrap");
  if (!wrap) return;

  const netMap = new Map();

  for (const r of rows) {
    const k = (r?.Killer ?? "").trim();
    const v = (r?.Victim ?? "").trim();
    const c = Number(r?.Count ?? 0) || 0;
    if (!k || !v || c <= 0) continue;

    netMap.set(k, (netMap.get(k) || 0) + c);
    netMap.set(v, (netMap.get(v) || 0) - c);
  }

  const netRows = [...netMap.entries()]
    .map(([player, net]) => ({ player, net }))
    .sort((a, b) => (b.net - a.net) || a.player.localeCompare(b.player));

  let html = `
    <div class="table-responsive">
      <table class="table table-dark table-striped table-hover align-middle mb-0">
        <thead>
          <tr>
            <th class="text-warning">Player</th>
            <th class="text-warning text-end">Net</th>
          </tr>
        </thead>
        <tbody>
  `;

  for (const r of netRows) {
    const cls =
      r.net > 0 ? "text-success fw-semibold" :
      r.net < 0 ? "text-danger fw-semibold" :
      "text-muted";

    html += `
      <tr>
        <td>${esc(r.player)}</td>
        <td class="text-end ${cls}">${esc(String(r.net))}</td>
      </tr>
    `;
  }

  html += `</tbody></table></div>`;
  wrap.innerHTML = html;
}