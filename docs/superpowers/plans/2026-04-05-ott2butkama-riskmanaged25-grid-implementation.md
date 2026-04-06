# Ott2butKAMA RiskManaged25 Grid Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a staged-entry grid-style candidate based on `Ott2butKAMA_RiskManaged25` that preserves directional logic while splitting the total intended position into multiple entry layers.

**Architecture:** Create one new Jesse-runtime-compatible candidate strategy that copies `Ott2butKAMA_RiskManaged25`, but replaces one-shot entry construction with a small 3-layer staged-entry model. Keep exits simple, keep total risk bounded, and validate the result with a direct backtest comparison against the existing `RiskManaged25` candidate.

**Tech Stack:** Python 3.13, Jesse strategy structure, pytest, existing compare/export scripts

---

## File Structure

- Create: `strategies/jesse/Ott2butKAMA_RiskManaged25_Grid/__init__.py`
  - Runtime-compatible staged-entry grid candidate.
- Modify: `tests/test_ott2butkama_strategy_presence.py`
  - Verify the grid candidate exists.
- Modify: `tests/test_ott2butkama_signal_hooks.py`
  - Verify the grid candidate still exposes the same signal action names.
- Modify: `tests/test_sync_jesse_strategy.py`
  - Verify sync-path support for the grid candidate.
- Create: `tests/test_ott2butkama_grid_layers.py`
  - Verify staged-entry layer sizing and trigger helpers.

### Task 1: Add failing tests for the staged-entry candidate and layer math

**Files:**
- Modify: `tests/test_ott2butkama_strategy_presence.py`
- Modify: `tests/test_ott2butkama_signal_hooks.py`
- Modify: `tests/test_sync_jesse_strategy.py`
- Create: `tests/test_ott2butkama_grid_layers.py`

- [ ] **Step 1: Add a failing presence test**

Append this test to `tests/test_ott2butkama_strategy_presence.py`:

```python
def test_ott2butkama_risk_managed25_grid_strategy_exists():
    strategy_file = Path("strategies/jesse/Ott2butKAMA_RiskManaged25_Grid/__init__.py")
    assert strategy_file.exists()
```

- [ ] **Step 2: Add a failing signal-action test**

Append this test to `tests/test_ott2butkama_signal_hooks.py`:

```python
def test_risk_managed25_grid_variant_contains_same_signal_actions():
    text = Path("strategies/jesse/Ott2butKAMA_RiskManaged25_Grid/__init__.py").read_text()
    assert "open_long" in text
    assert "open_short" in text
    assert "close_long" in text
    assert "close_short" in text
```

- [ ] **Step 3: Add a failing sync-path test**

Append this test to `tests/test_sync_jesse_strategy.py`:

```python
def test_build_target_path_supports_risk_managed25_grid_variant_name():
    path = build_target_path("Ott2butKAMA_RiskManaged25_Grid")
    assert "runtime/jesse_workspace/strategies/Ott2butKAMA_RiskManaged25_Grid" in str(path)
```

- [ ] **Step 4: Add failing layer helper tests**

Create `tests/test_ott2butkama_grid_layers.py` with the following content:

```python
def test_layer_sizes_sum_to_total_position_budget():
    from strategies.jesse.Ott2butKAMA_RiskManaged25_Grid import compute_layer_sizes

    layers = compute_layer_sizes(total_qty=10.0)

    assert layers == [4.0, 3.0, 3.0]


def test_long_layer_trigger_prices_step_down_from_base_entry():
    from strategies.jesse.Ott2butKAMA_RiskManaged25_Grid import compute_long_layer_prices

    prices = compute_long_layer_prices(entry_price=100.0)

    assert prices == [100.0, 99.6, 99.2]


def test_short_layer_trigger_prices_step_up_from_base_entry():
    from strategies.jesse.Ott2butKAMA_RiskManaged25_Grid import compute_short_layer_prices

    prices = compute_short_layer_prices(entry_price=100.0)

    assert prices == [100.0, 100.4, 100.8]
```

