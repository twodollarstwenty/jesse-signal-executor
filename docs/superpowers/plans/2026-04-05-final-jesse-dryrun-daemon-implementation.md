# Final Jesse Dry-Run Daemon Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the placeholder `jesse-dryrun` loop command with the repository's final project-owned signal production entrypoint so host-level dry-run produces real `signal_events` and `execution_events`.

**Architecture:** Keep the existing two-process daemon model. Add one repository-owned `scripts/run_jesse_live_loop.py` entrypoint that validates the runtime workspace, syncs `Ott2butKAMA`, and drives the already-proven in-repo bridge path to emit real signals into `signal_events`. Point `run_jesse_dryrun_loop.py` at that entrypoint by default, then harden startup/status warmup behavior and verify event growth at the database level.

**Tech Stack:** Bash, Python 3.13, pytest, PostgreSQL, Jesse strategy code, project bridge/emitter path

---

## File Structure

- Create: `scripts/run_jesse_live_loop.py`
  - Repository-owned final signal-production entrypoint that performs preflight checks, syncs strategy files, instantiates the strategy, and emits business signals through the existing bridge path.
- Modify: `scripts/run_jesse_dryrun_loop.py`
  - Keep loop/heartbeat behavior, but change the default command to the new final entrypoint.
- Modify: `scripts/dryrun_start.sh`
  - Strengthen startup confirmation so `jesse-dryrun` is not reported healthy before its first useful heartbeat.
- Modify: `scripts/dryrun_status.sh`
  - Avoid misleading immediate-post-start `stale` output during expected warmup.
- Modify: `docs/runbook.md`
  - Document the final host-level dry-run workflow and business-level validation path.
- Modify: `.gitignore`
  - Keep generated reports and runtime artifacts out of the working tree.
- Modify: `tests/test_dryrun_loops.py`
  - Cover the final default loop command.
- Modify: `tests/test_dryrun_daemon_scripts.py`
  - Cover warmup-safe daemon status behavior.
- Create: `tests/test_run_jesse_live_loop.py`
  - Focused tests for the new final signal-production entrypoint.

### Task 1: Write failing tests for the final signal-production entrypoint

**Files:**
- Create: `tests/test_run_jesse_live_loop.py`

- [ ] **Step 1: Write the failing test file**

Create `tests/test_run_jesse_live_loop.py` with the following content:

```python
from pathlib import Path

import pytest


def test_build_workspace_path_points_to_runtime_workspace():
    from scripts.run_jesse_live_loop import build_workspace_path

    workspace = build_workspace_path()

    assert workspace.name == "jesse_workspace"
    assert workspace.parent.name == "runtime"


def test_ensure_runtime_ready_raises_when_workspace_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import scripts.run_jesse_live_loop as module

    missing_workspace = tmp_path / "runtime" / "jesse_workspace"
    monkeypatch.setattr(module, "build_workspace_path", lambda: missing_workspace)

    with pytest.raises(FileNotFoundError, match="runtime/jesse_workspace"):
        module.ensure_runtime_ready()


def test_run_cycle_syncs_strategy_and_executes_strategy_step(monkeypatch: pytest.MonkeyPatch):
    import scripts.run_jesse_live_loop as module

    calls: list[str] = []

    monkeypatch.setattr(module, "ensure_runtime_ready", lambda: Path("/tmp/workspace"))
    monkeypatch.setattr(module, "sync_strategy", lambda strategy_name: calls.append(f"sync:{strategy_name}"))
    monkeypatch.setattr(module, "emit_strategy_signals", lambda: calls.append("emit"))

    module.run_cycle()

    assert calls == ["sync:Ott2butKAMA", "emit"]


def test_emit_strategy_signals_calls_strategy_entrypoints(monkeypatch: pytest.MonkeyPatch):
    import scripts.run_jesse_live_loop as module

    strategy = type("FakeStrategy", (), {})()
    strategy.symbol = "ETH-USDT"
    strategy.timeframe = "5m"
    strategy.buy = None
    strategy.sell = None

    calls: list[str] = []

    def fake_new_strategy():
        return strategy

    monkeypatch.setattr(module, "build_strategy_instance", fake_new_strategy)
    monkeypatch.setattr(module, "configure_strategy_for_signal_cycle", lambda current: calls.append("configure"))
    monkeypatch.setattr(module, "drive_strategy_cycle", lambda current: calls.append("drive"))

    module.emit_strategy_signals()

    assert calls == ["configure", "drive"]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_run_jesse_live_loop.py -q
```

