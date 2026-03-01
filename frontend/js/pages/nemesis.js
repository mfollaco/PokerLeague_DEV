// frontend/js/pages/nemesis.js
// Nemesis / Favorite Victim / Who's Your Daddy (from season JSON: EliminationsPairCounts)

import { initAnalyticsPage } from "../core/page_bootstrap.js";

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  }[c]));
}

// out[killer] -> Map(victim -> count)
// incoming[victim] -> Map(killer -> count)
function buildMaps(pairRows) {
  const out = new Map();
  const incoming = new Map();
  const players = new Set();

  for (const r of pairRows) {
    const killer = String(r.Killer ?? "").trim();
    const victim = String(r.Victim ?? "").trim();
    const count = Number(r.Count) || 0;
    if (!killer || !victim || count <= 0) continue;

    players.add(killer);
    players.add(victim);

    if (!out.has(killer)) out.set(killer, new Map());
    out.get(killer).set(victim, (out.get(killer).get(victim) || 0) + count);

    if (!incoming.has(victim)) incoming.set(victim, new Map());
    incoming.get(victim).set(killer, (incoming.get(victim).get(killer) || 0) + count);
  }

  return {
    out,
    incoming,
    players: Array.from(players).sort((a, b) => a.localeCompare(b)),
  };
}

function sumMap(map) {
  let s = 0;
  if (!map) return 0;
  for (const v of map.values()) s += Number(v) || 0;
  return s;
}

// returns ties for max value (sorted alpha)
function topTiesFromMap(map) {
  if (!map || map.size === 0) return { names: [], count: 0 };

  let max = 0;
  for (const v of map.values()) max = Math.max(max, Number(v) || 0);
  if (max <= 0) return { names: [], count: 0 };

  const names = [];
  for (const [name, v] of map.entries()) {
    if ((Number(v) || 0) === max) names.push(String(name));
  }
  names.sort((a, b) => a.localeCompare(b));
  return { names, count: max };
}

function buildNemesisRows(players, incoming, out) {
  const rows = [];

  for (const p of players) {
    const inMap = incoming.get(p) || new Map(); // who killed p
    const outMap = out.get(p) || new Map();     // who p killed

    const nem = topTiesFromMap(inMap);
    const fav = topTiesFromMap(outMap);

    rows.push({
      Player: p,
      TotalDeaths: sumMap(inMap),
      TotalKills: sumMap(outMap),

      Nemesis: nem.names.length ? nem.names.join(", ") : "—",
      NemesisCount: nem.count,

      FavoriteVictim: fav.names.length ? fav.names.join(", ") : "—",
      FavoriteVictimCount: fav.count,
    });
  }

  // Most "owned" first, then more deaths, then name
  rows.sort((a, b) =>
    (b.NemesisCount - a.NemesisCount) ||
    (b.TotalDeaths - a.TotalDeaths) ||
    a.Player.localeCompare(b.Player)
  );

  return rows;
}

// Victim-centric leaderboard: who eliminated you most (ties comma-separated)
function buildDaddyRows(players, incoming) {
  const rows = [];

  for (const victim of players) {
    const killersMap = incoming.get(victim) || new Map();

    let totalDeaths = 0;
    for (const cnt of killersMap.values()) totalDeaths += Number(cnt) || 0;

    const top = topTiesFromMap(killersMap); // names = killers, count = max kills vs victim

    rows.push({
      Player: victim,
      Daddy: top.names.length ? top.names.join(", ") : "—",
      DaddyCount: top.count || 0,
      TotalDeaths: totalDeaths || 0,
    });
  }

  // Sort: most "owned" first, then more total deaths, then name
  rows.sort((a, b) =>
    (b.DaddyCount - a.DaddyCount) ||
    (b.TotalDeaths - a.TotalDeaths) ||
    a.Player.localeCompare(b.Player)
  );

  return rows;
}

// ---------- renderers ----------

function renderKpis(rows) {
  const wrap = document.getElementById("nemesisKpis");
  if (!wrap) return;

  const totalPlayers = rows.length;

  const topKiller = totalPlayers
    ? [...rows].sort((a, b) =>
        (b.TotalKills - a.TotalKills) || a.Player.localeCompare(b.Player)
      )[0]
    : null;

  const badge = (label, value) =>
    `<span class="badge bg-warning text-dark me-2">${esc(label)}: ${esc(value)}</span>`;

  wrap.innerHTML =
    badge("Players", totalPlayers) +
    (topKiller ? badge("Top Kills", `${topKiller.Player} (${topKiller.TotalKills})`) : "");
}

