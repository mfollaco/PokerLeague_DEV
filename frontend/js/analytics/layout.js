// frontend/js/analytics/layout.js

function getSeasonIdFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get("season");
}

function withSeason(href) {
  const season = getSeasonIdFromUrl();
  if (!season) return href;

  const url = new URL(href, window.location.origin);
  url.searchParams.set("season", season);
  return url.pathname + url.search + url.hash;
}

export function injectAnalyticsShell(options = {}) {
  const title = options.title ?? "Analytics";
  const active = options.active ?? null; // "hub" | "survival" | "eliminations" | "nemesis"
  const isHub = active === "hub";

  const homeHref = options.homeHref ?? "/index.html";
  const hubHref = options.hubHref ?? "/analytics/analytics_index.html";

  const showSeasonControls = options.showSeasonControls ?? false;
  const showBackToHub = options.showBackToHub ?? false;

  const headerHost = document.getElementById("analytics-header");
  const footerHost = document.getElementById("analytics-footer");

  const navLink = (key, label, href) => {
    const isActive = active === key;
    const cls = "nav-link" + (isActive ? " active text-warning" : "");
    return `<a class="${cls}" href="${withSeason(href)}">${label}</a>`;
  };

  const seasonControlsHtml = showSeasonControls
    ? [
        `<div class="text-muted small">Season</div>`,
        `<select id="season-select" class="form-select form-select-sm" style="min-width:220px;"></select>`,
        `<button id="reload-data-btn" class="btn btn-sm btn-outline-warning">`,
        `<i class="bi bi-arrow-clockwise"></i> Reload`,
        `</button>`,
      ].join("")
    : "";

  const backBtnHtml =
    showBackToHub && active !== "hub"
      ? `<a class="btn btn-sm btn-outline-warning" href="${withSeason(hubHref)}">← Back</a>`
      : "";

  if (headerHost) {
    headerHost.innerHTML = [
      `<nav class="navbar navbar-expand-lg navbar-dark border-bottom border-warning-subtle mb-4" style="background: rgba(0,0,0,0.35);">`,
      `  <div class="container">`,
      `    <a class="navbar-brand text-warning fw-bold" href="${homeHref}">Home</a>`,
      `    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#analyticsNav" aria-controls="analyticsNav" aria-expanded="false" aria-label="Toggle navigation">`,
      `      <span class="navbar-toggler-icon"></span>`,
      `    </button>`,
      `    <div class="collapse navbar-collapse" id="analyticsNav">`,
      `      <ul class="navbar-nav ms-auto gap-lg-1">`,
      `        <li class="nav-item">${navLink("hub", "Analytics Home", hubHref)}</li>`,
      `        <li class="nav-item">${navLink("survival", "Survival", "/analytics/survival.html")}</li>`,
      `        <li class="nav-item">${navLink("eliminations", "Eliminations", "/analytics/eliminations.html")}</li>`,
      `        <li class="nav-item">${navLink("nemesis", "Nemesis", "/analytics/nemesis.html")}</li>`,
      `      </ul>`,
      `    </div>`,
      `  </div>`,
      `</nav>`,
      ``,
      `<div class="container mb-3">`,
      `  <div class="d-flex align-items-center justify-content-between flex-wrap gap-3">`,
      `    <div>${isHub ? "" : `<div class="neon-title mb-0">${title}</div>`}</div>`,
      `    <div class="d-flex align-items-center gap-2">`,
      `      ${seasonControlsHtml}`,
      `      ${backBtnHtml}`,
      `    </div>`,
      `  </div>`,
      `</div>`,
    ].join("\n");
  }

  if (footerHost) {
    footerHost.innerHTML = [
      `<div class="container analytics-footer-note small py-4 text-center">`,
      `  • Chip &amp; A Chair PokerLeague Analytics Lab •`,
      `</div>`,
    ].join("\n");
  }
}

// ---------------------------------------------
// Auto-shell (optional): inject automatically
// if the host elements exist on the page.
// ---------------------------------------------
(function autoInjectAnalyticsShell() {
  const headerHost = document.getElementById("analytics-header");
  const footerHost = document.getElementById("analytics-footer");
  if (!headerHost || !footerHost) return;

  // Read page hints from <body data-*>
  const b = document.body;
  const title = b?.dataset?.title || "Analytics";
  const active = b?.dataset?.active || null;

  // Defaults: non-hub pages show season controls + back button
  const showSeasonControls =
    (b?.dataset?.seasonControls ?? "true") === "true";
  const showBackToHub =
    (b?.dataset?.backToHub ?? "true") === "true";

  injectAnalyticsShell({
    title,
    active,
    showSeasonControls,
    showBackToHub
  });
})();