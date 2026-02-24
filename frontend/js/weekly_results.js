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

  // 👇 ADD THIS
  console.log("Week 1 rows from JSON:",
    data.WeeklyPoints.filter(r => r.Week === 1)
  );

  const weeklyRows = data.WeeklyPoints;
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
                .sort((a, b) => a.Place - b.Place)
                .map(
                  (r) => `
                    <tr>
                      <td>${r.Place}</td>
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
