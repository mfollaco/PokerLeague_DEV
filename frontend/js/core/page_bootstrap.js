import { byId, setHtml, show, hide, renderAlert } from "./dom_utils.js";
import { getSeasonIdFromUrl, resolveSeason } from "./season_config.js";
import { loadSeasonData } from "./data_loader.js";

export async function initAnalyticsPage({ render } = {}) {
  if (typeof render !== "function") {
    throw new Error("initAnalyticsPage requires a { render: (data, season) => ... } function.");
  }

  const seasonId = getSeasonIdFromUrl();
  const season = resolveSeason(seasonId);

  const loadingEl = byId("loading-row");
  const contentEl = byId("content-row");
  const statusEl = byId("data-status");

  // ✅ Null-safe show/hide (some pages won’t use these)
  if (loadingEl) show(loadingEl);
  if (contentEl) hide(contentEl);

  try {
    const { data } = await loadSeasonData(season.id);

    // Let the page-specific renderer handle content
    await render(data, season);

    if (statusEl) setHtml(statusEl, "");
  } catch (err) {
    if (statusEl) {
      setHtml(statusEl, renderAlert({
        type: "danger",
        title: "Failed to load analytics",
        message: err?.message || String(err)
      }));
    }
    // Optional: also log for debugging
    console.error(err);
  } finally {
    if (loadingEl) hide(loadingEl);
    if (contentEl) show(contentEl);
  }
}