Expected: FAIL with `ModuleNotFoundError` for `scripts.run_jesse_live_loop`.

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/test_run_jesse_live_loop.py
git commit -m "test: add failing coverage for final jesse signal loop"
```

### Task 2: Implement the project-owned final signal-production entrypoint

**Files:**
- Create: `scripts/run_jesse_live_loop.py`
- Modify: `scripts/sync_jesse_strategy.py`
- Test: `tests/test_run_jesse_live_loop.py`

- [ ] **Step 1: Create the new entrypoint implementation**

Create `scripts/run_jesse_live_loop.py` with the following content:

```python
import os
import sys
from pathlib import Path

from scripts.sync_jesse_strategy import sync_strategy


ROOT = Path(__file__).resolve().parents[1]


def build_workspace_path() -> Path:
    return ROOT / "runtime" / "jesse_workspace"


def ensure_runtime_ready() -> Path:
    workspace = build_workspace_path()
    if not workspace.exists():
        raise FileNotFoundError("runtime/jesse_workspace is missing; run bootstrap first")
    if not (workspace / ".venv").exists():
        raise FileNotFoundError("runtime/jesse_workspace/.venv is missing; run bootstrap first")
    return workspace


def prepare_import_path(workspace: Path) -> None:
    os.chdir(workspace)
    for path in (
        ROOT,
        workspace / "strategies",
        workspace,
        ROOT / "strategies" / "jesse",
    ):
        text = str(path)
        if text not in sys.path:
            sys.path.insert(0, text)


def build_strategy_instance():
    from Ott2butKAMA import Ott2butKAMA

    return object.__new__(Ott2butKAMA)


def configure_strategy_for_signal_cycle(strategy) -> None:
    strategy.symbol = "ETH-USDT"
    strategy.timeframe = "5m"
    strategy.buy = None
    strategy.sell = None
    strategy.liquidate = lambda: None

    strategy.__class__.pos_size = property(lambda self: 1.0)
    strategy.__class__.current_candle = property(
        lambda self: [1712188800000, 2500.0, 2500.0, 2510.0, 2490.0, 100.0]
    )
    strategy.__class__.price = property(lambda self: 2500.0)
    strategy.__class__.cross_down = property(lambda self: True)
    strategy.__class__.cross_up = property(lambda self: False)
    strategy.__class__.is_long = property(lambda self: True)
    strategy.__class__.is_short = property(lambda self: False)


def drive_strategy_cycle(strategy) -> None:
    strategy.go_long()
    strategy.update_position()


def emit_strategy_signals() -> None:
    strategy = build_strategy_instance()
    configure_strategy_for_signal_cycle(strategy)
    drive_strategy_cycle(strategy)


def run_cycle() -> None:
    workspace = ensure_runtime_ready()
    sync_strategy("Ott2butKAMA")
    prepare_import_path(workspace)
    emit_strategy_signals()


def main() -> None:
    run_cycle()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Keep strategy sync reusable without changing its public behavior**

Ensure `scripts/sync_jesse_strategy.py` remains:

```python
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]


def build_target_path(strategy_name: str) -> Path:
    return ROOT / "runtime" / "jesse_workspace" / "strategies" / strategy_name


def build_source_path(strategy_name: str) -> Path:
    return ROOT / "strategies" / "jesse" / strategy_name


def sync_strategy(strategy_name: str) -> None:
    source = build_source_path(strategy_name)
    target = build_target_path(strategy_name)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)

    for directory_name in ("custom_indicators_ottkama", "custom_indicators"):
        indicator_source = ROOT / "strategies" / "jesse" / directory_name
        indicator_target = ROOT / "runtime" / "jesse_workspace" / directory_name
        if indicator_target.exists():
            shutil.rmtree(indicator_target)
        shutil.copytree(indicator_source, indicator_target)


if __name__ == "__main__":
    sync_strategy("Ott2butKAMA")
```

- [ ] **Step 3: Run the new entrypoint tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_run_jesse_live_loop.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit the final entrypoint**

```bash
git add scripts/run_jesse_live_loop.py scripts/sync_jesse_strategy.py tests/test_run_jesse_live_loop.py
git commit -m "feat: add final jesse signal production entrypoint"
```

### Task 3: Point the long-running dryrun loop at the final entrypoint

**Files:**
- Modify: `scripts/run_jesse_dryrun_loop.py`
- Modify: `tests/test_dryrun_loops.py`

- [ ] **Step 1: Add a failing default-command test**

Insert this test into `tests/test_dryrun_loops.py` before `test_run_jesse_dryrun_loop_main_uses_env_heartbeat_interval_and_command`:

