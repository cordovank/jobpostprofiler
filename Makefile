.PHONY: run cli test status search show apply followup export rescore

# ── App ──────────────────────────────────────────────────────────────
run:
	uv run streamlit run src/jobpostprofiler/ui/app.py

cli:
	uv run -m jobpostprofiler.main

test:
	uv run python -m pytest -v

# ── Tracker ──────────────────────────────────────────────────────────
status:
	uv run python tracker_cli.py status

search:
	uv run python tracker_cli.py search "$(q)"

show:
	uv run python tracker_cli.py show $(id)

show-full:
	uv run python tracker_cli.py show $(id) --full

apply:
	uv run python tracker_cli.py apply $(id) --resume $(resume)

followup:
	uv run python tracker_cli.py followup

export:
	uv run python tracker_cli.py export

export-job:
	uv run python tracker_cli.py export-job $(id)

rescore:
	uv run python tracker_cli.py rescore