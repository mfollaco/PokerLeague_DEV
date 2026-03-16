PokerLeague_DEV Roadmap

Last updated: 2026-03-15

This file is the session anchor for PokerLeague_DEV work.

How we use this file

Session rule:
Do architecture cleanup before UI polish or new analytics.

At the start of every session:
1. Open this file first
2. Review current phase and next action
3. Do not start coding until the next action is clear

At the end of every session:
1. Mark what was completed
2. Add notes on what changed
3. Set the exact next starting step
4. Update the date above

---

GitHub Actions maintenance
- Update workflow actions to Node 24-compatible versions before June 2, 2026
- Review checkout, configure-pages, deploy-pages, setup-python, and upload-artifact versions

---

Current Focus

Primary Goal: Re-architect PokerLeague_DEV to support multiple seasons cleanly and prepare for cross-season trend analytics.

Current Phase: Phase 3 IN PROGRESS
Next Phase: Phase 4 - Clean current frontend architecture

Current Next Step: Migrate remaining legacy season-loading pages and utilities to the shared season system, starting with `frontend/js/analytics/luck.js`.

---

Phase 1: Freeze the target before touching more code

Goal: agree on what the system is becoming.

1. Product direction
- One site, not separate season sites
- One page per feature, not duplicated HTML per season
- Season pages support `?season=...`
- Default to the active/current season
- Archived seasons remain viewable
- Future analytics must support both:
  - season-specific views
  - cross-season trend views

2. Analytics model
- Separate Season Analytics from History / Trends Analytics
- Confirm season pages load one season at a time
- Confirm future trend pages should use aggregated cross-season data

---

Phase 2: Audit hardcoded season assumptions

Goal: identify every place the app is secretly hardwired to Spring 2026.

3. Search for hardcoded season IDs and labels
- Search for `spring_2026`
- Search for `Spring Season 2026`
- Search for `Spring 2026`
- Search for hardcoded notes paths
- Search for hardcoded footer season text
- Search for hardcoded season file paths in JS

4. Categorize each result

For every hardcoded result, label it:
- OK for now
- must become season-aware
- should move into season config
- future cross-season blocker

Status:
- COMPLETE

---

Phase 3: Build the season foundation

Goal: create the official season system.

5. Establish `season_config.js` as the single source of truth
- Every season has:
  - id
  - display label
  - short label
  - sort order
  - status (active, complete, upcoming)
  - data file path or derivable file naming
- Define default active season
- Define clean fallback behavior for invalid season params

Status:
- IN PROGRESS
- Canonical season config created
- Compatibility aliases added temporarily for legacy code paths

6. Standardize season resolution everywhere
- All season-aware pages use shared season resolution
- All season-aware pages use shared season data loading
- Remove local season parsing where duplicated
- Remove local season file fetch logic where duplicated

Status:
- IN PROGRESS

Completed this session:
- Created shared `core/season.js` loader layer
- Unified season pathing to root-relative `/data/<season>.json`
- Converted `leaderboard.js` to shared `loadSeason()` pattern
- Converted `weekly_results.js` to shared `loadSeason()` pattern
- Converted `chip_and_chair.js` to shared `loadSeason()` pattern
- Converted analytics hub to use season config + season-aware fetch path
- Added dynamic season selector support in analytics shell
- Added leaderboard page season selector
- Added dynamic leaderboard title based on selected season
- Verified no console errors on:
  - leaderboard
  - weekly results
  - chip and chair
  - analytics hub
- Removed dead `weekly-points.html`
- Removed dead `weekly_points.js`
- Confirmed no remaining references to deleted weekly points page/files

Still remaining in this phase:
- Refactor or retire core/page_bootstrap.js
- Decide whether core/data_loader.js is still needed after remaining migrations
- Make weekly notes paths season-aware instead of using a single shared notes folder
- Move season selector into broader shared site layout if justified

---

Phase 4: Clean the current frontend architecture

Goal: align pages to one sane pattern before new features multiply.

7. Lock the preferred analytics page pattern
- Identify preferred shared analytics initializer
- Write official page pattern rules into this roadmap
- Define standard analytics page structure

8. Classify current pages
- survival_analytics.js = model example
- eliminations.js = acceptable mixed pattern
- nemesis.js = acceptable mixed pattern
- luck.js = off-pattern legacy page
- homepage inline JS = future refactor target

9. Cleanup priorities
- Remove stale references and dead files discovered in audit
- Reduce inline JS in HTML
- Move duplicated helpers into core where justified
- Gradually align mixed pages to the shared pattern
- Leave stable working pages alone unless cleanup provides real value

---

Phase 4.5: UX Cleanup and Configuration Hardening

Goal: remove small architectural shortcuts that will cause confusion later.