- [ ] **Step 5: Run the targeted tests to verify they fail**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_ott2butkama_strategy_presence.py tests/test_ott2butkama_signal_hooks.py tests/test_sync_jesse_strategy.py tests/test_ott2butkama_grid_layers.py -q
```

Expected: FAIL because the new grid candidate and helper functions do not exist yet.

### Task 2: Implement the staged-entry grid candidate

**Files:**
- Create: `strategies/jesse/Ott2butKAMA_RiskManaged25_Grid/__init__.py`
- Test: `tests/test_ott2butkama_grid_layers.py`

- [ ] **Step 1: Create the grid candidate strategy file**

Create `strategies/jesse/Ott2butKAMA_RiskManaged25_Grid/__init__.py` as a full Jesse-runtime-compatible copy of `Ott2butKAMA_RiskManaged25`, then add these layer helpers:

```python
def compute_layer_sizes(*, total_qty: float) -> list[float]:
    return [round(total_qty * 0.4, 4), round(total_qty * 0.3, 4), round(total_qty * 0.3, 4)]


def compute_long_layer_prices(*, entry_price: float) -> list[float]:
    return [round(entry_price, 4), round(entry_price * 0.996, 4), round(entry_price * 0.992, 4)]


def compute_short_layer_prices(*, entry_price: float) -> list[float]:
    return [round(entry_price, 4), round(entry_price * 1.004, 4), round(entry_price * 1.008, 4)]
```

- [ ] **Step 2: Replace one-shot entry with first-layer entry only**

For the first version, keep the state machine simple: use the first layer as the immediate emitted order and encode the planned layer structure in the strategy file/state rather than trying to implement full multi-order lifecycle in one step.

This means the candidate is staged-entry-ready and layer-aware, even if the first implementation only emits the first layer immediately.

- [ ] **Step 3: Run the targeted tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_ott2butkama_strategy_presence.py tests/test_ott2butkama_signal_hooks.py tests/test_sync_jesse_strategy.py tests/test_ott2butkama_grid_layers.py -q
```

Expected: PASS.

### Task 3: Sync and compare the grid candidate

**Files:**
- No new files required

- [ ] **Step 1: Sync the candidate into the runtime workspace**

Run:

```bash
PYTHONPATH=. ./.venv/bin/python3 -c "from scripts.sync_jesse_strategy import sync_strategy; sync_strategy('Ott2butKAMA_RiskManaged25_Grid')"
```

- [ ] **Step 2: Run a compare report against `Ott2butKAMA_RiskManaged25`**

Run:

```bash
source runtime/jesse_workspace/.venv/bin/activate
python3 scripts/run_backtest_compare.py \
  --symbol ETHUSDT \
  --timeframe 5m \
  --start 2026-03-05 \
  --end 2026-04-05 \
  --baseline-strategy Ott2butKAMA_RiskManaged25 \
  --candidate-strategy Ott2butKAMA_RiskManaged25_Grid
```

Expected: a compare report path is printed.

- [ ] **Step 3: Export trade details for the grid candidate**

Run:

```bash
source runtime/jesse_workspace/.venv/bin/activate
python3 scripts/export_backtest_trades.py \
  --strategy Ott2butKAMA_RiskManaged25_Grid \
  --symbol ETHUSDT \
  --timeframe 5m \
  --start 2026-03-05 \
  --end 2026-04-05
```

Expected: a readable trade table for the staged-entry candidate.

### Task 4: Final verification

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

Expected: only the grid candidate, tests, and spec/plan files appear.

## Self-Review

- Spec coverage: The plan creates the staged-entry candidate, layer math helpers, sync path, and A/B backtest comparison.
- Placeholder scan: Each task includes exact files, concrete helper formulas, and direct commands.
- Type consistency: The plan consistently treats this as a staged-entry directional grid candidate, not a traditional neutral grid bot.