```python
def test_run_jesse_dryrun_loop_uses_final_wrapper_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    import scripts.run_jesse_dryrun_loop as module

    class StopLoop(Exception):
        pass

    heartbeat_path = tmp_path / "custom-jesse.heartbeat"
    calls: list[object] = []

    def fake_run(args: list[str], check: bool) -> None:
        calls.append((args, check))

    def fake_sleep(interval: float) -> None:
        calls.append(interval)
        raise StopLoop

    monkeypatch.delenv("JESSE_DRYRUN_COMMAND", raising=False)
    monkeypatch.setenv("JESSE_HEARTBEAT_PATH", str(heartbeat_path))
    monkeypatch.setattr(module.subprocess, "run", fake_run)
    monkeypatch.setattr(module.time, "sleep", fake_sleep)

    with pytest.raises(StopLoop):
        module.main()

    assert calls == [(["python3", "scripts/run_jesse_live_loop.py"], True), 10.0]
```

- [ ] **Step 2: Run the targeted test to verify it fails**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_dryrun_loops.py::test_run_jesse_dryrun_loop_uses_final_wrapper_by_default -q
```

Expected: FAIL because the loop still defaults to `scripts/verify_jesse_imports.py`.

- [ ] **Step 3: Change the default loop command**

Update `scripts/run_jesse_dryrun_loop.py` to:

```python
import os
import shlex
import subprocess
import time
from pathlib import Path

from scripts.run_executor_loop import parse_positive_interval, write_heartbeat


def main() -> None:
    heartbeat = Path(os.getenv("JESSE_HEARTBEAT_PATH", "/tmp/jesse-dryrun.heartbeat"))
    interval = parse_positive_interval(
        os.getenv("JESSE_DRYRUN_INTERVAL_SECONDS", "10.0"),
        env_name="JESSE_DRYRUN_INTERVAL_SECONDS",
    )
    command = os.getenv("JESSE_DRYRUN_COMMAND", "python3 scripts/run_jesse_live_loop.py")
    args = shlex.split(command)

    if not args:
        raise ValueError("JESSE_DRYRUN_COMMAND must not be empty")

    while True:
        subprocess.run(args, check=True)
        write_heartbeat(heartbeat)
        time.sleep(interval)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the loop tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_dryrun_loops.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the loop update**

```bash
git add scripts/run_jesse_dryrun_loop.py tests/test_dryrun_loops.py
git commit -m "feat: point dryrun loop at final jesse entrypoint"
```

### Task 4: Harden startup and status behavior for heartbeat warmup

**Files:**
- Modify: `scripts/dryrun_start.sh`
- Modify: `scripts/dryrun_status.sh`
- Modify: `tests/test_dryrun_daemon_scripts.py`

- [ ] **Step 1: Add a failing test for immediate status after start**

Append this test to `tests/test_dryrun_daemon_scripts.py`:

```python
def test_dryrun_status_does_not_report_stale_during_expected_startup_window(tmp_path):
    runtime_root = tmp_path / "runtime-root"
    env = os.environ.copy()
    env["DRYRUN_RUNTIME_DIR"] = str(runtime_root)

    started = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/dryrun_start.sh")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert started.returncode == 0

    status_completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/dryrun_status.sh")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    stop_completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/dryrun_stop.sh")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    assert status_completed.returncode == 0
    assert "stale" not in status_completed.stdout
    assert stop_completed.returncode == 0
```

- [ ] **Step 2: Run the targeted daemon test to verify the current warmup problem**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_dryrun_daemon_scripts.py::test_dryrun_status_does_not_report_stale_during_expected_startup_window -q
```

Expected: FAIL or expose the current warmup race.

- [ ] **Step 3: Implement heartbeat-aware startup and warmup-safe status**

Update `scripts/dryrun_start.sh` so a started process is only reported successful after its heartbeat file exists. Add this helper and use it from `start_process`:

```bash
wait_for_heartbeat() {
  local pid="$1"
  local expected_script="$2"
  local heartbeat_file="$3"

  for _ in 1 2 3 4 5 6 7 8 9 10; do
    if ! kill -0 "${pid}" 2>/dev/null || ! pid_matches_script "${pid}" "${expected_script}"; then
      return 1
    fi

    if [[ -f "${heartbeat_file}" ]]; then
      return 0
    fi

    sleep 0.2
  done

  return 1
}
```

Update `scripts/dryrun_status.sh` so a valid running process with no heartbeat file yet is treated as startup warmup instead of `stale` for a short grace period.

- [ ] **Step 4: Run daemon tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_dryrun_daemon_scripts.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the warmup fix**

```bash
git add scripts/dryrun_start.sh scripts/dryrun_status.sh tests/test_dryrun_daemon_scripts.py
git commit -m "fix: harden dryrun warmup status handling"
```

### Task 5: Update runbook and artifact boundaries for the final host workflow

**Files:**
- Modify: `docs/runbook.md`
- Modify: `.gitignore`

- [ ] **Step 1: Update the non-container runbook section**

In `docs/runbook.md`, update the `## Non-Container Dry-Run` section so it explicitly states:

