# Dry-Run Account Summary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a first-version dry-run account summary that shows initial capital, realized PnL, unrealized PnL, current equity, and current position details.

**Architecture:** Implement one small summary script that reads from existing dry-run tables and computes a best-effort account view. Use `1000 USDT` as the default initial capital, derive unrealized PnL from the current persisted position and current market price, and derive realized PnL from completed open/close cycles visible in the existing signal/execution history.

**Tech Stack:** Python 3.13, PostgreSQL, pytest, existing Binance market snapshot helper

---

## File Structure

- Create: `scripts/summarize_dryrun_account.py`
  - Compute and print the dry-run account summary.
- Create: `tests/test_summarize_dryrun_account.py`
  - Verify realized/unrealized/equity calculations and summary rendering.

### Task 1: Add failing tests for account summary calculations

**Files:**
- Create: `tests/test_summarize_dryrun_account.py`

- [ ] **Step 1: Write the failing test file**

Create `tests/test_summarize_dryrun_account.py` with the following content:

```python
def test_compute_current_equity_from_realized_and_unrealized_pnl():
    from scripts.summarize_dryrun_account import compute_current_equity

    equity = compute_current_equity(initial_capital=1000.0, realized_pnl=35.2, unrealized_pnl=-4.8)

    assert equity == 1030.4


def test_compute_unrealized_pnl_for_long_position():
    from scripts.summarize_dryrun_account import compute_unrealized_pnl

    position = {"side": "long", "qty": 1.0, "entry_price": 2058.05}

    pnl = compute_unrealized_pnl(position=position, current_price=2057.99)

    assert pnl == -0.06


def test_render_account_summary_contains_core_fields():
    from scripts.summarize_dryrun_account import render_account_summary

    text = render_account_summary(
        initial_capital=1000.0,
        realized_pnl=35.2,
        unrealized_pnl=-4.8,
        current_equity=1030.4,
        position={"side": "long", "qty": 1.0, "entry_price": 2058.05},
        current_price=2057.99,
    )

    assert "初始资金: 1000.00" in text
    assert "已实现盈亏: +35.20" in text
    assert "未实现盈亏: -4.80" in text
    assert "当前权益: 1030.40" in text
    assert "当前持仓: long" in text
    assert "持仓数量: 1.0" in text
    assert "开仓价: 2058.05" in text
    assert "当前价: 2057.99" in text
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_summarize_dryrun_account.py -q
```

Expected: FAIL because the new summary script does not exist yet.

### Task 2: Implement the account summary script

**Files:**
- Create: `scripts/summarize_dryrun_account.py`
- Test: `tests/test_summarize_dryrun_account.py`

- [ ] **Step 1: Create the script with core helpers**

Create `scripts/summarize_dryrun_account.py` with the following content:

```python
import argparse

from apps.shared.db import connect
from scripts.fetch_binance_market_snapshot import fetch_ticker_price


def compute_unrealized_pnl(*, position: dict | None, current_price: float | None) -> float:
    if not position or current_price is None:
        return 0.0
    side = position["side"]
    qty = float(position["qty"])
    entry_price = float(position["entry_price"])
    if side == "short":
        return round((entry_price - current_price) * qty, 2)
    return round((current_price - entry_price) * qty, 2)


def compute_current_equity(*, initial_capital: float, realized_pnl: float, unrealized_pnl: float) -> float:
    return round(initial_capital + realized_pnl + unrealized_pnl, 2)


def render_account_summary(*, initial_capital: float, realized_pnl: float, unrealized_pnl: float, current_equity: float, position: dict | None, current_price: float | None) -> str:
    lines = [
        f"初始资金: {initial_capital:.2f}",
        f"已实现盈亏: {realized_pnl:+.2f}",
        f"未实现盈亏: {unrealized_pnl:+.2f}",
        f"当前权益: {current_equity:.2f}",
    ]
    if position:
        lines.extend(
            [
                f"当前持仓: {position['side']}",
                f"持仓数量: {position['qty']}",
                f"开仓价: {position['entry_price']}",
                f"当前价: {current_price:.2f}",
            ]
        )
    else:
        lines.append("当前持仓: flat")
    return "\n".join(lines)
```

- [ ] **Step 2: Add first-version DB readers**

In the same script, add helpers to:

- fetch the latest non-flat position from `position_state`
- fetch the latest market price using `fetch_ticker_price(symbol='ETHUSDT')`
- compute a first-version realized PnL from completed open/close execution cycles using available event history

For the first version, a documented best-effort realized PnL calculation is acceptable.

- [ ] **Step 3: Add `main()` and CLI options**

Support:

```bash
python3 scripts/summarize_dryrun_account.py --initial-capital 1000
```

with `1000` as the default initial capital.

- [ ] **Step 4: Run the targeted tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_summarize_dryrun_account.py -q
```

Expected: PASS.

### Task 3: Practical validation

**Files:**
- No new files required

- [ ] **Step 1: Run the account summary script**

Run:

```bash
set -a && source .env && set +a
source .venv/bin/activate
python3 scripts/summarize_dryrun_account.py --initial-capital 1000
```

Expected: the script prints initial capital, realized PnL, unrealized PnL, current equity, and current position information.

- [ ] **Step 2: Run full tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest
```

Expected: PASS.

- [ ] **Step 3: Inspect worktree status**

Run:

```bash
git status --short
```

Expected: only the new account-summary script, tests, and spec/plan files appear.

## Self-Review

- Spec coverage: The plan covers initial capital, realized/unrealized PnL, current equity, and current position summary.
- Placeholder scan: The plan includes concrete files, helper functions, and commands.
- Type consistency: The plan consistently treats this as a dry-run account summary, not a full exchange-grade margin engine.
