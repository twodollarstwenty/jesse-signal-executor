.PHONY: test status init-db dryrun-up dryrun-down dryrun-watch dryrun-debug dryrun-log dryrun-panel dryrun-history

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

dryrun-debug:
	@bash scripts/dryrun_status.sh
	@echo
	@set -a && . .env && set +a && . .venv/bin/activate && python3 scripts/summarize_dryrun_validation.py --minutes 10
	@echo
	@set -a && . .env && set +a && . .venv/bin/activate && python3 -c "import os, psycopg2; conn = psycopg2.connect(host=os.getenv('POSTGRES_HOST', '127.0.0.1'), port=int(os.getenv('POSTGRES_PORT', '5432')), dbname=os.getenv('POSTGRES_DB', 'jesse_db'), user=os.getenv('POSTGRES_USER', 'jesse_user'), password=os.getenv('POSTGRES_PASSWORD', 'password')); cur = conn.cursor(); cur.execute('select signal_time, action, status from signal_events order by id desc limit 10'); print('signal_events:'); [print(row) for row in cur.fetchall()]; print(); cur.execute('select created_at, status, signal_id from execution_events order by id desc limit 10'); print('execution_events:'); [print(row) for row in cur.fetchall()]; cur.close(); conn.close()"

dryrun-log:
	tail -f runtime/dryrun/logs/jesse-dryrun.log

dryrun-panel:
	@set -a && . .env && set +a && . .venv/bin/activate && python3 scripts/build_current_position_panel.py

dryrun-history:
	@set -a && . .env && set +a && . .venv/bin/activate && python3 scripts/build_trade_history_panel.py
