console.log("Weekly Points JS Loaded");

function formatMoney(x) {
  const n = Number(x || 0);
  return n.toLocaleString(undefined, { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

// Load JSON
fetch("data/spring_2026.json")
  .then(response => response.json())
  .then(data => {

  console.log("DATA LOADED:", data);

  console.log("Week 1 rows from JSON:",
    data.WeeklyPoints.filter(r => r.Week === 1)
  );

  const weeklyRows = data.WeeklyPoints;

  initPlayerWeeklyFinishes(data);   // ← NEW

  const weekly = groupWeeklyPoints(weeklyRows);

  renderWeeklyPoints(weekly);
})

async function loadWeekNotes(weekNumber) {
  const el = document.getElementById("week-notes");
  if (!el) return;

  // If nothing selected yet (page load), show default message
  if (!weekNumber) {
    el.innerHTML = `<p class="text-muted mb-0">No notes posted for this week.</p>`;
    return;
  }

  el.innerHTML = `<p class="text-muted mb-0">Loading Week ${weekNumber} notes…</p>`;

  const file = `data/notes/week-${String(weekNumber).padStart(2, "0")}.md`;

  try {
    const res = await fetch(file, { cache: "no-store" });

    // Missing file = strict “no notes”
    if (!res.ok) throw new Error(`Missing: ${file} (${res.status})`);

    const md = await res.text();
    if (!md.trim()) throw new Error(`Empty: ${file}`);

    // Render markdown -> HTML
    const html = marked.parse(md);
    el.innerHTML = `<div class="notes-markdown">${html}</div>`;
  } catch (err) {
    el.innerHTML = `<p class="text-muted mb-0">No notes posted for this week.</p>`;
    console.warn("[WeekNotes]", err);
  }
}


function groupWeeklyPoints(rows) {
  const map = new Map();

  rows.forEach(r => {
    const weekNum = Number(r.Week);
    if (!map.has(weekNum)) {
      map.set(weekNum, { week: weekNum, date: r.TournamentDate, results: [] });
    }

    map.get(weekNum).results.push({
      Place: r.FinishPlace,
      Player: r.Player,
      Points: r.Points,
      Payout: r.Payout || 0,
      PlayerID: r.PlayerID
    });
  });

  // week 1..N
  return Array.from(map.values()).sort((a, b) => a.week - b.week);
}


// ------------------------------------------------------------
// RENDER WEEKLY POINTS (Vegas‑styled accordion)
// ------------------------------------------------------------
function renderWeeklyPoints(weekly) {
    const container = document.getElementById("weeklyResultsTable");
    container.innerHTML = ""; // clear loading text

    weekly.forEach((week) => {
      const weekLabel = new Date(week.date).toLocaleDateString();

      const section = document.createElement("details");
      section.id = `week${week.week}`;
      section.classList.add("vegas-week-card");

      section.innerHTML = `
        <summary class="vegas-week-summary">
          <span class="neon-gold">Week ${week.week}</span>
          <span class="text-muted-vegas ms-2">(${weekLabel})</span>
        </summary>

        <div class="vegas-week-content mt-3">
          <table class="table table-dark table-hover align-middle mb-0">
            <thead class="table-gold">
              <tr>
                <th>Finish Place</th>
                <th>Player</th>
                <th>Points</th>
                <th>Payout</th>
              </tr>
            </thead>
            <tbody>
              ${week.results
                .sort((a, b) => (a.Place ?? 999) - (b.Place ?? 999))
                .map(
                  (r) => `
                    <tr>
                      <td>${r.Place ?? "DNP"}</td>
                      <td>${r.Player}</td>
                      <td>${r.Points}</td>
                      <td>${formatMoney(r.Payout || 0)}</td>
                    </tr>
                  `
                )
                .join("")}
            </tbody>
          </table>
        </div>
      `;

      container.appendChild(section);
    });

    // When a week accordion opens, load notes for that week (and close others)
    container.querySelectorAll("details.vegas-week-card").forEach((detailsEl) => {
      detailsEl.addEventListener("toggle", () => {
        if (!detailsEl.open) return;

        // Close all other weeks
        container.querySelectorAll("details.vegas-week-card").forEach((other) => {
          if (other !== detailsEl) other.open = false;
        });

        // Load notes for this week
        const weekNum = Number(detailsEl.id.replace("week", ""));
        loadWeekNotes(weekNum);

        // Scroll to notes card
        document.getElementById("week-notes")?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      });
    });

    // Default message before any week is opened
    loadWeekNotes(null);
}

async function loadWeekNotes(weekNumber) {
  const el = document.getElementById("week-notes");
  if (!el) return;

  if (!weekNumber) {
    el.innerHTML = `<p class="text-muted mb-0">Select a week to view notes.</p>`;
    return;
  }

  const weekStr = String(weekNumber).padStart(2, "0");
  const url = `data/notes/week-${weekStr}.md`;

  try {
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) throw new Error(res.status);

    const md = await res.text();
    if (!md.trim()) throw new Error("Empty notes file");
    if (typeof marked === "undefined") throw new Error("Marked not loaded");

    el.innerHTML = `<div class="notes-markdown">${marked.parse(md)}</div>`;
  } catch (err) {
    el.innerHTML = `<p class="text-muted mb-0">No notes posted for Week ${weekNumber}.</p>`;
    console.warn("[WeekNotes]", err);
  }
}

// --------------------------------------------
// Player Weekly Finishes Card
// --------------------------------------------

function initPlayerWeeklyFinishes(data) {

  const buttonsHost = document.getElementById("playerWeeklyButtons");
  const resultsHost = document.getElementById("playerWeeklyResults");

  if (!buttonsHost || !resultsHost) return;

  const weekly = Array.isArray(data.WeeklyPoints) ? data.WeeklyPoints : [];

  if (weekly.length === 0) {
    buttonsHost.innerHTML = `<span class="text-muted">No weekly data available.</span>`;
    return;
  }

  // --------------------------------------------
  // Build player list
  // --------------------------------------------

  const players = [...new Set(weekly.map(r => r.Player))].sort();

  buttonsHost.innerHTML = "";

  players.forEach(player => {

    const btn = document.createElement("button");
    btn.className = "btn btn-outline-warning btn-sm";
    btn.textContent = player;

    btn.onclick = () => {
      // remove active state from all buttons
      buttonsHost.querySelectorAll("button").forEach(b => b.classList.remove("active"));

      // set this button active
      btn.classList.add("active");

      renderPlayerWeeklyFinishes(player, weekly);
    };

    buttonsHost.appendChild(btn);

  });

}

function renderPlayerWeeklyFinishes(player, weekly) {
  const host = document.getElementById("playerWeeklyResults");
  if (!host) return;

  // 1) Filter to this player FIRST
  const rows = (Array.isArray(weekly) ? weekly : [])
    .filter(r => r.Player === player)
    .sort((a, b) => (Number(a.Week) || 0) - (Number(b.Week) || 0));

  if (rows.length === 0) {
    host.innerHTML = `<p class="text-muted mb-0">No results found.</p>`;
    return;
  }

  // 2) Compute stats from THIS player's FinishPlace only (ignore nulls)
  const finishes = rows
    .map(r => Number(r.FinishPlace))
    .filter(f => Number.isFinite(f) && f >= 1); // ignore 0 / negatives

  let avg = "—";
  let best = "—";
  let worst = "—";
  let top3 = 0;
  let wins = 0;

  if (finishes.length > 0) {
    avg = (finishes.reduce((a, b) => a + b, 0) / finishes.length).toFixed(1);
    best = Math.min(...finishes);
    worst = Math.max(...finishes);
    top3 = finishes.filter(f => f <= 3).length;
    wins = finishes.filter(f => f === 1).length;
  }

  // 3) Render badges W1..Wmax
  const maxWeek = Math.max(...rows.map(r => Number(r.Week) || 0));
  const byWeek = new Map(rows.map(r => [Number(r.Week), r]));

  let html = `
    <div class="mb-1">
      <span class="text-warning fw-semibold">${player}</span>
      <span class="text-muted small ms-2">Weekly finishes</span>
    </div>

    <div class="small mb-2 text-warning">
      Avg Finish: ${avg}
      &nbsp;|&nbsp;
      Top 3: ${top3}
      &nbsp;|&nbsp;
      Wins: ${wins}
      &nbsp;|&nbsp;
      Best: ${best}
      &nbsp;|&nbsp;
      Worst: ${worst}
    </div>

    <div class="d-flex flex-wrap gap-2">
  `;

  for (let w = 1; w <= maxWeek; w++) {
    const r = byWeek.get(w);
    let finish = (r && r.FinishPlace != null) ? Number(r.FinishPlace) : null;
    if (!Number.isFinite(finish) || finish < 1) finish = null; // treat 0 as "—"

    const label = (finish == null) ? "—" : String(finish);

    // heat-scale class by finish place
    let cls = "badge rounded-pill finish-badge finish-na";
    if (Number.isFinite(finish)) {
      cls = `badge rounded-pill finish-badge finish-${finish}`;
    }

    // add $ indicator for cash weeks (1-3)
    const cash = (Number.isFinite(finish) && finish <= 3) ? `<span class="cash">$</span>` : ``;

    html += `
      <div class="d-flex flex-column align-items-center">
        <div class="text-muted small">W${w}</div>
        <span class="${cls}" style="min-width: 2.6rem; padding:6px 8px; text-align:center;">
          ${cash}${label}
        </span>
      </div>
    `;
  }

  html += `</div>`;
  host.innerHTML = html;
}
