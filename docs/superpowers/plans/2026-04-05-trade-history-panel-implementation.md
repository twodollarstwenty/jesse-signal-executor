# Trade History Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a first-version trade-history panel/data view that matches the requested fields and uses current dry-run tables honestly.

**Architecture:** Build one lightweight script that reads dry-run event tables and renders a trade-history table. The first version will use internal event data, not exchange-grade fill data, and will explicitly show placeholder values for fields such as fee and role when no real execution source exists yet.

**Tech Stack:** Python 3.13, PostgreSQL, pytest

---

## File Structure

- Create: `scripts/build_trade_history_panel.py`
  - Build and print the trade-history panel/data view.
- Create: `tests/test_build_trade_history_panel.py`
  - Verify field mapping and first-version placeholder behavior.

### Task 1: Add failing tests for trade-history panel field mapping

**Files:**
- Create: `tests/test_build_trade_history_panel.py`

- [ ] **Step 1: Write the failing test file**

Create `tests/test_build_trade_history_panel.py` with the following content:

```python
def test_translate_actions_to_chinese_direction_labels():
    from scripts.build_trade_history_panel import translate_action_label

    assert translate_action_label("open_long") == "开多"
    assert translate_action_label("open_short") == "开空"
    assert translate_action_label("close_long") == "平多"
    assert translate_action_label("close_short") == "平空"


def test_render_trade_history_row_contains_requested_fields():
    from scripts.build_trade_history_panel import render_trade_history_row

    row = {
        "time": "2026-04-06 09:23:25",
        "contract": "ETHUSDT 永续",
        "direction": "平空",
        "price": 2114.84,
        "qty_text": "0.362 ETH",
        "fee_text": "--",
        "role": "dry-run",
        "realized_pnl_text": "+4.96060999 USDT",
    }

    text = render_trade_history_row(row)

    assert "2026-04-06 09:23:25" in text
    assert "ETHUSDT 永续" in text
    assert "平空" in text
    assert "2114.84" in text
    assert "0.362 ETH" in text
    assert "--" in text
    assert "dry-run" in text
    assert "+4.96060999 USDT" in text


def test_build_trade_row_uses_dryrun_placeholders_for_fee_and_role():
    from scripts.build_trade_history_panel import build_trade_row

    row = build_trade_row(
        signal_time="2026-04-06 09:23:25",
        symbol="ETHUSDT",
        action="close_short",
        payload={"price": 2114.84, "qty": 0.362},
        realized_pnl=4.96060999,
    )

    assert row["fee_text"] == "--"
    assert row["role"] == "dry-run"
    assert row["direction"] == "平空"
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_build_trade_history_panel.py -q
```

Expected: FAIL because the trade-history script does not exist yet.

### Task 2: Implement the first-version trade-history panel

**Files:**
- Create: `scripts/build_trade_history_panel.py`
- Test: `tests/test_build_trade_history_panel.py`

- [ ] **Step 1: Create core field helpers**

Create `scripts/build_trade_history_panel.py` with helpers:

```python
def translate_action_label(action: str) -> str:
    return {
        "open_long": "开多",
        "open_short": "开空",
        "close_long": "平多",
        "close_short": "平空",
    }.get(action, action)


def build_trade_row(*, signal_time: str, symbol: str, action: str, payload: dict, realized_pnl: float) -> dict:
    qty = float(payload.get("qty", 1.0))
    base_asset = symbol.replace("USDT", "")
    return {
        "time": signal_time,
        "contract": f"{symbol} 永续",
        "direction": translate_action_label(action),
        "price": float(payload.get("price", 0.0)),
        "qty_text": f"{qty:.3f} {base_asset}",
        "fee_text": "--",
        "role": "dry-run",
        "realized_pnl_text": f"{realized_pnl:+.8f} USDT",
    }


def render_trade_history_row(row: dict) -> str:
    return " | ".join(
        [
            row["time"],
            row["contract"],
            row["direction"],
            str(row["price"]),
            row["qty_text"],
            row["fee_text"],
            row["role"],
            row["realized_pnl_text"],
        ]
    )
```

- [ ] **Step 2: Add a first-version realized-PnL pairing reader**

Use the same `signal_events(status='execute')` event sequence to build trade rows. The first version can pair open/close actions sequentially and only assign non-zero realized PnL on close rows.

- [ ] **Step 3: Add `main()`**

Support a simple direct run such as:

```bash
python3 scripts/build_trade_history_panel.py
```

and print rows in reverse chronological order.

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

Expected: a readable trade-history table using the requested field structure.

- [ ] **Step 2: Run full tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest
```

Expected: PASS.

## Self-Review

- Spec coverage: The plan implements the requested trade-history fields and explicitly uses placeholders for exchange-only fields not yet available.
- Placeholder scan: Tasks include exact file paths, helper functions, and commands.
- Type consistency: The plan keeps fee/role honest for dry-run rather than inventing exchange-grade values.
