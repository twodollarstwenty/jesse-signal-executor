# Richer Dry-Run Log Line Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich the existing one-line `jesse-dryrun` output so it includes account summary values and notional USDT position size in real time.

**Architecture:** Reuse the account-summary helpers rather than creating a second accounting path. Extend the terminal summary renderers in `run_jesse_live_loop.py` so flat lines include initial capital/realized/unrealized/equity, and in-position lines add the same account values plus notional USDT size.

**Tech Stack:** Python 3.13, pytest, existing dry-run account summary helpers

---

## File Structure

- Modify: `scripts/run_jesse_live_loop.py`
  - Enrich flat and position one-line summaries with account values.
- Modify: `tests/test_run_jesse_live_loop.py`
  - Add assertions for account summary and notional fields.
- Modify: `scripts/summarize_dryrun_account.py`
  - Expose or reuse minimal helper(s) if needed for log-line composition.

### Task 1: Add failing tests for richer log-line fields

**Files:**
- Modify: `tests/test_run_jesse_live_loop.py`

- [ ] **Step 1: Add a failing flat-summary test**

Append this test to `tests/test_run_jesse_live_loop.py`:

```python
def test_render_flat_summary_contains_account_fields():
    from scripts.run_jesse_live_loop import render_flat_summary

    text = render_flat_summary(
        timestamp="2026-04-05T21:03:20+08:00",
        strategy="Ott2butKAMA",
        symbol="ETHUSDT",
        price=2057.99,
        bias="flat",
        action="none",
        emitted=False,
        initial_capital=1000.0,
        realized_pnl=35.2,
        unrealized_pnl=0.0,
        current_equity=1035.2,
    )

    assert "初始资金=1000.00" in text
    assert "已实现盈亏=+35.20" in text
    assert "未实现盈亏=+0.00" in text
    assert "当前权益=1035.20" in text
```

- [ ] **Step 2: Add a failing position-summary test**

Append this test to `tests/test_run_jesse_live_loop.py`:

```python
def test_render_position_summary_contains_account_and_notional_fields():
    from scripts.run_jesse_live_loop import render_position_summary

    position = {
        "side": "long",
        "qty": 1.0,
        "entry_price": 2058.05,
    }

    text = render_position_summary(
        timestamp="2026-04-05T21:03:30+08:00",
        strategy="Ott2butKAMA",
        symbol="ETHUSDT",
        current_price=2057.99,
        position=position,
        action="hold",
        emitted=False,
        initial_capital=1000.0,
        realized_pnl=35.2,
        unrealized_pnl=-0.06,
        current_equity=1035.14,
    )

    assert "持仓名义金额(USDT)=2057.99" in text
    assert "已实现盈亏=+35.20" in text
    assert "未实现盈亏=-0.06" in text
    assert "当前权益=1035.14" in text
```

- [ ] **Step 3: Run the targeted tests to verify they fail**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_run_jesse_live_loop.py -q
```

Expected: FAIL because the log-line renderers do not yet include these fields.

### Task 2: Implement richer one-line summaries

**Files:**
- Modify: `scripts/run_jesse_live_loop.py`
- Optionally modify: `scripts/summarize_dryrun_account.py`
- Test: `tests/test_run_jesse_live_loop.py`

- [ ] **Step 1: Extend `render_flat_summary()` signature and output**

Add parameters:

- `initial_capital`
- `realized_pnl`
- `unrealized_pnl`
- `current_equity`

Then append these Chinese fields to the flat one-line summary.

- [ ] **Step 2: Extend `render_position_summary()` signature and output**

Add parameters:

- `initial_capital`
- `realized_pnl`
- `unrealized_pnl`
- `current_equity`

Compute:

```python
notional_usdt = round(float(position['qty']) * current_price, 2)
```

Then append:

- `持仓名义金额(USDT)=...`
- `已实现盈亏=...`
- `未实现盈亏=...`
- `当前权益=...`

- [ ] **Step 3: In `print_cycle_summary()`, compute account values before rendering**

Use the existing dry-run account-summary helpers or equivalent local calls to obtain:

- initial capital (default `1000.0`)
- realized PnL
- unrealized PnL
- current equity

Pass those values into both summary renderers.

- [ ] **Step 4: Run the targeted tests**

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
set -a && source .env && set +a
bash scripts/dryrun_stop.sh
bash scripts/dryrun_start.sh
```

- [ ] **Step 2: Observe the log line output**

Run:

```bash
tail -f runtime/dryrun/logs/jesse-dryrun.log
```

Expected: one-line summaries now include account fields and, when in position, `持仓名义金额(USDT)`.

- [ ] **Step 3: Run full tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest
```

Expected: PASS.

## Self-Review

- Spec coverage: The plan adds account summary values and notional USDT size to the existing one-line output.
- Placeholder scan: All tasks include exact files, field names, and commands.
- Type consistency: The plan consistently uses the existing account-summary model rather than inventing a second accounting path.
