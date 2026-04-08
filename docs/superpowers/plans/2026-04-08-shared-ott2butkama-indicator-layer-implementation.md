# Shared Ott2butKAMA Indicator Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract a shared `Ott2butKAMA` indicator-input layer and begin using it in both dry-run and strategy-side code so the two paths derive direction from the same underlying features.

**Architecture:** First create one pure indicator-state module that computes the key `Ott2butKAMA` features from candle closes and strategy parameters. Then wire the dry-run path onto that shared state and lightly adapt the Jesse strategy wrapper so its direction decision also reads through the shared feature model.

**Tech Stack:** Python 3.13, pytest, TA-Lib, existing Ott2butKAMA strategy code

---

## File Structure

- Create: `strategies/shared/ott2butkama_features.py`
  - Shared indicator-state builder for Ott2butKAMA.
- Modify: `strategies/shared/ott2butkama_core.py`
  - Continue using the shared decision layer over shared feature values.
- Modify: `scripts/run_jesse_live_loop.py`
  - Replace heuristic candle inputs with the shared feature builder.
- Modify: `strategies/jesse/Ott2butKAMA/__init__.py`
  - Reuse the shared feature/decision path where safe.
- Create: `tests/test_ott2butkama_features.py`
  - Lock the shared feature-state behavior.
- Modify: `tests/test_run_jesse_live_loop.py`
  - Verify dry-run uses shared features rather than heuristic approximations.

### Task 1: Add failing tests for the shared feature builder

**Files:**
- Create: `tests/test_ott2butkama_features.py`

- [ ] **Step 1: Write the failing feature test file**

Create `tests/test_ott2butkama_features.py` with the following content:

```python
def test_build_feature_state_includes_cross_flags_and_chop_bands(monkeypatch):
    from strategies.shared.ott2butkama_features import build_feature_state

    closes = [2500.0, 2510.0, 2520.0, 2530.0]

    state = build_feature_state(
        closes=closes,
        ott_len=36,
        ott_percent=5.4,
        chop_rsi_len=17,
        chop_bandwidth=144,
    )

    assert "cross_up" in state
    assert "cross_down" in state
    assert "chop_value" in state
    assert state["chop_upper_band"] == 54.4
    assert state["chop_lower_band"] == 45.6
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_ott2butkama_features.py -q
```

Expected: FAIL because the shared feature module does not exist yet.

### Task 2: Implement the shared feature builder

**Files:**
- Create: `strategies/shared/ott2butkama_features.py`
- Test: `tests/test_ott2butkama_features.py`

- [ ] **Step 1: Create the feature-state module**

Create `strategies/shared/ott2butkama_features.py` with the following content:

```python
import talib

import custom_indicators_ottkama as cta


def build_feature_state(*, closes, ott_len: int, ott_percent: float, chop_rsi_len: int, chop_bandwidth: int) -> dict:
    ott = cta.ott(closes, ott_len, ott_percent, ma_type="kama", sequential=True)
    chop = talib.RSI(closes, chop_rsi_len)

    mavg = ott.mavg
    ott_line = ott.ott
    cross_up = bool(mavg[-2] <= ott_line[-2] and mavg[-1] > ott_line[-1])
    cross_down = bool(mavg[-2] >= ott_line[-2] and mavg[-1] < ott_line[-1])

    return {
        "cross_up": cross_up,
        "cross_down": cross_down,
        "chop_value": float(chop[-1]),
        "chop_upper_band": 40 + (chop_bandwidth / 10),
        "chop_lower_band": 60 - (chop_bandwidth / 10),
    }
```

- [ ] **Step 2: Run the targeted tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_ott2butkama_features.py tests/test_ott2butkama_core.py -q
```

Expected: PASS.

### Task 3: Use the shared feature builder in dry-run

**Files:**
- Modify: `scripts/run_jesse_live_loop.py`
- Modify: `tests/test_run_jesse_live_loop.py`

- [ ] **Step 1: Replace heuristic cross/chop approximations**

In `build_loop_state_from_candles(...)`, replace the current ad-hoc feature approximation with:

```python
features = build_feature_state(
    closes=close_prices,
    ott_len=36,
    ott_percent=5.4,
    chop_rsi_len=17,
    chop_bandwidth=144,
)

intent = evaluate_direction(**features)
```

Then derive `bias` from `intent` and keep the rest of the dry-run adapter path intact.

- [ ] **Step 2: Add/adjust dry-run tests**

Add a test to `tests/test_run_jesse_live_loop.py` that monkeypatches `build_feature_state(...)` and `evaluate_direction(...)` to verify the dry-run path now depends on the shared feature builder rather than the old local heuristic.

- [ ] **Step 3: Run targeted tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_ott2butkama_features.py tests/test_ott2butkama_core.py tests/test_run_jesse_live_loop.py -q
```

Expected: PASS.

### Task 4: Reuse the shared feature builder in the Jesse strategy wrapper

**Files:**
- Modify: `strategies/jesse/Ott2butKAMA/__init__.py`

- [ ] **Step 1: Replace local duplicated feature math where safe**

Use `build_feature_state(...)` in the strategy wrapper's `_evaluate_direction()` path instead of recomputing direction inputs independently, while preserving current strategy semantics.

- [ ] **Step 2: Run focused regression tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_ott2butkama_features.py tests/test_ott2butkama_core.py tests/test_ott2butkama_signal_hooks.py tests/test_ott2butkama_bridge_smoke.py tests/test_run_jesse_live_loop.py -q
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

Expected: only the shared feature layer and touched adapters appear.

## Self-Review

- Spec coverage: The plan extracts shared indicator-state computation and begins using it in both dry-run and the strategy wrapper.
- Placeholder scan: Tasks include exact files, concrete code, and direct commands.
- Type consistency: The plan clearly separates feature-state generation from final direction evaluation.
