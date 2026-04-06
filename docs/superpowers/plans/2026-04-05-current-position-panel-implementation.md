# Current Position Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a first-version current-position panel data view that exposes the requested fields with explicit first-version calculation rules.

**Architecture:** Do not build a frontend page yet. First implement a reusable Python data/view model that computes the current position panel fields from the existing dry-run state and market price, with explicit handling of estimated fields such as margin and margin ratio. This creates a stable backend shape for future UI work.

**Tech Stack:** Python 3.13, PostgreSQL, pytest, existing dry-run account summary helpers

---

## File Structure

- Create: `scripts/build_current_position_panel.py`
  - Compute and print the current-position panel data view.
- Create: `tests/test_build_current_position_panel.py`
  - Verify panel-field calculations and display shape.

### Task 1: Add failing tests for the current-position panel view

**Files:**
- Create: `tests/test_build_current_position_panel.py`

- [ ] **Step 1: Write the failing test file**

Create `tests/test_build_current_position_panel.py` with the following content:

```python
def test_compute_notional_usdt_from_qty_and_mark_price():
    from scripts.build_current_position_panel import compute_notional_usdt

    assert compute_notional_usdt(qty=1.0, mark_price=2075.55) == 2075.55


def test_compute_margin_estimate_from_notional_and_leverage():
    from scripts.build_current_position_panel import compute_margin_estimate

    assert compute_margin_estimate(notional_usdt=2075.55, leverage=10) == 207.56


def test_compute_margin_ratio_estimate_from_margin_and_equity():
    from scripts.build_current_position_panel import compute_margin_ratio_estimate

    assert compute_margin_ratio_estimate(margin=207.56, equity=1000.0) == 20.76


def test_render_position_panel_contains_requested_fields():
    from scripts.build_current_position_panel import render_position_panel

    panel = {
        "symbol": "ETHUSDT 永续",
        "qty": 1.0,
        "notional_usdt": 2075.55,
        "margin": 207.56,
        "margin_ratio": 20.76,
        "entry_price": 2058.05,
        "mark_price": 2075.55,
        "liquidation_price": "--",
        "pnl_text": "+17.50 USDT (+0.85%)",
        "tp_sl": "TP 2120 / SL 2041",
    }

    text = render_position_panel(panel)

    assert "符号: ETHUSDT 永续" in text
    assert "大小(ETH): 1.0" in text
    assert "名义金额(USDT): 2075.55" in text
    assert "保证金: 207.56" in text
    assert "保证金比率: 20.76%" in text
    assert "开仓价格: 2058.05" in text
    assert "标记价格: 2075.55" in text
    assert "强平价格: --" in text
    assert "收益额（收益率）: +17.50 USDT (+0.85%)" in text
    assert "止盈/止损: TP 2120 / SL 2041" in text
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_build_current_position_panel.py -q
```

Expected: FAIL because the panel builder script does not exist yet.

### Task 2: Implement the current-position panel data view

**Files:**
- Create: `scripts/build_current_position_panel.py`
- Test: `tests/test_build_current_position_panel.py`

- [ ] **Step 1: Create the core field helpers**

Create `scripts/build_current_position_panel.py` with these helpers:

```python
def compute_notional_usdt(*, qty: float, mark_price: float) -> float:
    return round(qty * mark_price, 2)


def compute_margin_estimate(*, notional_usdt: float, leverage: float) -> float:
    return round(notional_usdt / leverage, 2)


def compute_margin_ratio_estimate(*, margin: float, equity: float) -> float:
    if equity <= 0:
        return 0.0
    return round((margin / equity) * 100, 2)
```

- [ ] **Step 2: Create the panel renderer**

Add:

```python
def render_position_panel(panel: dict) -> str:
    return "\n".join(
        [
            f"符号: {panel['symbol']}",
            f"大小(ETH): {panel['qty']}",
            f"名义金额(USDT): {panel['notional_usdt']}",
            f"保证金: {panel['margin']}",
            f"保证金比率: {panel['margin_ratio']}%",
            f"开仓价格: {panel['entry_price']}",
            f"标记价格: {panel['mark_price']}",
            f"强平价格: {panel['liquidation_price']}",
            f"收益额（收益率）: {panel['pnl_text']}",
            f"止盈/止损: {panel['tp_sl']}",
        ]
    )
```

- [ ] **Step 3: Add a first-version builder from current dry-run state**

The script should read:

- latest persisted position state
- current market price
- dry-run account summary values

Then assemble a panel dict using these first-version rules:

- `符号`: `<symbol> 永续`
- `大小(ETH)`: persisted qty
- `名义金额(USDT)`: `qty * mark_price`
- `保证金`: `名义金额 / 杠杆`
- `保证金比率`: `保证金 / 当前权益`
- `强平价格`: `--`
- `收益额（收益率）`: use unrealized PnL text when a position exists
- `止盈/止损`: `--` if unavailable

- [ ] **Step 4: Run the targeted tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_build_current_position_panel.py -q
```

Expected: PASS.

### Task 3: Practical validation

**Files:**
- No new files required

- [ ] **Step 1: Run the panel builder**

Run:

```bash
set -a && source .env && set +a
source .venv/bin/activate
python3 scripts/build_current_position_panel.py
```

Expected: a readable current-position panel using the requested fields and first-version rules.

- [ ] **Step 2: Run full tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest
```

Expected: PASS.

## Self-Review

- Spec coverage: The plan implements the requested position panel fields and explicit first-version calculations.
- Placeholder scan: All tasks include exact files, formulas, and commands.
- Type consistency: The plan explicitly distinguishes base-asset size from USDT notional amount.
