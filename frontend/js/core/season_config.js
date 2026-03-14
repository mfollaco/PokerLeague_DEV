export const DEFAULT_SEASON_ID = "spring_2026";

export const SEASONS = {
  [DEFAULT_SEASON_ID]: {
    id: DEFAULT_SEASON_ID,
    name: "Spring Season 2026",
    dataPath: `../data/${DEFAULT_SEASON_ID}.json`
  }
};

export function getSeasonIdFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get("season") || DEFAULT_SEASON_ID;
}

export function resolveSeason(seasonId) {
  return SEASONS[seasonId] || SEASONS[DEFAULT_SEASON_ID];
}
