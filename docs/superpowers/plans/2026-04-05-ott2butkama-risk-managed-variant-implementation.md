# Ott2butKAMA Risk-Managed Variant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an `Ott2butKAMA_RiskManaged` variant that preserves the original signal logic while sizing each position to risk roughly `1%` of account equity at the stop-loss.

**Architecture:** Copy the current `Ott2butKAMA` strategy into a new runtime-compatible variant, add a `risk_per_trade` hyperparameter, and replace the current half-balance sizing logic with a stop-distance-based risk model. Validate the new sizing behavior with focused tests and then compare the variant against the original in a monthly backtest.

**Tech Stack:** Python 3.13, Jesse strategy structure, pytest, existing compare/export scripts

---

## File Structure

- Create: `strategies/jesse/Ott2butKAMA_RiskManaged/__init__.py`
  - Full Jesse-runtime-compatible strategy copy with fixed-risk sizing.
- Modify: `tests/test_ott2butkama_strategy_presence.py`
  - Verify the risk-managed variant exists.
- Modify: `tests/test_ott2butkama_signal_hooks.py`
  - Verify the risk-managed variant still contains the same signal actions.
- Modify: `tests/test_sync_jesse_strategy.py`
  - Verify the sync helper supports the risk-managed variant strategy name.
- Create: `tests/test_ott2butkama_risk_managed_sizing.py`
  - Verify the new sizing helpers behave as intended.

### Task 1: Add failing tests for the risk-managed variant and sizing behavior

**Files:**
- Modify: `tests/test_ott2butkama_strategy_presence.py`
- Modify: `tests/test_ott2butkama_signal_hooks.py`
- Modify: `tests/test_sync_jesse_strategy.py`
- Create: `tests/test_ott2butkama_risk_managed_sizing.py`

- [ ] **Step 1: Add a failing presence test**

Append this test to `tests/test_ott2butkama_strategy_presence.py`:

```python
def test_ott2butkama_risk_managed_strategy_exists():
    strategy_file = Path("strategies/jesse/Ott2butKAMA_RiskManaged/__init__.py")
    assert strategy_file.exists()
```

- [ ] **Step 2: Add a failing signal-action test**

Append this test to `tests/test_ott2butkama_signal_hooks.py`:

```python
def test_risk_managed_variant_contains_same_signal_actions():
    text = Path("strategies/jesse/Ott2butKAMA_RiskManaged/__init__.py").read_text()
    assert "open_long" in text
    assert "open_short" in text
    assert "close_long" in text
    assert "close_short" in text
```

- [ ] **Step 3: Add a failing sync-path test**

Append this test to `tests/test_sync_jesse_strategy.py`:

```python
def test_build_target_path_supports_risk_managed_variant_name():
    path = build_target_path("Ott2butKAMA_RiskManaged")
    assert "runtime/jesse_workspace/strategies/Ott2butKAMA_RiskManaged" in str(path)
```

- [ ] **Step 4: Add a failing sizing test file**

Create `tests/test_ott2butkama_risk_managed_sizing.py` with the following content:

```python
def test_compute_risk_fraction_from_hyperparameter():
    from strategies.jesse.Ott2butKAMA_RiskManaged import Ott2butKAMA_RiskManaged

    strategy = object.__new__(Ott2butKAMA_RiskManaged)
    strategy.hp = {"risk_per_trade": 10}

    assert strategy.risk_fraction == 0.01


def test_compute_risk_based_qty_for_long_uses_stop_distance():
    from strategies.jesse.Ott2butKAMA_RiskManaged import Ott2butKAMA_RiskManaged

    strategy = object.__new__(Ott2butKAMA_RiskManaged)
    strategy.balance = 10000
    strategy.price = 2000
    strategy.hp = {"risk_per_trade": 10}

    qty = strategy.compute_risk_based_qty(stop_price=1980)

    assert qty == 5.0


def test_compute_risk_based_qty_returns_zero_for_invalid_stop_distance():
    from strategies.jesse.Ott2butKAMA_RiskManaged import Ott2butKAMA_RiskManaged

    strategy = object.__new__(Ott2butKAMA_RiskManaged)
    strategy.balance = 10000
    strategy.price = 2000
    strategy.hp = {"risk_per_trade": 10}

    assert strategy.compute_risk_based_qty(stop_price=2000) == 0
    assert strategy.compute_risk_based_qty(stop_price=2001) == 0
```

