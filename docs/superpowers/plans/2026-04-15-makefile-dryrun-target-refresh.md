# Makefile Dryrun Target Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refresh the stale dry-run `Makefile` targets so reset and log operations match the current supervisor and per-instance runtime layout.

**Architecture:** Keep the change tightly scoped to `Makefile` behavior. Reuse the existing `scripts/dryrun_stop.sh` and `scripts/dryrun_status.sh` entrypoints, but update cleanup and log paths to the current `runtime/dryrun/supervisor/` and `runtime/dryrun/instances/` layout. Add small verification coverage so the refreshed targets are protected against regressions.

**Tech Stack:** GNU Make, shell commands, pytest, existing dry-run supervisor scripts

---

### Task 1: Add Failing Coverage For Refreshed Makefile Targets

**Files:**
- Modify: `tests/test_dryrun_daemon_scripts.py`
- Test: `tests/test_dryrun_daemon_scripts.py`

- [ ] **Step 1: Write the failing tests**

Add tests that lock in the new target behavior.

```python
def test_makefile_mentions_instance_worker_logs():
    from pathlib import Path

    makefile = Path("Makefile").read_text()

    assert "runtime/dryrun/instances/*/logs/worker.log" in makefile


def test_makefile_mentions_supervisor_pid_cleanup():
    from pathlib import Path

    makefile = Path("Makefile").read_text()

    assert "runtime/dryrun/supervisor/pids" in makefile
    assert "run_executor_loop.py" not in makefile
    assert "run_jesse_dryrun_loop.py" not in makefile
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/bin/python -m pytest tests/test_dryrun_daemon_scripts.py -q`
Expected: FAIL because `Makefile` still references the legacy dry-run log path and old process names.

- [ ] **Step 3: Write minimal implementation in `Makefile`**

Update only the stale dry-run targets.

```make
dryrun-log:
	tail -f runtime/dryrun/instances/*/logs/worker.log

dryrun-reset:
	@set -a && . .env && set +a && bash scripts/dryrun_stop.sh || true
	@rm -f runtime/dryrun/supervisor/pids/*.pid
	@rm -f runtime/dryrun/instances/*/logs/*.log
	@rm -f runtime/dryrun/instances/*/heartbeats/*
	@rm -f runtime/dryrun/instances/*/state/*
	@set -a && . .env && set +a && . .venv/bin/activate && python3 -c "import os, psycopg2; conn = psycopg2.connect(host=os.getenv('POSTGRES_HOST','127.0.0.1'), port=int(os.getenv('POSTGRES_PORT','5432')), dbname=os.getenv('POSTGRES_DB','jesse_db'), user=os.getenv('POSTGRES_USER','jesse_user'), password=os.getenv('POSTGRES_PASSWORD','password')); cur = conn.cursor(); cur.execute('DELETE FROM execution_events'); cur.execute('DELETE FROM signal_events'); cur.execute('DELETE FROM position_state'); conn.commit(); cur.close(); conn.close(); print('已清空 signal_events / execution_events / position_state')"
	@echo "已清空 dry-run 日志和状态文件"
	@bash scripts/dryrun_status.sh
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `./.venv/bin/python -m pytest tests/test_dryrun_daemon_scripts.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add Makefile tests/test_dryrun_daemon_scripts.py
git commit -m "fix: refresh makefile dryrun targets"
```

### Task 2: Verify Operator Commands End-To-End

**Files:**
- Modify: `Makefile`
- Test: runtime verification via `make`

- [ ] **Step 1: Run the refreshed reset target**

Run: `make dryrun-reset`
Expected: exits successfully, clears runtime state, clears database tables, prints current dry-run status.

- [ ] **Step 2: Run the existing lifecycle targets after reset**

Run: `make dryrun-up && make dryrun-down`
Expected: `dryrun-up` reports supervisor running with instance counts, and `dryrun-down` reports supervisor stopped.

- [ ] **Step 3: Check the log target path**

Run: `grep -n "dryrun-log\|worker.log\|supervisor/pids" Makefile`
Expected: output shows the refreshed `dryrun-log` worker path and the refreshed `dryrun-reset` cleanup path.

- [ ] **Step 4: Run the full regression suite**

Run: `./.venv/bin/python -m pytest -q`
Expected: PASS

- [ ] **Step 5: Commit verification-safe final state if Task 1 was not committed yet**

```bash
git status --short
```

Expected: no unexpected modified files remain beyond the intended refresh changes and any already-known uncommitted work.
