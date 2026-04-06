# Trade History Reality Improvement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the realism of the trade-history panel by adding meaningful realized PnL on close rows, handling `price = 0` rows safely, and keeping fee/role fields honest.

**Architecture:** Keep the current panel structure unchanged. Extend the trade-history builder with a best-effort pairing model for realized PnL, filter or neutralize impossible price rows, and continue using explicit placeholders for unavailable exchange-only fields.

**Tech Stack:** Python 3.13, PostgreSQL, pytest

---

## File Structure

- Modify: `scripts/build_trade_history_panel.py`
  - Improve pairing logic, zero-price handling, and row rendering.
- Modify: `tests/test_build_trade_history_panel.py`
  - Add coverage for close-row realized PnL and zero-price handling.

### Task 1: Add failing tests for improved trade-history realism

**Files:**
- Modify: `tests/test_build_trade_history_panel.py`

- [ ] **Step 1: Add a failing realized-PnL pairing test**

Append this test to `tests/test_build_trade_history_panel.py`:

```python
def test_compute_realized_pnl_pairs_open_and_close_long():
    from scripts.build_trade_history_panel import compute_realized_pnl_rows

    rows = [
        ("2026-04-06 09:20:00", "ETHUSDT", "open_long", {"price": 2000.0, "qty": 1.0}),
        ("2026-04-06 09:30:00", "ETHUSDT", "close_long", {"price": 2050.0, "qty": 1.0}),
    ]

    trade_rows = compute_realized_pnl_rows(rows)

    assert trade_rows[-1]["realized_pnl_text"] == "+50.00000000 USDT"
```

- [ ] **Step 2: Add a failing zero-price handling test**

Append this test to `tests/test_build_trade_history_panel.py`:

```python
def test_build_trade_row_replaces_zero_price_with_placeholder():
    from scripts.build_trade_history_panel import build_trade_row

    row = build_trade_row(
        signal_time="2026-04-06 09:23:25",
        symbol="ETHUSDT",
        action="open_long",
        payload={"price": 0.0, "qty": 1.0},
        realized_pnl=0.0,
    )

    assert row["price_text"] == "--"
```

- [ ] **Step 3: Run the targeted tests to verify they fail**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_build_trade_history_panel.py -q
```

Expected: FAIL because the first-version script does not yet implement these behaviors.

### Task 2: Improve trade-history panel value quality

**Files:**
- Modify: `scripts/build_trade_history_panel.py`
- Test: `tests/test_build_trade_history_panel.py`

- [ ] **Step 1: Add a realized-PnL pairing helper**

Implement a helper like:

```python
def compute_realized_pnl_rows(rows):
    ...
```

that walks executed signal rows in time order and assigns non-zero realized PnL on close rows when it can match a prior open row of the same direction.

- [ ] **Step 2: Improve zero-price handling**

In `build_trade_row(...)`, if `price <= 0`, set:

```python
"price_text": "--"
```

and do not render `0.0` as a meaningful execution price.

- [ ] **Step 3: Keep fee and role honest**

Continue using:

- `fee_text = "--"`
- `role = "dry-run"`

unless a better explicit estimate is added. Do not fabricate exchange-grade values.

- [ ] **Step 4: Run the targeted tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_build_trade_history_panel.py -q
```

Expected: PASS.

### Task 3: Practical validation

**Files:**
- No new files required

- [ ] **Step 1: Run the trade-history panel script**

Run:

```bash
set -a && source .env && set +a
source .venv/bin/activate
python3 scripts/build_trade_history_panel.py
```

Expected: the panel output is more believable, with non-zero realized PnL on matched close rows and no fake `0.0` execution prices.

- [ ] **Step 2: Run full tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest
```

Expected: PASS.

## Self-Review

- Spec coverage: The plan improves realized PnL, zero-price handling, and keeps fee/role honest.
- Placeholder scan: Tasks include exact files, helper responsibilities, and validation commands.
- Type consistency: The plan keeps the panel structure stable while only improving value quality.
