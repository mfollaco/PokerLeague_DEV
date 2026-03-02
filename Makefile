PY ?= python3

.PHONY: build init ingest elims points finish points_from_finish payouts totals stats export sync_analytics

build: init ingest elims points finish points_from_finish payouts totals stats export sync_analytics

init:
	$(PY) backend/scripts/init_db.py

ingest:
	$(PY) backend/scripts/ingest_all_csvs.py

# ----------------------------
# Build eliminations table
# ----------------------------
elims:
	$(PY) backend/scripts/build_eliminations.py

points:
	$(PY) backend/scripts/build_weekly_points.py

finish:
	$(PY) backend/scripts/fill_finish_place.py

points_from_finish:
	$(PY) backend/scripts/fill_points_from_finish.py

payouts:
	$(PY) backend/scripts/build_weekly_payouts.py

totals:
	$(PY) backend/scripts/build_season_totals_drop2.py

stats:
	$(PY) backend/scripts/build_player_season_stats.py

export:
	$(PY) backend/scripts/export_season_json.py

# ----------------------------
# Sync JSON to Analytics Lab
# ----------------------------
sync_analytics:
	cp frontend/data/spring_2026.json ../PokerLeague_ANALYTICS_LAB/frontend/data/
	@echo "✅ Synced spring_2026.json to PokerLeague_ANALYTICS_LAB"