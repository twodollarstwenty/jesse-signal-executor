.PHONY: test status init-db

test:
	. .venv/bin/activate && python3 -m pytest tests -q

status:
	bash scripts/status.sh

init-db:
	. .venv/bin/activate && python3 scripts/init_db.py
