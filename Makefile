PY ?= python3

.PHONY: build init ingest points finish points_from_finish payouts totals stats export

build: init ingest points finish points_from_finish payouts totals stats export
	@echo "Done: init + ingest + points + finish + points_from_finish + payouts + totals + stats + export"

init:
	$(PY) backend/scripts/init_db.py

ingest:
	$(PY) backend/scripts/ingest_all_csvs.py

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