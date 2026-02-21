PY ?= python3

.PHONY: build init ingest points payouts export

build: init ingest points payouts export
	@echo "Done: init + ingest + points + payouts + export"

init:
	$(PY) backend/scripts/init_db.py

ingest:
	$(PY) backend/scripts/ingest_all_csvs.py

points:
	$(PY) backend/scripts/build_weekly_points.py

payouts:
	$(PY) backend/scripts/build_weekly_payouts.py

export:
	$(PY) backend/scripts/export_season_json.py