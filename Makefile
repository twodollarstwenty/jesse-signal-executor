.PHONY: test status init-db dryrun-up dryrun-down dryrun-watch

test:
	. .venv/bin/activate && python3 -m pytest tests -q

status:
	bash scripts/status.sh

init-db:
	. .venv/bin/activate && python3 scripts/init_db.py

dryrun-up:
	set -a && . .env && set +a && bash scripts/dryrun_start.sh
	set -a && . .env && set +a && bash scripts/dryrun_status.sh
	set -a && . .env && set +a && . .venv/bin/activate && python3 scripts/summarize_dryrun_validation.py --minutes 60

dryrun-down:
	set -a && . .env && set +a && bash scripts/dryrun_stop.sh
	set -a && . .env && set +a && bash scripts/dryrun_status.sh

dryrun-watch:
	while true; do \
		clear; \
		bash scripts/dryrun_status.sh; \
		echo; \
		set -a && . .env && set +a && . .venv/bin/activate && python3 scripts/summarize_dryrun_validation.py --minutes 20; \
		sleep 10; \
	done