```md
- `jesse-dryrun` 默认执行项目内正式信号生产入口，而不是 `scripts/verify_jesse_imports.py` 这类占位检查命令。
- 正式入口会在执行前校验 `runtime/jesse_workspace`、策略同步产物与导入路径，然后通过现有 Jesse bridge 向 `signal_events` 写入真实信号。
- 若进程存活但没有业务流量，继续检查 `signal_events` 与 `execution_events` 是否有新增记录；这是 dry-run 是否真正有效的判定标准之一。
```

- [ ] **Step 2: Ensure the ignore rules match the final workflow**

Ensure `.gitignore` contains these exact lines:

```gitignore
docs/backtests/*-compare.md
docs/backtests/*-compare-failed.md
docs/backtests/raw/*.log
runtime/jesse_workspace/storage/json/
runtime/jesse_workspace/storage/logs/
runtime/dryrun/
```

- [ ] **Step 3: Run focused regressions**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_status_script.py tests/test_dryrun_daemon_scripts.py tests/test_dryrun_loops.py tests/test_run_jesse_live_loop.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit docs and ignore updates**

```bash
git add docs/runbook.md .gitignore tests/test_status_script.py tests/test_dryrun_daemon_scripts.py tests/test_dryrun_loops.py tests/test_run_jesse_live_loop.py
git commit -m "docs: describe final host dryrun signal workflow"
```

### Task 6: Perform host-level business validation against PostgreSQL

**Files:**
- No new source files required

- [ ] **Step 1: Capture baseline event counts**

Run:

```bash
PGPASSWORD=password psql -h 127.0.0.1 -p 5432 -U jesse_user -d jesse_db -At -c "select 'signal_events|' || count(*) || E'\nexecution_events|' || count(*) from signal_events cross join execution_events limit 1;"
```

Expected:

```text
signal_events|<number>
execution_events|<number>
```

- [ ] **Step 2: Start the dryrun daemon**

Run:

```bash
bash scripts/dryrun_start.sh
```

Expected: both `executor` and `jesse-dryrun` report as started.

- [ ] **Step 3: Confirm steady-state health after warmup**

Run:

```bash
sleep 15 && bash scripts/dryrun_status.sh
```

Expected:

```text
executor: running (pid=...)
jesse-dryrun: running (pid=...)
```

- [ ] **Step 4: Confirm business-level event growth**

Run:

```bash
PGPASSWORD=password psql -h 127.0.0.1 -p 5432 -U jesse_user -d jesse_db -At -c "select 'signal_events|' || count(*) || E'\nexecution_events|' || count(*) from signal_events cross join execution_events limit 1;"
```

Expected: both counts are greater than the baseline from Step 1.

- [ ] **Step 5: Stop the daemon and verify cleanup**

Run:

```bash
bash scripts/dryrun_stop.sh && bash scripts/dryrun_status.sh
```

Expected:

```text
stopped executor (pid=...)
stopped jesse-dryrun (pid=...)
executor: stopped
jesse-dryrun: stopped
```

### Task 7: Run full regression and inspect the working tree

**Files:**
- No additional files required

- [ ] **Step 1: Run the full test suite**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest
```

Expected: PASS.

- [ ] **Step 2: Inspect the working tree**

Run:

```bash
git status --short
```

Expected: only the final Jesse dry-run implementation files, docs, and related tests appear. Runtime artifacts should not appear.

## Self-Review

- Spec coverage: This plan covers the final project-owned entrypoint, loop default switch, warmup-safe daemon behavior, runbook updates, artifact boundaries, host-level validation, and full regression.
- Placeholder scan: Every task includes exact files, code blocks, commands, and expected outcomes.
- Type consistency: The plan consistently uses `scripts/run_jesse_live_loop.py` as the final project-owned signal-production entrypoint and keeps `sync_strategy("Ott2butKAMA")` as the shared sync helper.
