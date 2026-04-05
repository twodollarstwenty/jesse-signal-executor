# Dynamic Dry-Run Signal Driver Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the fixed pseudo-state behavior in `run_jesse_live_loop.py` with a data-driven dry-run signal driver that prints one-line loop summaries and highlights floating PnL while in position.

**Architecture:** Keep the existing signal bridge and executor flow unchanged. Refactor `run_jesse_live_loop.py` into a small dynamic loop driver that derives state from changing data inputs, maintains minimal local position context for observability, and emits one-line terminal summaries for both flat and in-position states.

**Tech Stack:** Python 3.13, Jesse runtime imports, pytest

---

## File Structure

- Modify: `scripts/run_jesse_live_loop.py`
  - Replace fixed pseudo-state behavior with a dynamic driver and terminal summaries.
- Modify: `tests/test_run_jesse_live_loop.py`
  - Add tests for one-line summaries and local position PnL formatting.

### Task 1: Add failing tests for dynamic summaries and local position context

**Files:**
- Modify: `tests/test_run_jesse_live_loop.py`

- [ ] **Step 1: Add a failing flat-summary test**

Append this test to `tests/test_run_jesse_live_loop.py`:

```python
def test_render_flat_summary_contains_price_bias_action_and_emitted_flag():
    from scripts.run_jesse_live_loop import render_flat_summary

    text = render_flat_summary(
        timestamp="2026-04-05T21:03:20+08:00",
        strategy="Ott2butKAMA",
        symbol="ETHUSDT",
        price=2488.1,
        bias="flat",
        action="none",
        emitted=False,
    )

    assert "strategy=Ott2butKAMA" in text
    assert "symbol=ETHUSDT" in text
    assert "price=2488.1" in text
    assert "bias=flat" in text
    assert "action=none" in text
    assert "emitted=no" in text
```

- [ ] **Step 2: Add a failing in-position summary test**

Append this test to `tests/test_run_jesse_live_loop.py`:

```python
def test_render_position_summary_contains_floating_pnl_fields():
    from scripts.run_jesse_live_loop import render_position_summary

    position = {
        "side": "long",
        "qty": 5.12,
        "entry_price": 2450.0,
    }

    text = render_position_summary(
        timestamp="2026-04-05T21:03:30+08:00",
        strategy="Ott2butKAMA",
        symbol="ETHUSDT",
        current_price=2488.1,
        position=position,
        action="hold",
        emitted=False,
    )

    assert "side=long" in text
    assert "qty=5.12" in text
    assert "entry=2450.0" in text
    assert "price=2488.1" in text
    assert "pnl=" in text
    assert "pnl_pct=" in text
    assert "action=hold" in text
```

- [ ] **Step 3: Add a failing PnL helper test**

Append this test to `tests/test_run_jesse_live_loop.py`:

```python
def test_compute_position_pnl_for_short_position():
    from scripts.run_jesse_live_loop import compute_position_pnl

    position = {
        "side": "short",
        "qty": 2.0,
        "entry_price": 2500.0,
    }

    pnl, pnl_pct = compute_position_pnl(position=position, current_price=2400.0)

    assert pnl == 200.0
    assert pnl_pct == 4.0
```

- [ ] **Step 4: Run the targeted tests to verify they fail**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_run_jesse_live_loop.py -q
```

Expected: FAIL because the new summary/PnL helpers do not exist yet.

### Task 2: Implement one-line summaries and position PnL helpers

**Files:**
- Modify: `scripts/run_jesse_live_loop.py`
- Test: `tests/test_run_jesse_live_loop.py`

- [ ] **Step 1: Add helpers for PnL and summary rendering**

Add these functions to `scripts/run_jesse_live_loop.py`:

```python
def compute_position_pnl(*, position: dict, current_price: float) -> tuple[float, float]:
    side = position["side"]
    qty = float(position["qty"])
    entry_price = float(position["entry_price"])

    if side == "short":
        pnl = (entry_price - current_price) * qty
    else:
        pnl = (current_price - entry_price) * qty

    pnl_pct = ((current_price - entry_price) / entry_price) * 100 if side != "short" else ((entry_price - current_price) / entry_price) * 100
    return round(pnl, 2), round(pnl_pct, 2)


def render_flat_summary(*, timestamp: str, strategy: str, symbol: str, price: float, bias: str, action: str, emitted: bool) -> str:
    return f"[{timestamp}] strategy={strategy} symbol={symbol} price={price} position=flat bias={bias} action={action} emitted={'yes' if emitted else 'no'}"


def render_position_summary(*, timestamp: str, strategy: str, symbol: str, current_price: float, position: dict, action: str, emitted: bool) -> str:
    pnl, pnl_pct = compute_position_pnl(position=position, current_price=current_price)
    return (
        f"[{timestamp}] strategy={strategy} symbol={symbol} side={position['side']} qty={position['qty']} "
        f"entry={position['entry_price']} price={current_price} pnl={pnl:+.2f} pnl_pct={pnl_pct:+.2f}% "
        f"action={action} emitted={'yes' if emitted else 'no'}"
    )
```

- [ ] **Step 2: Run the targeted tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_run_jesse_live_loop.py -q
```

Expected: PASS for the new helper-level behavior.

### Task 3: Replace fixed pseudo-state with a dynamic loop driver

**Files:**
- Modify: `scripts/run_jesse_live_loop.py`

- [ ] **Step 1: Introduce a minimal local position context**

Add a simple in-memory position dict that can represent:

```python
{"side": "long" | "short", "qty": float, "entry_price": float}
```

or `None` when flat.

- [ ] **Step 2: Replace the fixed constants with evolving loop inputs**

The loop should no longer hardcode static values like one fixed `price`, one fixed `current_candle`, and one fixed cross state. Instead, derive a changing current price/input per loop from available runtime data and use that to choose among:

- `open_long`
- `open_short`
- `close_long`
- `close_short`
- `none`

The first implementation may remain lightweight, but it must evolve over time rather than replaying the same exact state forever.

- [ ] **Step 3: Print one-line summaries each cycle**

Use:

- `render_flat_summary(...)` when no position is open
- `render_position_summary(...)` when position exists

The printed line should describe the current loop, even when no signal is emitted.

- [ ] **Step 4: Keep existing signal bridge emission behavior**

When the loop chooses an action, continue emitting through the existing bridge path so dry-run and executor remain connected.

### Task 4: Validate the dynamic loop in practice

**Files:**
- No new files required

- [ ] **Step 1: Run the targeted live-loop tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_run_jesse_live_loop.py -q
```

Expected: PASS.

- [ ] **Step 2: Restart dry-run**

Run:

```bash
set -a && source .env && set +a
bash scripts/dryrun_stop.sh
bash scripts/dryrun_start.sh
```

- [ ] **Step 3: Observe one-line terminal summaries**

Expected: `jesse-dryrun` loop prints one-line summaries that show either flat-state bias/action or in-position floating PnL.

- [ ] **Step 4: Re-check dry-run summary after waiting**

Run:

```bash
set -a && source .env && set +a
source .venv/bin/activate
python3 scripts/summarize_dryrun_validation.py --minutes 15
```

Expected: more convincing recent event flow than the old fixed pseudo-state loop.

### Task 5: Final verification

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

Expected: only the intended live-loop and doc files appear.

## Self-Review

- Spec coverage: The plan adds dynamic observability, floating PnL summaries, and replaces fixed pseudo-state behavior with evolving loop inputs.
- Placeholder scan: All tasks include exact file paths, helper function code, and concrete validation commands.
- Type consistency: The plan consistently uses one-line flat and in-position summaries plus a minimal local position context.
