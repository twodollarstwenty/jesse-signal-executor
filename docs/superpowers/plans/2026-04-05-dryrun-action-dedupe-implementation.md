# Dry-Run Action Dedupe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent consecutive identical actions from being emitted repeatedly in the dry-run live loop while preserving terminal visibility of the current recommended action.

**Architecture:** Add a tiny in-memory memory of the last emitted action inside `run_jesse_live_loop.py`. Keep the current summary output and current action decision logic, but suppress emission when the action is `none` or unchanged from the last emitted action.

**Tech Stack:** Python 3.13, pytest

---

## File Structure

- Modify: `scripts/run_jesse_live_loop.py`
  - Add last-emitted-action memory and suppress duplicate emits.
- Modify: `tests/test_run_jesse_live_loop.py`
  - Add tests for duplicate-action suppression.

### Task 1: Add failing tests for duplicate-action suppression

**Files:**
- Modify: `tests/test_run_jesse_live_loop.py`

- [ ] **Step 1: Add a failing duplicate-action test**

Append this test to `tests/test_run_jesse_live_loop.py`:

```python
def test_emit_strategy_signals_suppresses_repeated_identical_action(monkeypatch: pytest.MonkeyPatch):
    import scripts.run_jesse_live_loop as module

    strategy = type("FakeStrategy", (), {})()
    strategy.symbol = "ETH-USDT"
    strategy.timeframe = "5m"
    strategy.buy = None
    strategy.sell = None

    loop_state = {
        "timestamp": "2026-04-05T21:33:20+08:00",
        "price": 2516.8,
        "candle_timestamp": 1712188800000,
        "bias": "long",
        "position": {"side": "long", "qty": 1.0, "entry_price": 2506.8},
        "action": "open_long",
        "last_action": "open_long",
    }

    monkeypatch.setattr(module, "build_strategy_instance", lambda: strategy)
    monkeypatch.setattr(module, "configure_strategy_for_signal_cycle", lambda current, loop_state=None: None)
    monkeypatch.setattr(module, "drive_strategy_cycle", lambda current, loop_state: True)
    module.LAST_EMITTED_ACTION = "open_long"

    result = module.emit_strategy_signals(loop_state)

    assert result["emitted"] is False
```

- [ ] **Step 2: Add a failing new-action test**

Append this test to `tests/test_run_jesse_live_loop.py`:

```python
def test_emit_strategy_signals_emits_when_action_changes(monkeypatch: pytest.MonkeyPatch):
    import scripts.run_jesse_live_loop as module

    strategy = type("FakeStrategy", (), {})()
    strategy.symbol = "ETH-USDT"
    strategy.timeframe = "5m"
    strategy.buy = None
    strategy.sell = None

    loop_state = {
        "timestamp": "2026-04-05T21:33:20+08:00",
        "price": 2516.8,
        "candle_timestamp": 1712188800000,
        "bias": "short",
        "position": {"side": "short", "qty": 1.0, "entry_price": 2526.8},
        "action": "close_short",
        "last_action": "close_short",
    }

    monkeypatch.setattr(module, "build_strategy_instance", lambda: strategy)
    monkeypatch.setattr(module, "configure_strategy_for_signal_cycle", lambda current, loop_state=None: None)
    monkeypatch.setattr(module, "drive_strategy_cycle", lambda current, loop_state: True)
    module.LAST_EMITTED_ACTION = "open_short"

    result = module.emit_strategy_signals(loop_state)

    assert result["emitted"] is True
```

- [ ] **Step 3: Run the targeted tests to verify they fail**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_run_jesse_live_loop.py -q
```

Expected: FAIL because duplicate actions are not suppressed yet.

### Task 2: Implement duplicate-action suppression

**Files:**
- Modify: `scripts/run_jesse_live_loop.py`
- Test: `tests/test_run_jesse_live_loop.py`

- [ ] **Step 1: Add a last-emitted-action memory**

Add a module-level variable:

```python
LAST_EMITTED_ACTION: str | None = None
```

- [ ] **Step 2: Suppress repeated identical actions**

In `emit_strategy_signals(...)`, implement this logic:

```python
if loop_state["action"] == "none":
    emitted = False
elif loop_state["action"] == LAST_EMITTED_ACTION:
    emitted = False
else:
    emitted = drive_strategy_cycle(strategy, loop_state)
    if emitted:
        LAST_EMITTED_ACTION = loop_state["action"]
```

Keep terminal summaries unchanged except for `emitted=yes/no` reflecting the new behavior.

- [ ] **Step 3: Run the targeted tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_run_jesse_live_loop.py -q
```

Expected: PASS.

### Task 3: Validate the effect in practice

**Files:**
- No new files required

- [ ] **Step 1: Restart dry-run**

Run:

```bash
set -a && source .env && set +a
bash scripts/dryrun_stop.sh
bash scripts/dryrun_start.sh
```

- [ ] **Step 2: Observe the live-loop log**

Run:

```bash
tail -f runtime/dryrun/logs/jesse-dryrun.log
```

Expected: repeated consecutive identical actions still appear in the summary, but only the first of each run is marked `emitted=yes`; subsequent identical actions are `emitted=no`.

- [ ] **Step 3: Run full tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest
```

Expected: PASS.
