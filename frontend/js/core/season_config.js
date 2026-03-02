export const DEFAULT_SEASON_ID = "spring_2026";

export const SEASONS = {
  spring_2026: {
    id: "spring_2026",
    name: "Spring Season 2026",
    dataPath: "../data/spring_2026.json"
  }
};

export function getSeasonIdFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get("season") || DEFAULT_SEASON_ID;
}

export function resolveSeason(seasonId) {
  return SEASONS[seasonId] || SEASONS[DEFAULT_SEASON_ID];
}
