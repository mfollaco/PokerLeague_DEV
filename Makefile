PY ?= python3

.PHONY: build payouts export

build: payouts export
	@echo "Done: payouts rebuilt + season JSON exported"

payouts:
	$(PY) backend/scripts/build_weekly_payouts.py

export:
	$(PY) backend/scripts/export_season_json.py
