PokerLeague_DEV Roadmap

Last updated: 2026-03-13

This file is the session anchor for PokerLeague_DEV work.

How we use this file

Session rule:
Do architecture cleanup before UI polish or new analytics.

At the start of every session:
	1.	Open this file first
	2.	Review current phase and next action
	3.	Do not start coding until the next action is clear

At the end of every session:
	1.	Mark what was completed
	2.	Add notes on what changed
	3.	Set the exact next starting step
	4.	Update the date above


GitHub Actions maintenance
- Update workflow actions to Node 24-compatible versions before June 2, 2026
- Review checkout, configure-pages, deploy-pages, setup-python, and upload-artifact versions

⸻

Current Focus

Primary Goal: Re-architect PokerLeague_DEV to support multiple seasons cleanly and prepare for cross-season trend analytics.

Current Phase: Phase 3 – Multi-season architecture preparation

Current Next Step: Add seasons table and begin multi-season data model

⸻

Phase 1: Freeze the target before touching more code

Goal: agree on what the system is becoming.

1. Product direction
	•	One site, not separate season sites
	•	One page per feature, not duplicated HTML per season
	•	Season pages support ?season=...
	•	Default to the active/current season
	•	Archived seasons remain viewable
	•	Future analytics must support both:
	•	season-specific views
	•	cross-season trend views

2. Analytics model
	•	Separate Season Analytics from History / Trends Analytics
	•	Confirm season pages load one season at a time
	•	Confirm future trend pages should use aggregated cross-season data

⸻

Phase 2: Audit hardcoded season assumptions

Goal: identify every place the app is secretly hardwired to Spring 2026.

3. Search for hardcoded season IDs and labels
	•	Search for spring_2026
	•	Search for Spring Season 2026
	•	Search for Spring 2026
	•	Search for hardcoded notes paths
	•	Search for hardcoded footer season text
	•	Search for hardcoded season file paths in JS

4. Categorize each result

For every hardcoded result, label it:
	•	OK for now
	•	must become season-aware
	•	should move into season config
	•	future cross-season blocker

⸻

Phase 3: Build the season foundation

Goal: create the official season system.

5. Establish season_config.js as the single source of truth
	•	Every season has:
	•	id
	•	display label
	•	short label
	•	sort order
	•	status (active, complete, upcoming)
	•	data file path or derivable file naming
	•	Define default active season
	•	Define clean fallback behavior for invalid season params

6. Standardize season resolution everywhere
	•	All season-aware pages use shared season resolution
	•	All season-aware pages use shared season data loading
	•	Remove local season parsing where duplicated
	•	Remove local season file fetch logic where duplicated

⸻

Phase 4: Clean the current frontend architecture

Goal: align pages to one sane pattern before new features multiply.

7. Lock the preferred analytics page pattern
	•	Identify initAnalyticsPage() as preferred shared page initializer
	•	Identify survival_analytics.js as strongest current example
	•	Write official page pattern rules into this roadmap
	•	Define standard analytics page structure

8. Classify current pages
	•	survival_analytics.js = model example
	•	eliminations.js = acceptable mixed pattern
	•	nemesis.js = acceptable mixed pattern
	•	luck.js = off-pattern legacy page
	•	homepage inline JS = future refactor target

9. Cleanup priorities
	•	Remove stale references and dead files discovered in audit
	•	Reduce inline JS in HTML
	•	Move duplicated helpers into core where justified
	•	Gradually align mixed pages to the shared pattern
	•	Leave stable working pages alone unless cleanup provides real value

⸻

Phase 4.5: UX Cleanup and Configuration Hardening

Goal: remove small architectural shortcuts that will cause confusion later.

9A. Externalize Season Award payouts
	•	Move Season Awards payouts to config constant

Target:

SEASON_AWARD_PAYOUTS = [400, 250, 150]

Then generate awards dynamically from leaderboard truth.

Reason:
	•	removes payout values from logic
	•	allows payout changes without modifying logic
	•	improves maintainability

