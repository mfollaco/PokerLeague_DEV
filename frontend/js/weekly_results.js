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

  // weekly is already sorted by week number in groupWeeklyResults()
  weekly.forEach((week) => {

      // Format date
      const weekLabel = new Date(week.date).toLocaleDateString();

      // Create <details> wrapper
      const section = document.createElement("details");
      section.id = `week${week.week}`;
      section.classList.add("vegas-week-card");

      // Vegas styling applied via CSS classes
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
                .map(r => `
                  <tr>
                    <td>${r.Place}</td>
                    <td>${r.Player}</td>
                    <td>${r.Points}</td>
                    <td>${formatMoney(r.Payout  || 0)}</td>
                  </tr>
                `).join("")}
            </tbody>
          </table>
        </div>
      `;

      container.appendChild(section);
    });
}
