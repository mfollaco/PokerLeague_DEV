console.log("Weekly Points JS Loaded");

// Load JSON
fetch("data/spring_2026.json")
  .then(r => r.json())
  .then(data => {
    console.log("DATA LOADED:", data);
    const weekly = data.weekly_points;
    renderWeeklyPoints(weekly);
  })
  .catch(err => console.error("JSON LOAD ERROR:", err));


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
