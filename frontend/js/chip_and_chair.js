// frontend/js/chip-and-chair.js

let cacRows = [];
let cacSort = { key: "TotalStack", dir: "desc" }; // default sort

function fmtInt(n) {
  const x = Number(n) || 0;
  return x.toLocaleString();
}

function sortRows(rows, key, dir) {
  const mult = dir === "asc" ? 1 : -1;

  return [...rows].sort((a, b) => {
    const av = a?.[key];
    const bv = b?.[key];

    const aNum = Number(av);
    const bNum = Number(bv);

    const aIsNum = !Number.isNaN(aNum);
    const bIsNum = !Number.isNaN(bNum);

    if (aIsNum && bIsNum) {
      if (aNum !== bNum) return (aNum - bNum) * mult;
    } else {
      const aStr = String(av ?? "");
      const bStr = String(bv ?? "");
      const cmp = aStr.localeCompare(bStr);
      if (cmp !== 0) return cmp * mult;
    }

    // stable tiebreak
    return String(a?.Player ?? "").localeCompare(String(b?.Player ?? ""));
  });
}

function renderKpis(rules, rows, buildTs) {
  // Update "As of"
  const asofEl = document.getElementById("cac-asof");
  if (asofEl) asofEl.textContent = buildTs ? `As of ${buildTs}` : "—";

  // Rules with defaults
  const base = rules?.base_stack ?? 6500;
  const mult = rules?.season_points_chip_multiplier ?? 150;

  // Totals + leader
  const totalChips = (rows || []).reduce((sum, r) => sum + (Number(r.TotalStack) || 0), 0);

  const leader = [...(rows || [])].sort(
    (a, b) => (Number(b.TotalStack) || 0) - (Number(a.TotalStack) || 0)
  )[0];

  // Helper to safely set text
  const setText = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  };

  // Write into your STATIC KPI HTML ids
  setText("kpi-base-stack", fmtInt(base));
  setText("kpi-points-rate", fmtInt(mult));
  setText("kpi-total-chips", fmtInt(totalChips));

  setText("kpi-leader-name", leader?.Player ?? "—");
  setText(
    "kpi-leader-stack",
    leader ? `${fmtInt(leader.TotalStack)} chips` : "—"
  );
}

function renderWeek11Payouts(payouts) {
  const host = document.getElementById("week11PayoutsBody");
  const poolText = document.getElementById("week11PrizePoolText");

  if (!host) return;

  const rows = Array.isArray(payouts) ? payouts : [];
  host.innerHTML = "";

  if (rows.length === 0) {
    host.innerHTML = `
      <div class="col-12">
        <div class="text-muted">
          <span class="badge bg-secondary me-2">Pending</span>
          Results will appear automatically after Week 11 payouts are entered.
        </div>
    `;

    if (poolText) {
      poolText.textContent = `Prize Pool: $1120`;
    }

    return;
  }

  const places = ["1st Place","2nd Place","3rd Place","4th Place","5th Place","6th Place"];

  rows.forEach((p, i) => {
    const place = places[i] ?? `${i+1}th Place`;
    const name = p.Player ?? "";
    const amt = `$${Number(p.Amount ?? 0).toFixed(0)}`;

    const col = document.createElement("div");
    col.className = "col-12 col-md-6 col-lg-4";

    col.innerHTML = `
      <div class="p-3 rounded border border-gold bg-dark h-100">
        <div class="text-warning fw-semibold mb-1">${place}</div>
        <div class="fs-5 fw-bold">${name || "—"}</div>
        <div class="text-muted small mt-1">${amt}</div>
      </div>
    `;

    host.appendChild(col);
  });

  // prize pool (sum of payouts)
  const pool = rows.reduce((a,b)=>a + Number(b.Amount || 0),0);

  if (poolText) {
    poolText.textContent = `Prize Pool: $${pool.toFixed(0)}`;
  }
}

function renderTable(rows) {
  const tbody = document.getElementById("cac-body");
  if (!tbody) return;

  tbody.innerHTML = "";

  rows.forEach((r) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="fw-bold">${fmtInt(r.TotalStack)}</td>
      <td>${r.Player ?? ""}</td>
      <td>${fmtInt(r.BaseStack)}</td>
      <td>${fmtInt(r.ChipsFromSeasonPoints)}</td>
      <td>${fmtInt(r.TotalEliminations)}</td>
      <td>${fmtInt(r.ChipsFromTotalElims)}</td>
      <td>${fmtInt(r.RepeatElimCount)}</td>
      <td>${fmtInt(r.ChipsFromRepeatElims)}</td>
      <td>${fmtInt(r.HighValueElimCount)}</td>
      <td>${fmtInt(r.ChipsFromHighValueElims)}</td>
    `;
    tbody.appendChild(tr);
  });
}

function wireSortHeaders() {
  document.querySelectorAll("#cacTable th[data-sort]").forEach((th) => {
    th.addEventListener("click", () => {
      const key = th.dataset.sort;

      if (cacSort.key === key) {
        cacSort.dir = cacSort.dir === "asc" ? "desc" : "asc";
      } else {
        cacSort.key = key;
        cacSort.dir = "desc";
      }

      const sorted = sortRows(cacRows, cacSort.key, cacSort.dir);
      renderTable(sorted);
    });
  });
}

async function initChipAndChair() {
  try {
    const res = await fetch("data/spring_2026.json");
    const data = await res.json();

    // These keys are what your exporter is writing:
    const rows = Array.isArray(data.ChipAndChairStacks) ? data.ChipAndChairStacks : [];
    const rules = data.ChipAndChairRules ?? null;
    const buildTs = data.build_ts ?? "";

    const payouts = Array.isArray(data.ChipAndChairPayouts) ? data.ChipAndChairPayouts : [];
    renderWeek11Payouts(payouts);

    cacRows = rows;

    renderKpis(rules, rows, buildTs);

    const sorted = sortRows(rows, cacSort.key, cacSort.dir);
    renderTable(sorted);
    wireSortHeaders();
  } catch (err) {
    console.error(err);
    const tbody = document.getElementById("cac-body");
    if (tbody) {
      tbody.innerHTML = `<tr><td colspan="10" class="text-center text-danger">Failed to load Chip &amp; Chair data.</td></tr>`;
    }
  }
}

document.addEventListener("DOMContentLoaded", initChipAndChair);