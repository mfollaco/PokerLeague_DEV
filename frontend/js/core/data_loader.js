import { resolveSeason } from "./season_config.js";

const MEMORY_CACHE = new Map();

const CACHE_VERSION = "v1"; // bump when you change JSON schema or want to flush all caches

function storageKey(seasonId) {
  return `PL_ANALYTICS_SEASON_DATA__${seasonId}__${CACHE_VERSION}`;
}

export async function loadSeasonData(seasonId) {
  const season = resolveSeason(seasonId);

  // Memory cache
  if (MEMORY_CACHE.has(season.id)) {
    return { season, data: MEMORY_CACHE.get(season.id), source: "memory" };
  }

  // sessionStorage cache (safe: validate build_ts via HEAD/ETag/Last-Modified)
  try {
    const cached = sessionStorage.getItem(storageKey(season.id));
    if (cached) {
      const parsed = JSON.parse(cached);

      // If cache has a build_ts, validate the server copy before trusting it.
      // (Python http.server supports Last-Modified; some servers also return ETag.)
      let serverStamp = null;
      try {
        const head = await fetch(season.dataPath, { method: "HEAD", cache: "no-store" });
        if (head.ok) {
          serverStamp =
            head.headers.get("etag") ||
            head.headers.get("last-modified") ||
            null;
        }
      } catch (_) {}

      // Store the server stamp alongside cached JSON (if present)
      const cachedStamp = parsed?.__cacheStamp || null;

      // If we have a server stamp and it differs, ignore cache and refetch below
      if (serverStamp && cachedStamp && serverStamp !== cachedStamp) {
        // fall through to fetch
      } else {
        MEMORY_CACHE.set(season.id, parsed);
        return { season, data: parsed, source: "sessionStorage" };
      }
    }
  } catch (e) {}

  // Fetch
  let resp;
  try {
    resp = await fetch(season.dataPath, { cache: "no-store" });
  } catch (e) {
    throw new Error(
      `Network error fetching ${season.dataPath}. Make sure you run python http.server from /frontend.`
    );
  }

  if (!resp.ok) {
    throw new Error(`Failed to load ${season.dataPath}. HTTP ${resp.status} ${resp.statusText}`);
  }

  let json;
  try {
    json = await resp.json();
  } catch (e) {
    throw new Error(`Invalid JSON at ${season.dataPath}.`);
  }

  if (!json || typeof json !== "object") {
    throw new Error(`Season JSON at ${season.dataPath} did not parse into an object.`);
  }

  // Attach a cache stamp so we can detect stale sessionStorage next load
  let cacheStamp = null;
  try {
    const head = await fetch(season.dataPath, { method: "HEAD", cache: "no-store" });
    if (head.ok) {
      cacheStamp =
        head.headers.get("etag") ||
        head.headers.get("last-modified") ||
        null;
    }
  } catch (_) {}

  if (cacheStamp) {
    json.__cacheStamp = cacheStamp;
  }

  MEMORY_CACHE.set(season.id, json);
  try {
    sessionStorage.setItem(storageKey(season.id), JSON.stringify(json));
  } catch (e) {}

  return { season, data: json, source: "fetch" };
}

export function clearSeasonCache(seasonId) {
  MEMORY_CACHE.delete(seasonId);
  try {
    sessionStorage.removeItem(storageKey(seasonId));
  } catch (e) {}
}