function renderNemesisTable(rows) {
  const wrap = document.getElementById("nemesisWrap");
  if (!wrap) return;

  wrap.innerHTML = `
    <div class="table-responsive">
      <table class="table table-dark table-striped table-hover align-middle mb-0">
        <thead>
          <tr>
            <th class="text-warning">Player</th>
            <th class="text-warning">Nemesis</th>
            <th class="text-warning text-end">Times</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map(r => `
            <tr>
              <td>${esc(r.Player)}</td>
              <td>${esc(r.Nemesis)}</td>
              <td class="text-end">${r.NemesisCount ? esc(r.NemesisCount) : "—"}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderVictimTable(rows) {
  const wrap = document.getElementById("victimWrap");
  if (!wrap) return;

  // Sort by favorite victim count desc, then total kills desc, then player
  const sorted = [...rows].sort((a, b) =>
    (b.FavoriteVictimCount - a.FavoriteVictimCount) ||
    (b.TotalKills - a.TotalKills) ||
    a.Player.localeCompare(b.Player)
  );

  wrap.innerHTML = `
    <div class="table-responsive">
      <table class="table table-dark table-striped table-hover align-middle mb-0">
        <thead>
          <tr>
            <th class="text-warning">Player</th>
            <th class="text-warning">Top Victim</th>
            <th class="text-warning text-end">Times</th>
          </tr>
        </thead>
        <tbody>
          ${sorted.map(r => `
            <tr>
              <td>${esc(r.Player)}</td>
              <td>${esc(r.FavoriteVictim)}</td>
              <td class="text-end">${r.FavoriteVictimCount ? esc(r.FavoriteVictimCount) : "—"}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderDaddyTable(rows) {
  const wrap = document.getElementById("daddyWrap");
  if (!wrap) return;

  wrap.innerHTML = `
    <div class="table-responsive">
      <table class="table table-dark table-striped table-hover align-middle mb-0">
        <thead>
          <tr>
            <th class="text-warning">Player</th>
            <th class="text-warning">Who’s Your Daddy</th>
            <th class="text-warning text-end">Times</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map(r => `
            <tr>
              <td>${esc(r.Player)}</td>
              <td>${esc(r.Daddy)}</td>
              <td class="text-end">${r.DaddyCount ? esc(r.DaddyCount) : "—"}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

// ---------- page bootstrap ----------

initAnalyticsPage({
  render: async (data) => {
    const root = document.getElementById("page-root");
    if (!root) throw new Error("Missing #page-root in nemesis.html");

    root.innerHTML = `
      <div class="subtle-help mb-2">Rivalries and ownership (based on eliminations). Ties are comma-separated.</div>

      <div id="nemesisKpis" class="d-flex flex-wrap gap-2 mb-3"></div>

      <div class="row g-3">
        <div class="col-12 col-lg-6">
          <div class="card vegas-card h-100">
            <div class="card-body">
              <div class="km-title text-center mb-2">Nemesis</div>
              <div id="nemesisWrap"><div class="text-muted">Loading…</div></div>
            </div>
          </div>
        </div>

        <div class="col-12 col-lg-6">
          <div class="card vegas-card h-100">
            <div class="card-body">
              <div class="km-title text-center mb-2">Favorite Victim</div>
              <div id="victimWrap"><div class="text-muted">Loading…</div></div>
            </div>
          </div>
        </div>

        <div class="col-12">
          <div class="card vegas-card">
            <div class="card-body">
              <div class="km-title text-center mb-2">Who’s Your Daddy</div>
              <div class="subtle-help mb-2">
                For each player, shows who eliminated them the most (ties shown).
              </div>
              <div id="daddyWrap"><div class="text-muted">Loading…</div></div>
            </div>
          </div>
        </div>
      </div>
    `;

    const pairRows = Array.isArray(data?.EliminationsPairCounts) ? data.EliminationsPairCounts : [];
    if (!pairRows.length) {
      const msg = `<div class="text-muted">No EliminationsPairCounts found for this season.</div>`;
      ["nemesisWrap", "victimWrap", "daddyWrap"].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = msg;
      });
      renderKpis([]);
      return;
    }

    const { out, incoming, players } = buildMaps(pairRows);

    const nemRows = buildNemesisRows(players, incoming, out);
    renderKpis(nemRows);
    renderNemesisTable(nemRows);
    renderVictimTable(nemRows);

    const daddyRows = buildDaddyRows(players, incoming);
    renderDaddyTable(daddyRows);
  }
});