9B. Fix Weekly Results money badge ambiguity
	•	Redesign payout badges in Weekly Results

Current UI problem:
“$3” visually looks like three dollars instead of “3rd place and in the money”.

Goal:
Badges should clearly communicate finish position first, payout second.

Candidate formats:

3rd • $60
🥉 $60
3rd Place — $60

Reason:
	•	prevents misreading
	•	improves mobile readability
	•	clearer for league members

⸻

Phase 5: Make the site multi-season capable

Goal: allow one codebase to cleanly show different seasons.

10. Convert primary pages to season-aware behavior

Priority order:
	•	homepage
	•	leaderboard
	•	weekly points
	•	weekly results
	•	chip and chair
	•	analytics hub
	•	survival
	•	eliminations
	•	nemesis
	•	luck vs skill

11. Make season labels dynamic
	•	page titles reflect selected season where appropriate
	•	hero labels reflect selected season
	•	footer season references are no longer hardcoded
	•	notes paths become season-aware

12. Make commissioner notes season-aware
	•	move notes to season-based folder structure
	•	support notes by season + week
	•	homepage notes use selected/default season

⸻

Phase 6: Standardize page templates

Goal: stop building pages freestyle and retrofitting later.

13. Create the official analytics page structure
	•	hero/header area
	•	season metadata area
	•	optional KPI strip
	•	primary visualization area
	•	supporting analysis area
	•	methodology / legend area
	•	empty/error state area

14. Standardize JS page structure
	•	shared bootstrap/init
	•	clear render entry point
	•	one source of truth for sorted rows/data
	•	reusable helper naming conventions
	•	predictable DOM IDs/hooks

15. Standardize reusable CSS patterns
	•	card structure
	•	section headers
	•	KPI cards
	•	chips/badges
	•	table wrappers
	•	legends
	•	empty states
	•	page spacing/layout rules

⸻

Phase 7: Prepare for cross-season analytics

Goal: make trend analysis possible without turning the frontend into spaghetti.

16. Define the future history data layer
	•	Keep one JSON per season
	•	Add season registry
	•	Plan one aggregated cross-season export
	•	Do not make each page fetch multiple seasons on its own

17. Define the first cross-season datasets
	•	player season history
	•	league season summaries
	•	wins by season
	•	avg finish by season
	•	eliminations by season
	•	survival by season

18. Define history / trend page category
	•	Player Trends
	•	Rivalries Over Time
	•	League History
	•	Era Leaders
	•	Progression / Improvement
	•	Dynasty / legacy metrics

⸻

Phase 8: Only then add new analytics

Goal: no more cool pages until the runway is paved.

19. Gate for new analytics

Before building any new page, confirm:
	•	Uses shared page pattern
	•	Uses shared season resolution
	•	Supports season-aware labels
	•	Fits either:
	•	Season Analytics
	•	History / Trends

20. Candidate future analytics
	•	Kill Matrix heatmap
	•	Player trendlines across seasons
	•	Rivalries over time
	•	Season-to-season improvement charts
	•	League parity / dominance trend analytics

⸻

Audit Findings Already Confirmed
	•	schedule.html had a stale reference to nonexistent js/schedule.js and it was removed
	•	index.html contains meaningful inline JavaScript and is a future refactor target
	•	page_bootstrap.js is the correct shared analytics foundation
	•	survival_analytics.js is the best current page example
	•	luck.js is functional but off-pattern
	•	eliminations.js and nemesis.js are healthy but mixed-pattern

⸻

Rabbit-Hole Rules
	•	Do not build a new analytic until the season foundation is defined
	•	Do not polish random CSS before season hardcoding is audited
	•	Do not refactor stable pages just because the code is ugly
	•	Do not build cross-season charts until the data model is planned
	•	Do not invent page structure per page anymore
	•	Do not let one-off hacks bypass season_config.js and shared loaders

⸻

Session Log

2026-03-12

