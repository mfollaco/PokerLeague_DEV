import { getSeasonIdFromUrl } from "./core/season_config.js";
import { loadSeasonData } from "./core/data_loader.js";

console.log("Weekly Points JS Loaded");

async function initWeeklyPointsPage() {
  try {
    const seasonId = getSeasonIdFromUrl();
    const { data, season, source } = await loadSeasonData(seasonId);

    console.log("Weekly Points loaded for season:", season.id, "source:", source);
    console.log("DATA LOADED:", data);

    const weeklyRows = Array.isArray(data.WeeklyPoints) ? data.WeeklyPoints : [];
    const weekly = groupWeeklyPoints(weeklyRows);

    renderWeeklyPoints(weekly);
  } catch (err) {
    console.error("Failed to initialize weekly points page:", err);

    const container = document.getElementById("weeklyPointsTable");
    if (container) {
      container.innerHTML = `
        <div class="alert alert-danger mb-0">
          Failed to load weekly points.<br>
          <small>${err?.message || String(err)}</small>
        </div>
      `;
    }
  }
}

function groupWeeklyPoints(rows) {
  // rows: [{Week, TournamentDate, Player, FinishPlace, Points}, ...]
  const map = new Map();

  rows.forEach(r => {
    const key = r.TournamentDate; // "YYYY-MM-DD"
    if (!map.has(key)) {
      map.set(key, { date: key, results: [] });
    }
    map.get(key).results.push({
      Place: r.FinishPlace,
      Player: r.Player,
      Points: r.Points
    });
  });

  return Array.from(map.values());
}


// ------------------------------------------------------------
// RENDER WEEKLY POINTS (Vegas‑styled accordion)
// ------------------------------------------------------------
function renderWeeklyPoints(weekly) {
  const container = document.getElementById("weeklyPointsTable");
  container.innerHTML = ""; // clear loading text

  // Sort newest week first
  weekly
    .sort((a, b) => new Date(b.date) - new Date(a.date))
    .forEach((week, index) => {

      // Format date
      const weekLabel = new Date(week.date).toLocaleDateString();

      // Create <details> wrapper
      const section = document.createElement("details");
      section.id = `week${index + 1}`;
      section.classList.add("vegas-week-card");

      // Vegas styling applied via CSS classes
      section.innerHTML = `
        <summary class="vegas-week-summary">
          <span class="neon-gold">Week ${index + 1}</span>
          <span class="text-muted-vegas ms-2">(${weekLabel})</span>
        </summary>

        <div class="vegas-week-content mt-3">
          <table class="table table-dark table-hover align-middle mb-0">
            <thead class="table-gold">
              <tr>
                <th>Finish Place</th>
                <th>Player</th>
                <th>Points</th>
              </tr>
            </thead>
            <tbody>
              ${week.results
                .sort((a, b) => a.Place - b.Place)
                .map(r => `
                  <tr>
                    <td>${r.Place}</td>
                    <td>${r.Player}</td>
                    <td>${r.Points}</td>
                  </tr>
                `).join("")}
            </tbody>
          </table>
        </div>
      `;

      container.appendChild(section);
    });
}

initWeeklyPointsPage();