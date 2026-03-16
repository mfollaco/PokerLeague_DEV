export const DEFAULT_SEASON_ID = "spring_2026";

export const SEASONS = {
  spring_2026: {
    id: "spring_2026",
    displayLabel: "Spring Season 2026",
    shortLabel: "Spring 2026",
    sortOrder: 202601,
    status: "active"
  }
};

export function getAllSeasons() {
  return Object.values(SEASONS).sort((a, b) => a.sortOrder - b.sortOrder);
}

export function getSeasonById(seasonId) {
  return SEASONS[seasonId] || null;
}

export function getDefaultSeasonId() {
  return DEFAULT_SEASON_ID;
}

export function buildSeasonDataPath(seasonId) {
  return `/data/${seasonId}.json`;
}

export function resolveSeasonIdFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const requestedSeasonId = params.get("season");

  if (requestedSeasonId && SEASONS[requestedSeasonId]) {
    return requestedSeasonId;
  }

  return DEFAULT_SEASON_ID;
}

export function resolveSeasonConfig(seasonId = null) {
  const resolvedSeasonId = seasonId || resolveSeasonIdFromUrl();
  const season = getSeasonById(resolvedSeasonId);

  if (season) {
    return {
      ...season,
      dataPath: buildSeasonDataPath(season.id)
    };
  }

  const fallbackSeason = getSeasonById(DEFAULT_SEASON_ID);

  return {
    ...fallbackSeason,
    dataPath: buildSeasonDataPath(fallbackSeason.id)
  };
}

export function resolveSeason(seasonId = null) {
  return resolveSeasonConfig(seasonId);
}

export function getSeasonIdFromUrl() {
  return resolveSeasonIdFromUrl();
}