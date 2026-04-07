# Shared Strategy Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract a shared `Ott2butKAMA` strategy core and make both backtest and dry-run rely on the same decision logic.

**Architecture:** First extract a pure evaluator layer for the essential `Ott2butKAMA` conditions (`ott`, `cross_up`, `cross_down`, `chop`/RSI filter, and directional intent). Then incrementally wire dry-run and backtest adapters onto that shared evaluator while keeping the surrounding execution and reporting layers intact.

**Tech Stack:** Python 3.13, pytest, existing strategy files, Binance candle inputs, Jesse backtest path

---

## File Structure

- Create: `strategies/shared/ott2butkama_core.py`
  - Pure reusable evaluator for `Ott2butKAMA`-style direction logic.
- Modify: `strategies/jesse/Ott2butKAMA/__init__.py`
  - Reuse the shared core where practical.
- Modify: `scripts/run_jesse_live_loop.py`
  - Replace its local heuristic intent logic with the shared evaluator.
- Modify: `scripts/run_single_backtest_case.py`
  - Introduce a shared-core-assisted path where possible without breaking current backtest execution.
- Create: `tests/test_ott2butkama_core.py`
  - Lock the shared evaluator behavior.
- Modify: `tests/test_run_jesse_live_loop.py`
  - Verify dry-run uses the shared evaluator.

### Task 1: Add failing tests for the shared strategy evaluator

**Files:**
- Create: `tests/test_ott2butkama_core.py`

- [ ] **Step 1: Write the failing test file**

Create `tests/test_ott2butkama_core.py` with the following content:

```python
def test_evaluate_direction_returns_long_when_cross_up_and_chop_filter_pass():
    from strategies.shared.ott2butkama_core import evaluate_direction

    result = evaluate_direction(
        cross_up=True,
        cross_down=False,
        chop_value=65.0,
        chop_upper_band=54.4,
        chop_lower_band=45.6,
    )

    assert result == "long"


def test_evaluate_direction_returns_short_when_cross_down_and_chop_filter_pass():
    from strategies.shared.ott2butkama_core import evaluate_direction

    result = evaluate_direction(
        cross_up=False,
        cross_down=True,
        chop_value=40.0,
        chop_upper_band=54.4,
        chop_lower_band=45.6,
    )

    assert result == "short"


def test_evaluate_direction_returns_flat_when_neither_condition_passes():
    from strategies.shared.ott2butkama_core import evaluate_direction

    result = evaluate_direction(
        cross_up=False,
        cross_down=False,
        chop_value=50.0,
        chop_upper_band=54.4,
        chop_lower_band=45.6,
    )

    assert result == "flat"
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_ott2butkama_core.py -q
```

Expected: FAIL because the shared core module does not exist yet.

### Task 2: Implement the shared strategy core

**Files:**
- Create: `strategies/shared/ott2butkama_core.py`
- Test: `tests/test_ott2butkama_core.py`

- [ ] **Step 1: Create the evaluator module**

Create `strategies/shared/ott2butkama_core.py` with the following content:

```python
def evaluate_direction(*, cross_up: bool, cross_down: bool, chop_value: float, chop_upper_band: float, chop_lower_band: float) -> str:
    if cross_up and chop_value > chop_upper_band:
        return "long"
    if cross_down and chop_value < chop_lower_band:
        return "short"
    return "flat"
```

- [ ] **Step 2: Run the targeted tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_ott2butkama_core.py -q
```

Expected: PASS.

### Task 3: Reuse the shared core in dry-run

**Files:**
- Modify: `scripts/run_jesse_live_loop.py`
- Modify: `tests/test_run_jesse_live_loop.py`

- [ ] **Step 1: Replace local intent heuristic with shared evaluator**

In `scripts/run_jesse_live_loop.py`, stop deriving `intent` from the 3-close heuristic directly. Instead, compute the necessary intermediate values and call `evaluate_direction(...)` from `strategies.shared.ott2butkama_core`.

For the first step, it is acceptable if `cross_up`, `cross_down`, and `chop` are still approximated from current candle-derived inputs, as long as the final intent decision flows through the shared evaluator.

- [ ] **Step 2: Add a dry-run integration test**

Add a test to `tests/test_run_jesse_live_loop.py` asserting that `build_loop_state_from_candles(...)` uses the shared evaluator result to set `intent`.

- [ ] **Step 3: Run the targeted tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_ott2butkama_core.py tests/test_run_jesse_live_loop.py -q
```

Expected: PASS.

### Task 4: Reuse the shared core in backtest-adjacent code

**Files:**
- Modify: `strategies/jesse/Ott2butKAMA/__init__.py`
- Optionally modify: `scripts/run_single_backtest_case.py`

- [ ] **Step 1: Introduce the shared evaluator into the strategy file where safe**

Where practical, replace duplicated direct condition logic with calls to the shared evaluator or a wrapper around it, without changing backtest behavior.

- [ ] **Step 2: Run regression tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_ott2butkama_core.py tests/test_run_jesse_live_loop.py tests/test_ott2butkama_signal_hooks.py tests/test_ott2butkama_bridge_smoke.py -q
```

Expected: PASS.

### Task 5: Full verification

**Files:**
- No new files required

- [ ] **Step 1: Run full tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest
```

Expected: PASS.

- [ ] **Step 2: Inspect worktree status**

Run:

```bash
git status --short
```

Expected: only the shared-core files and touched adapters appear.

## Self-Review

- Spec coverage: The plan extracts a shared evaluator and starts moving dry-run and backtest-adjacent code onto it.
- Placeholder scan: Tasks include exact files, concrete code, and direct commands.
- Type consistency: The plan consistently distinguishes shared strategy intent evaluation from adapter-specific action normalization.
