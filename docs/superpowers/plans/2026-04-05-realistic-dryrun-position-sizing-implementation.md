# Realistic Dry-Run Position Sizing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the placeholder-style dry-run quantity with a capital-aware quantity model derived from initial capital, leverage, position fraction, and current market price.

**Architecture:** Add one small sizing helper path that computes a realistic dry-run quantity from a simple formula. Reuse that helper in the current-position panel and dry-run terminal summaries so the displayed size, notional, and margin estimates become consistent with one another.

**Tech Stack:** Python 3.13, pytest, existing dry-run panel and summary scripts

---

## File Structure

- Modify: `scripts/build_current_position_panel.py`
  - Add the realistic quantity helper and integrate it into the panel view.
- Modify: `scripts/summarize_dryrun_account.py`
  - Reuse the same sizing assumptions if needed for account-facing outputs.
- Modify: `scripts/run_jesse_live_loop.py`
  - Use the same quantity model in terminal display when position state is incomplete or local dry-run context is needed.
- Create: `tests/test_realistic_dryrun_position_sizing.py`
  - Verify the sizing formula and downstream notional/margin values.

### Task 1: Add failing tests for the realistic quantity model

**Files:**
- Create: `tests/test_realistic_dryrun_position_sizing.py`

- [ ] **Step 1: Write the failing test file**

Create `tests/test_realistic_dryrun_position_sizing.py` with the following content:

```python
def test_compute_position_qty_from_initial_capital_leverage_and_fraction():
    from scripts.build_current_position_panel import compute_position_qty

    qty = compute_position_qty(
        initial_capital=1000.0,
        leverage=10.0,
        position_fraction=0.2,
        current_price=2100.0,
    )

    assert qty == 0.95238


def test_compute_position_qty_returns_zero_for_invalid_price():
    from scripts.build_current_position_panel import compute_position_qty

    assert compute_position_qty(
        initial_capital=1000.0,
        leverage=10.0,
        position_fraction=0.2,
        current_price=0.0,
    ) == 0.0


def test_compute_notional_usdt_uses_realistic_qty():
    from scripts.build_current_position_panel import compute_notional_usdt

    assert compute_notional_usdt(qty=0.95238, mark_price=2100.0) == 2000.0
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_realistic_dryrun_position_sizing.py -q
```

Expected: FAIL because the new quantity helper does not exist yet.

### Task 2: Implement the realistic quantity helper

**Files:**
- Modify: `scripts/build_current_position_panel.py`
- Test: `tests/test_realistic_dryrun_position_sizing.py`

- [ ] **Step 1: Add the core sizing helper**

In `scripts/build_current_position_panel.py`, add:

```python
def compute_position_qty(*, initial_capital: float, leverage: float, position_fraction: float, current_price: float) -> float:
    if current_price <= 0:
        return 0.0
    max_notional = initial_capital * leverage
    effective_notional = max_notional * position_fraction
    return round(effective_notional / current_price, 5)
```

- [ ] **Step 2: Run the targeted tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_realistic_dryrun_position_sizing.py tests/test_build_current_position_panel.py -q
```

Expected: PASS.

### Task 3: Integrate the model into current position panel output

**Files:**
- Modify: `scripts/build_current_position_panel.py`

- [ ] **Step 1: Use the sizing model in the panel builder**

In `build_current_position_panel(...)`, compute a first-version display quantity using:

```python
display_qty = compute_position_qty(
    initial_capital=initial_capital,
    leverage=leverage,
    position_fraction=0.2,
    current_price=mark_price,
)
```

Then use this `display_qty` consistently for:

- `大小(ETH)`
- `名义金额(USDT)`
- `保证金`

This first version is intentionally display-oriented and does not claim to be exchange-grade risk accounting.

- [ ] **Step 2: Run the panel script**

Run:

```bash
set -a && source .env && set +a
source .venv/bin/activate
python3 scripts/build_current_position_panel.py
```

Expected: the displayed quantity is no longer a hardcoded-looking `1.0` when price and leverage imply something else.

### Task 4: Integrate the same quantity model into dry-run terminal observability

**Files:**
- Modify: `scripts/run_jesse_live_loop.py`

- [ ] **Step 1: Reuse the same quantity logic for terminal display when appropriate**

Where terminal display needs a quantity view and persistent state does not provide a reliable quantity yet, use the same `compute_position_qty(...)` assumptions so the log output and panel output do not disagree.

- [ ] **Step 2: Run full tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest
```

Expected: PASS.

## Self-Review

- Spec coverage: The plan replaces placeholder quantity display with a simple capital-aware sizing formula.
- Placeholder scan: Tasks include exact helper formulas, file paths, and commands.
- Type consistency: The same quantity model is reused across panel and terminal display.