9A. Externalize Season Award payouts
- Move Season Awards payouts to config constant

Target:
`SEASON_AWARD_PAYOUTS = [400, 250, 150]`

Then generate awards dynamically from leaderboard truth.

Reason:
- removes payout values from logic
- allows payout changes without modifying logic
- improves maintainability

9B. Fix Weekly Results money badge ambiguity
- Redesign payout badges in Weekly Results

Current UI problem:
`$3` visually looks like three dollars instead of “3rd place and in the money”.

Goal:
Badges should clearly communicate finish position first, payout second.

Candidate formats:
- `3rd • $60`
- `🥉 $60`
- `3rd Place — $60`

Reason:
- prevents misreading
- improves mobile readability
- clearer for league members

9C. Make notes season-aware
- Move week notes to season-based folder structure
- Support notes by season + week
- Remove single shared notes assumption from Weekly Results and homepage

Reason:
- current notes loading is still effectively single-season
- this becomes a blocker as soon as archived seasons are added

---

Phase 5: Make the site multi-season capable

Goal: allow one codebase to cleanly show different seasons.

10. Convert primary pages to season-aware behavior

Priority order:
- homepage
- leaderboard
- weekly results
- chip and chair
- analytics hub
- survival
- eliminations
- nemesis
- luck vs skill

Status:
- Partially complete
- leaderboard, weekly results, chip and chair, and analytics hub are now aligned to the shared season system

11. Make season labels dynamic
- page titles reflect selected season where appropriate
- hero labels reflect selected season
- footer season references are no longer hardcoded
- notes paths become season-aware

Status:
- In progress
- leaderboard title is now dynamic
- more page titles and footer references still need cleanup

12. Make commissioner notes season-aware
- move notes to season-based folder structure
- support notes by season + week
- homepage notes use selected/default season

Status:
- Not started

---

Phase 6: Standardize page templates

Goal: stop building pages freestyle and retrofitting later.

13. Create the official analytics page structure
- hero/header area
- season metadata area
- optional KPI strip
- primary visualization area
- supporting analysis area
- methodology / legend area
- empty/error state area

14. Standardize JS page structure
- shared bootstrap/init
- clear render entry point
- one source of truth for sorted rows/data
- reusable helper naming conventions
- predictable DOM IDs/hooks

15. Standardize reusable CSS patterns
- card structure
- section headers
- KPI cards
- chips/badges
- table wrappers
- legends
- empty states
- page spacing/layout rules

---

Phase 7: Prepare for cross-season analytics

Goal: make trend analysis possible without turning the frontend into spaghetti.

16. Define the future history data layer
- Keep one JSON per season
- Add season registry
- Plan one aggregated cross-season export
- Do not make each page fetch multiple seasons on its own

17. Define the first cross-season datasets
- player season history
- league season summaries
- wins by season
- avg finish by season
- eliminations by season
- survival by season

18. Define history / trend page category
- Player Trends
- Rivalries Over Time
- League History
- Era Leaders
- Progression / Improvement
- Dynasty / legacy metrics

---

Phase 8: Only then add new analytics

Goal: no more cool pages until the runway is paved.

19. Gate for new analytics

Before building any new page, confirm:
- Uses shared page pattern
- Uses shared season resolution
- Supports season-aware labels
- Fits either:
  - Season Analytics
  - History / Trends

20. Candidate future analytics
- Kill Matrix heatmap
- Player trendlines across seasons
- Rivalries over time
- Season-to-season improvement charts
- League parity / dominance trend analytics

---

Session Notes - 2026-03-15

Completed
- Phase 3 season foundation moved from planning into real frontend implementation
- Shared season config and shared season loader established
- Analytics shell now preserves season through links
- Leaderboard, Weekly Results, Chip & A Chair, and Analytics Hub all load successfully with the shared season system
- Weekly Points page was removed after confirming Weekly Results is the correct unified page
- Season dropdown groundwork is now in place
- Confirmed local testing with no console errors on key migrated pages
- Migrated luck.js to the shared season loader system
- Migrated luck.js to the shared season loader
- Refactored homepage to use shared season loader instead of hardcoded spring_2026

Discovered Issues
- Legacy compatibility shims were needed because old files still imported `resolveSeason` and `getSeasonIdFromUrl`
- `analytics_hub.js` contained a mixed old/new loader pattern and required cleanup
- `buildSeasonDataPath()` must remain root-relative (`/data/...`) for pages in nested directories
- week notes are still not season-aware
- remaining legacy season-loading code still exists in `luck.js`, homepage inline JS, and `page_bootstrap.js`

Next starting step
- Decide whether core/page_bootstrap.js and core/data_loader.js should be refactored, compatibility-only, or removed
- Then make weekly notes paths season-aware
- Then evaluate whether the season selector should move into the shared layout
