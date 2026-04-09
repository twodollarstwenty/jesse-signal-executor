# Host Dry-Run Supervisor Consistency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make host dry-run `start / status / stop` consistent with real process state rather than relying on pid files alone.

**Architecture:** Add a shared process-discovery strategy based on script path plus runtime-specific heartbeat path, and use that logic consistently in `dryrun_start.sh`, `dryrun_status.sh`, and `dryrun_stop.sh`. Preserve the current user-facing commands while eliminating duplicate-instance and stale-pid drift.

**Tech Stack:** shell, pytest, existing dryrun daemon tests

---

## File Structure

- Modify: `scripts/dryrun_start.sh`
  - Improve orphan detection and startup timeout handling.
- Modify: `scripts/dryrun_status.sh`
  - Discover real matching processes even when pid files are missing.
- Modify: `scripts/dryrun_stop.sh`
  - Stop matching processes even when pid files are missing.
- Modify: `tests/test_dryrun_daemon_scripts.py`
  - Lock the improved behavior.

### Task 1: Add failing tests for pid-file-independent process discovery

**Files:**
- Modify: `tests/test_dryrun_daemon_scripts.py`

- [ ] **Step 1: Add a failing status test for missing pid file but live process**

Append this test to `tests/test_dryrun_daemon_scripts.py`:

```python
def test_dryrun_status_detects_live_jesse_process_even_without_pid_file(tmp_path):
    runtime_root = tmp_path / "runtime-root"
    env = os.environ.copy()
    env["DRYRUN_RUNTIME_DIR"] = str(runtime_root)
    heartbeat_path = runtime_root / "heartbeats" / "jesse-dryrun.heartbeat"
    env["JESSE_DRYRUN_COMMAND"] = f'python3 "{LONG_RUNNING_JESSE_TEST_SCRIPT}" "{heartbeat_path}"'

    started = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/dryrun_start.sh")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert started.returncode == 0

    (runtime_root / "pids" / "jesse-dryrun.pid").unlink()

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

    assert "jesse-dryrun: running" in status_completed.stdout
    assert stop_completed.returncode == 0
```

- [ ] **Step 2: Add a failing stop test for missing pid file but live process**

Append this test to `tests/test_dryrun_daemon_scripts.py`:

```python
def test_dryrun_stop_terminates_live_jesse_process_even_without_pid_file(tmp_path):
    runtime_root = tmp_path / "runtime-root"
    env = os.environ.copy()
    env["DRYRUN_RUNTIME_DIR"] = str(runtime_root)
    heartbeat_path = runtime_root / "heartbeats" / "jesse-dryrun.heartbeat"
    env["JESSE_DRYRUN_COMMAND"] = f'python3 "{LONG_RUNNING_JESSE_TEST_SCRIPT}" "{heartbeat_path}"'

    started = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/dryrun_start.sh")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert started.returncode == 0

    (runtime_root / "pids" / "jesse-dryrun.pid").unlink()

    stop_completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/dryrun_stop.sh")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    status_completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/dryrun_status.sh")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    assert stop_completed.returncode == 0
    assert "jesse-dryrun: stopped" in status_completed.stdout
```

- [ ] **Step 3: Run the targeted tests to verify they fail**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_dryrun_daemon_scripts.py -q
```

Expected: FAIL because status/stop still rely too heavily on pid files.

### Task 2: Implement shared process discovery across start/status/stop

**Files:**
- Modify: `scripts/dryrun_start.sh`
- Modify: `scripts/dryrun_status.sh`
- Modify: `scripts/dryrun_stop.sh`
- Test: `tests/test_dryrun_daemon_scripts.py`

- [ ] **Step 1: Introduce a shared matching rule**

Use a consistent process-discovery rule based on:

- matching script path
- matching heartbeat file path in the command environment/command line

This should become the fallback even when pid files are missing.

- [ ] **Step 2: Update `dryrun_status.sh`**

If pid file is missing, search for a matching live process for the runtime instance before concluding `stopped`.

- [ ] **Step 3: Update `dryrun_stop.sh`**

If pid file is missing, search for and terminate matching live processes before concluding `already stopped`.

- [ ] **Step 4: Keep `dryrun_start.sh` single-instance safe**

If a matching process already exists for the runtime instance, do not launch a second one.

- [ ] **Step 5: Run targeted tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_dryrun_daemon_scripts.py -q
```

Expected: PASS.

### Task 3: Practical validation

**Files:**
- No new files required

- [ ] **Step 1: Fresh restart**

Run:

```bash
make dryrun-reset-up
```

- [ ] **Step 2: Verify stable status reporting**

Run:

```bash
bash scripts/dryrun_status.sh
```

Expected: if matching processes are alive, status should report `running`, even if pid files had previously drifted.

- [ ] **Step 3: Run full tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest
```

Expected: PASS.

## Self-Review

- Spec coverage: The plan aligns start, status, and stop on real-process truth rather than pid-file-only assumptions.
- Placeholder scan: Tasks include exact files, behaviors, and commands.
- Type consistency: The same matching logic is reused across all three scripts.
