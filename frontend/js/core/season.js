 import {
  resolveSeasonConfig,
  getAllSeasons,
  resolveSeasonIdFromUrl
} from "./season_config.js";

export async function loadSeason() {
  const season = resolveSeasonConfig();

  const response = await fetch(season.dataPath, { cache: "no-store" });

  if (!response.ok) {
    throw new Error(`Failed to load season data: ${season.dataPath}`);
  }

  const data = await response.json();

  return {
    seasonId: season.id,
    seasonLabel: season.displayLabel,
    seasonShortLabel: season.shortLabel,
    data
  };
}

export function initSeasonSelector() {
  const selector = document.getElementById("seasonSelector");
  if (!selector) return;

  const seasons = getAllSeasons();
  const currentSeasonId = resolveSeasonIdFromUrl();

  selector.innerHTML = seasons
    .map(
      (season) =>
        `<option value="${season.id}">${season.shortLabel}</option>`
    )
    .join("");

  selector.value = currentSeasonId;

  selector.addEventListener("change", () => {
    const selectedSeasonId = selector.value;
    const url = new URL(window.location.href);
    url.searchParams.set("season", selectedSeasonId);
    window.location.href = url.toString();
  });
}

export function preserveSeasonInNavigation(root = document) {
  const seasonId = resolveSeasonIdFromUrl();

  root.querySelectorAll("a[href]").forEach((link) => {
    const href = link.getAttribute("href");
    if (!href || href.startsWith("#") || href.startsWith("mailto:")) return;

    const url = new URL(href, window.location.href);
    if (url.origin !== window.location.origin) return;
    if (!url.pathname.endsWith(".html") && !url.pathname.endsWith("/")) return;

    url.searchParams.set("season", seasonId);
    link.setAttribute("href", `${url.pathname}${url.search}${url.hash}`);
  });
}

function initSeasonNavigation() {
  preserveSeasonInNavigation();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initSeasonNavigation);
} else {
  initSeasonNavigation();
}