Completed
	•	Fixed incorrect weekly scoring rule (winner always 8 points)
	•	Rebuilt season totals and drop-bottom-2 logic
	•	Corrected Season Awards ordering
	•	Refactored export_season_json.py so awards derive from leaderboard truth
	•	Verified correct site rebuild and deployment

Discovered Issues
	•	Season Award payouts currently hardcoded in export logic
	•	Weekly Results payout badge can be misread (”$3”)

Cleanup Tasks Added
	•	Externalize season award payouts into configuration constant
	•	Redesign Weekly Results payout badges for clarity

Next starting step

Search the codebase for every hardcoded spring_2026 reference and classify results.

Notes

Do not start cleanup refactors until the hardcoded season audit is complete.
:::

FILE: frontend/js/core/season_config.js
LINE: 7
MATCH: dataPath: "../data/spring_2026.json"
CLASSIFICATION: should move into season config
WHY: This is a central config file. It should define season-aware paths dynamically, not pin to one season file.

FILE: frontend/js/weekly_results.js
LINE: 9
MATCH: fetch("data/spring_2026.json")
CLASSIFICATION: must become season-aware
WHY: Weekly results should load the selected/current season, not a fixed season.

FILE: frontend/js/leaderboard.js
LINE: 316
MATCH: const response = await fetch("data/spring_2026.json");
CLASSIFICATION: must become season-aware
WHY: Leaderboard is core season-driven UI and must support switching seasons cleanly.

FILE: frontend/js/chip_and_chair.js
LINE: 170
MATCH: const res = await fetch("data/spring_2026.json");
CLASSIFICATION: must become season-aware
WHY: This page is season analytics and should not be tied to a single season file.

FILE: frontend/js/weekly_points.js
LINE: 4
MATCH: fetch("data/spring_2026.json")
CLASSIFICATION: must become season-aware
WHY: Weekly points is season-scoped data and should resolve dynamically.

FILE: frontend/index.html
LINE: 198
MATCH: const url = `data/${SEASON_ID}.json`;
CLASSIFICATION: OK for now
WHY: Dynamic season-aware path already in place.

FILE: frontend/js/analytics/luck.js
LINE: 77
MATCH: const response = await fetch(`../data/${seasonId}.json`);
CLASSIFICATION: OK for now
WHY: Already dynamically loads season data.

PHASE 2 AUDIT SUMMARY

Frontend issues:
- index.html hardcodes current season
- weekly_results.js hardcodes season JSON
- leaderboard.js hardcodes season JSON
- chip_and_chair.js hardcodes season JSON
- weekly_points.js hardcodes season JSON
- analytics/luck.js uses page-local default fallback

Backend issues:
- multiple scripts hardcode SEASON_ID = "spring_2026"
- export_season_json.py hardcodes both season ID and output file
- build_all.py hardcodes output filename and season_id payload
- Makefile sync hardcodes spring_2026.json

Conclusion:
- Frontend is partially season-aware
- Backend build pipeline is still single-season
- Need a single source of truth for active/default season before refactoring scripts

2026-03-13

Completed
• Continued hardcoded season audit across frontend
• Fixed Season Awards sorting logic (now based on payout amount)
• Added medal indicators to Season Awards UI (🥇🥈🥉)
• Verified leaderboard + awards consistency
• Confirmed season loader and sessionStorage caching working correctly

Discovered Issues
• Several frontend pages still fetch spring_2026.json directly
• Backend build scripts still assume a single active season

Cleanup Tasks Added
• Replace remaining hardcoded season fetch calls with shared season loader
• Move season award payouts to configuration constant
• Implement season switcher UI in navbar (future)

Next starting step

Finish replacing remaining hardcoded JSON fetches with shared loader:
- chip_and_chair.js
- weekly_points.js

2026-03-13
- Removed remaining hardcoded spring_2026 references
- Backend scripts now use SEASON_ID environment variable
- build_all.py output path now dynamic
- Makefile sync_analytics now copies using season variable
