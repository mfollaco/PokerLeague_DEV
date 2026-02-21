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
    const rows = Array.isArray(data.ChipAndChair) ? data.ChipAndChair : [];
    const rules = data.ChipAndChairRules ?? null;
    const buildTs = data.build_ts ?? "";

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