- [ ] **Step 5: Run the targeted tests to verify they fail**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_ott2butkama_strategy_presence.py tests/test_ott2butkama_signal_hooks.py tests/test_sync_jesse_strategy.py tests/test_ott2butkama_risk_managed_sizing.py -q
```

Expected: FAIL because `Ott2butKAMA_RiskManaged` does not exist yet.

### Task 2: Implement the risk-managed variant

**Files:**
- Create: `strategies/jesse/Ott2butKAMA_RiskManaged/__init__.py`
- Test: `tests/test_ott2butkama_risk_managed_sizing.py`

- [ ] **Step 1: Create the variant strategy file**

Create `strategies/jesse/Ott2butKAMA_RiskManaged/__init__.py` as a full runtime-compatible copy of `Ott2butKAMA`, then make these changes:

1. add a new hyperparameter:

```python
{'name': 'risk_per_trade', 'type': int, 'min': 1, 'max': 50, 'default': 10}
```

2. add a property:

```python
@property
@cached
def risk_fraction(self):
    return self.hp['risk_per_trade'] / 1000
```

3. add a sizing helper:

```python
def compute_risk_based_qty(self, *, stop_price: float) -> float:
    stop_distance = self.price - stop_price
    if stop_distance <= 0:
        return 0
    risk_amount = self.balance * self.risk_fraction
    return risk_amount / stop_distance
```

4. replace the current `pos_size` property with a stop-distance-based version. For the first implementation, compute a long-style stop estimate using the same stop formula already used in `on_open_position()`:

```python
@property
@cached
def pos_size(self):
    estimated_stop = self.ott.ott[-1] - (self.ott.ott[-1] * self.stop)
    return self.compute_risk_based_qty(stop_price=estimated_stop)
```

This first version is intended as a practical risk-managed experiment, not a complete directional sizing engine.

- [ ] **Step 2: Run the targeted tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_ott2butkama_strategy_presence.py tests/test_ott2butkama_signal_hooks.py tests/test_sync_jesse_strategy.py tests/test_ott2butkama_risk_managed_sizing.py -q
```

Expected: PASS.

### Task 3: Sync and compare the risk-managed variant

**Files:**
- No new files required

- [ ] **Step 1: Sync the risk-managed variant into the runtime workspace**

Run:

```bash
PYTHONPATH=. ./.venv/bin/python3 -c "from scripts.sync_jesse_strategy import sync_strategy; sync_strategy('Ott2butKAMA_RiskManaged')"
```

- [ ] **Step 2: Run a compare report for original vs risk-managed variant**

Run:

```bash
source runtime/jesse_workspace/.venv/bin/activate
python3 scripts/run_backtest_compare.py \
  --symbol ETHUSDT \
  --timeframe 5m \
  --start 2026-03-05 \
  --end 2026-04-05 \
  --baseline-strategy Ott2butKAMA \
  --candidate-strategy Ott2butKAMA_RiskManaged
```

Expected: a compare report path is printed.

- [ ] **Step 3: Export trade details for the risk-managed variant**

Run:

```bash
source runtime/jesse_workspace/.venv/bin/activate
python3 scripts/export_backtest_trades.py \
  --strategy Ott2butKAMA_RiskManaged \
  --symbol ETHUSDT \
  --timeframe 5m \
  --start 2026-03-05 \
  --end 2026-04-05
```

Expected: a readable trade table that can be used to inspect practical risk behavior and position sizing outcomes.

- [ ] **Step 4: Inspect worktree status**

Run:

```bash
git status --short
```

Expected: only the risk-managed variant, touched tests, and plan/spec files for this work appear.

## Self-Review

- Spec coverage: The plan adds a risk-managed strategy variant, sizing tests, runtime sync, and A/B backtest validation.
- Placeholder scan: Tasks contain exact file paths, explicit parameter values, and concrete commands.
- Type consistency: The plan consistently uses `Ott2butKAMA_RiskManaged` as the fixed-risk variant name.
