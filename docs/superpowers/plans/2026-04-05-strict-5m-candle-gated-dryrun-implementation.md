# Strict 5m Candle-Gated Dry-Run Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make dry-run action evaluation happen only when a new 5-minute candle is available, so the dry-run cadence is materially closer to the strategy's 5m backtest regime.

**Architecture:** Keep the current Binance Futures kline polling approach, but add a small remembered last-processed-candle timestamp. If the latest candle timestamp has not changed, the loop should skip action evaluation, emit nothing, and print a simple waiting status line. If the candle timestamp is new, the loop should evaluate exactly once and remember it.

**Tech Stack:** Python 3.13, pytest, Binance Futures kline snapshot helper

---

## File Structure

- Modify: `scripts/run_jesse_live_loop.py`
  - Add 5m candle gating state and waiting-status output.
- Modify: `tests/test_run_jesse_live_loop.py`
  - Add tests for same-candle suppression and new-candle evaluation.

### Task 1: Add failing tests for 5m candle gating

**Files:**
- Modify: `tests/test_run_jesse_live_loop.py`

- [ ] **Step 1: Add a failing same-candle suppression test**

Append this test to `tests/test_run_jesse_live_loop.py`:

```python
def test_run_cycle_skips_action_when_latest_candle_is_already_processed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys):
    import scripts.run_jesse_live_loop as module

    workspace = tmp_path / "runtime" / "jesse_workspace"
    workspace.mkdir(parents=True)

    snapshot = {
        "symbol": "ETHUSDT",
        "close_prices": [2505.0, 2516.8, 2524.1],
        "latest_timestamp": 1712189100000,
        "timestamp": "2026-04-05T21:33:20+08:00",
    }

    monkeypatch.setattr(module, "ensure_runtime_ready", lambda: workspace)
    monkeypatch.setattr(module, "prepare_import_path", lambda current: None)
    monkeypatch.setattr(module, "fetch_recent_klines", lambda symbol, interval="5m", limit=50: snapshot)
    monkeypatch.setattr(module, "emit_strategy_signals", lambda loop_state=None: (_ for _ in ()).throw(AssertionError("should not emit for the same candle twice")))
    module.LAST_PROCESSED_CANDLE_TS = 1712189100000

    module.run_cycle()

    output = capsys.readouterr().out.strip()
    assert "等待新 5m K 线" in output
```

- [ ] **Step 2: Add a failing new-candle evaluation test**

Append this test to `tests/test_run_jesse_live_loop.py`:

```python
def test_run_cycle_evaluates_once_when_new_candle_arrives(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import scripts.run_jesse_live_loop as module

    workspace = tmp_path / "runtime" / "jesse_workspace"
    workspace.mkdir(parents=True)

    snapshot = {
        "symbol": "ETHUSDT",
        "close_prices": [2505.0, 2516.8, 2524.1],
        "latest_timestamp": 1712189100000,
        "timestamp": "2026-04-05T21:33:20+08:00",
    }

    calls = []
    monkeypatch.setattr(module, "ensure_runtime_ready", lambda: workspace)
    monkeypatch.setattr(module, "prepare_import_path", lambda current: None)
    monkeypatch.setattr(module, "fetch_recent_klines", lambda symbol, interval="5m", limit=50: snapshot)
    monkeypatch.setattr(module, "emit_strategy_signals", lambda loop_state=None: calls.append(loop_state) or {**loop_state, "emitted": True})
    module.LAST_PROCESSED_CANDLE_TS = 1712188800000

    module.run_cycle()

    assert len(calls) == 1
    assert module.LAST_PROCESSED_CANDLE_TS == 1712189100000
```

- [ ] **Step 3: Run the targeted tests to verify they fail**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_run_jesse_live_loop.py -q
```

Expected: FAIL because same-candle iterations are not suppressed yet.

### Task 2: Implement 5m candle gating

**Files:**
- Modify: `scripts/run_jesse_live_loop.py`
- Test: `tests/test_run_jesse_live_loop.py`

- [ ] **Step 1: Add a processed-candle memory field**

Add a module-level variable:

```python
LAST_PROCESSED_CANDLE_TS: int | None = None
```

- [ ] **Step 2: Gate action evaluation in `run_cycle()`**

After fetching the latest kline snapshot, compare `snapshot["latest_timestamp"]` to `LAST_PROCESSED_CANDLE_TS`.

If the timestamp is unchanged:

- do not call `emit_strategy_signals()`
- print a light status line such as:

```python
print(f"[{...}] 等待新 5m K 线")
```

If the timestamp is newer:

- build the loop state
- evaluate once
- update `LAST_PROCESSED_CANDLE_TS`

- [ ] **Step 3: Run the targeted tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_run_jesse_live_loop.py -q
```

Expected: PASS.

### Task 3: Practical validation

**Files:**
- No new files required

- [ ] **Step 1: Restart dry-run**

Run:

```bash
make dryrun-reset-up
```

- [ ] **Step 2: Observe log cadence**

Run:

```bash
make dryrun-log
```

Expected: the log should show many more “等待新 5m K 线” intervals and far fewer actual action emissions within the same 5-minute period.

- [ ] **Step 3: Run full tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest
```

Expected: PASS.

## Self-Review

- Spec coverage: The plan gates dry-run decisions on new 5m candles and adds an explicit waiting state.
- Placeholder scan: Tasks include exact files, exact gating behavior, and direct commands.
- Type consistency: The plan consistently treats `latest_timestamp` as the single source of candle progression.
