// frontend/js/core/eliminations_engine.js
// Pure calculation layer (no DOM). Reuse across Eliminations + Nemesis + future charts.

function normName(v) {
  return String(v ?? "").trim();
}

// Accepts many possible shapes and returns { killer, victim } or null
export function normalizeElimEvent(e) {
  if (!e || typeof e !== "object") return null;

  const killer =
    e.Killer ?? e.killer ?? e.killer_name ?? e.killerName ?? e.Eliminator ?? e.eliminator;
  const victim =
    e.Victim ?? e.victim ?? e.victim_name ?? e.victimName ?? e.Eliminated ?? e.eliminated;

  const k = normName(killer);
  const v = normName(victim);
  if (!k || !v) return null;
  if (k === v) return null; // ignore self
  return { killer: k, victim: v };
}

export function buildElimIndex(eventsRaw) {
  const events = [];
  for (const e of (eventsRaw ?? [])) {
    const x = normalizeElimEvent(e);
    if (x) events.push(x);
  }

  // Collect players
  const playerSet = new Set();
  for (const { killer, victim } of events) {
    playerSet.add(killer);
    playerSet.add(victim);
  }
  const players = [...playerSet].sort((a, b) => a.localeCompare(b));

  // Matrix counts: killer -> victim -> n
  const matrix = new Map(); // Map<killer, Map<victim, count>>
  const killsBy = new Map(); // Map<killer, n>
  const deathsBy = new Map(); // Map<victim, n>

  for (const p of players) {
    matrix.set(p, new Map());
    killsBy.set(p, 0);
    deathsBy.set(p, 0);
  }

  for (const { killer, victim } of events) {
    killsBy.set(killer, (killsBy.get(killer) ?? 0) + 1);
    deathsBy.set(victim, (deathsBy.get(victim) ?? 0) + 1);

    const row = matrix.get(killer) ?? new Map();
    row.set(victim, (row.get(victim) ?? 0) + 1);
    matrix.set(killer, row);
  }

  return { events, players, matrix, killsBy, deathsBy };
}

export function getTopKiller(killsBy) {
  let best = { player: null, kills: 0 };
  for (const [p, k] of killsBy.entries()) {
    if (k > best.kills) best = { player: p, kills: k };
  }
  return best;
}

export function computeRepeatPairs(events, minTimes = 2) {
  // Pair key: killer|||victim
  const counts = new Map();
  for (const { killer, victim } of (events ?? [])) {
    const key = `${killer}|||${victim}`;
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }

  const rows = [];
  for (const [key, times] of counts.entries()) {
    if (times >= minTimes) {
      const [killer, victim] = key.split("|||");
      rows.push({ killer, victim, times });
    }
  }

  rows.sort((a, b) => (b.times - a.times) || a.killer.localeCompare(b.killer) || a.victim.localeCompare(b.victim));

  const totalRepeatElims = rows.reduce((sum, r) => sum + (r.times - 1), 0); // “extra” repeats beyond first
  const topPair = rows[0] ? { killer: rows[0].killer, victim: rows[0].victim, times: rows[0].times } : null;

  return {
    repeatPairs: rows,
    repeatPairsCount: rows.length,
    repeatEliminations: totalRepeatElims,
    topPair
  };
}

export function computeNemesisTable(players, matrix) {
  // For each victim V: find killer K with max matrix[K][V]
  const rows = [];

  for (const victim of players) {
    let bestKiller = null;
    let bestTimes = 0;

    for (const killer of players) {
      if (killer === victim) continue;
      const times = matrix.get(killer)?.get(victim) ?? 0;
      if (times > bestTimes) {
        bestTimes = times;
        bestKiller = killer;
      }
    }

    rows.push({
      player: victim,
      nemesis: bestTimes > 0 ? bestKiller : "—",
      times: bestTimes > 0 ? bestTimes : "—"
    });
  }

  // Sort: strongest nemesis first
  rows.sort((a, b) => {
    const ta = a.times === "—" ? -1 : a.times;
    const tb = b.times === "—" ? -1 : b.times;
    return (tb - ta) || String(a.player).localeCompare(String(b.player));
  });

  return rows;
}

export function computeFavoriteVictimTable(players, matrix) {
  // For each killer K: find victim V with max matrix[K][V]
  const rows = [];

  for (const killer of players) {
    let bestVictim = null;
    let bestTimes = 0;

    for (const victim of players) {
      if (killer === victim) continue;
      const times = matrix.get(killer)?.get(victim) ?? 0;
      if (times > bestTimes) {
        bestTimes = times;
        bestVictim = victim;
      }
    }

    rows.push({
      player: killer,
      topVictim: bestTimes > 0 ? bestVictim : "—",
      times: bestTimes > 0 ? bestTimes : "—"
    });
  }

  rows.sort((a, b) => {
    const ta = a.times === "—" ? -1 : a.times;
    const tb = b.times === "—" ? -1 : b.times;
    return (tb - ta) || String(a.player).localeCompare(String(b.player));
  });

  return rows;
}

export function computeNetRows(players, killsBy, deathsBy, matrix) {
  // NetScore = kills - deaths
  // TopNetVictim: victim where (K->V - V->K) is max positive
  // WorstNetNemesis: opponent where (K->O - O->K) is most negative
  const rows = [];

  for (const p of players) {
    const kills = killsBy.get(p) ?? 0;
    const deaths = deathsBy.get(p) ?? 0;
    const net = kills - deaths;

    let topVictim = "—", topNet = 0;
    let worstNemesis = "—", worstNet = 0; // negative

    for (const o of players) {
      if (o === p) continue;
      const pv = matrix.get(p)?.get(o) ?? 0;
      const vp = matrix.get(o)?.get(p) ?? 0;
      const diff = pv - vp;

      if (diff > topNet) {
        topNet = diff;
        topVictim = o;
      }
      if (diff < worstNet) {
        worstNet = diff;
        worstNemesis = o;
      }
    }

    rows.push({
      Player: p,
      NetScore: net,
      TopVictim: topVictim,
      TopNet: topNet,
      WorstNemesis: worstNemesis,
      WorstNet: worstNet
    });
  }

  rows.sort((a, b) => (b.NetScore - a.NetScore) || a.Player.localeCompare(b.Player));
  return rows;
}