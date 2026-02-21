PY ?= python3

.PHONY: build init ingest payouts export

build: init ingest payouts export
	@echo "Done: init + ingest + payouts + export"

init:
	$(PY) backend/scripts/init_db.py

ingest:
	$(PY) backend/scripts/ingest_all_csvs.py

payouts:
	$(PY) backend/scripts/build_weekly_payouts.py

export:
	$(PY) backend/scripts/export_season_json.py