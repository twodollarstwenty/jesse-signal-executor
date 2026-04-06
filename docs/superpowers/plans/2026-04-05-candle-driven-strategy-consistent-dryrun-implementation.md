# Candle-Driven Strategy-Consistent Dry-Run Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current lightweight price-to-action mapping with a candle-driven dry-run evaluator that is materially closer to the backtest strategy logic.

**Architecture:** Keep the existing signal bridge, executor, notifications, and account/panel/logging features. Add a small Binance Futures kline snapshot helper, compute a minimal candle-based strategy evaluation state from recent candles, and let `run_jesse_live_loop.py` emit actions from that state instead of from modulo/price mapping.

**Tech Stack:** Python 3.13, pytest, Binance Futures REST klines, existing Ott2butKAMA signal semantics

---

## File Structure

- Create: `scripts/fetch_binance_kline_snapshot.py`
  - Fetch a recent kline window from Binance Futures.
- Modify: `scripts/run_jesse_live_loop.py`
  - Replace lightweight action mapping with candle-driven evaluation.
- Create: `tests/test_fetch_binance_kline_snapshot.py`
  - Verify kline fetch parsing and shape.
- Modify: `tests/test_run_jesse_live_loop.py`
  - Add tests for candle-driven loop-state evaluation.

### Task 1: Add failing tests for candle-driven dry-run evaluation

**Files:**
- Create: `tests/test_fetch_binance_kline_snapshot.py`
- Modify: `tests/test_run_jesse_live_loop.py`

- [ ] **Step 1: Write failing kline-snapshot tests**

Create `tests/test_fetch_binance_kline_snapshot.py` with the following content:

```python
def test_parse_klines_response_returns_close_prices_and_latest_timestamp():
    from scripts.fetch_binance_kline_snapshot import parse_klines_response

    payload = [
        [1712188800000, "2500.0", "2510.0", "2490.0", "2505.0", "100"],
        [1712189100000, "2505.0", "2520.0", "2500.0", "2516.8", "120"],
    ]

    snapshot = parse_klines_response(payload)

    assert snapshot["close_prices"] == [2505.0, 2516.8]
    assert snapshot["latest_timestamp"] == 1712189100000
```

- [ ] **Step 2: Add a failing candle-driven loop-state test**

Append this test to `tests/test_run_jesse_live_loop.py`:

```python
def test_build_loop_state_from_candles_uses_recent_close_prices():
    from scripts.run_jesse_live_loop import build_loop_state_from_candles

    snapshot = {
        "symbol": "ETHUSDT",
        "close_prices": [2505.0, 2516.8, 2524.1],
        "latest_timestamp": 1712189100000,
        "timestamp": "2026-04-05T21:33:20+08:00",
    }

    state = build_loop_state_from_candles(snapshot)

    assert state["price"] == 2524.1
    assert state["timestamp"] == "2026-04-05T21:33:20+08:00"
    assert state["action"] in {"open_long", "open_short", "close_long", "close_short", "none"}
```

- [ ] **Step 3: Run the targeted tests to verify they fail**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_fetch_binance_kline_snapshot.py tests/test_run_jesse_live_loop.py -q
```

Expected: FAIL because the kline helper and candle-driven state builder do not exist yet.

### Task 2: Implement Binance Futures kline snapshot helper

**Files:**
- Create: `scripts/fetch_binance_kline_snapshot.py`
- Test: `tests/test_fetch_binance_kline_snapshot.py`

- [ ] **Step 1: Create the snapshot helper**

Create `scripts/fetch_binance_kline_snapshot.py` with the following content:

```python
import json
import urllib.request


def parse_klines_response(payload: list[list]) -> dict:
    return {
        "close_prices": [float(row[4]) for row in payload],
        "latest_timestamp": int(payload[-1][0]) if payload else 0,
    }


def fetch_recent_klines(*, symbol: str, interval: str = "5m", limit: int = 50) -> dict:
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
    with urllib.request.urlopen(url, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    snapshot = parse_klines_response(payload)
    snapshot["symbol"] = symbol
    return snapshot
```

- [ ] **Step 2: Run the targeted tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_fetch_binance_kline_snapshot.py -q
```

Expected: PASS.

### Task 3: Replace price-mapping with candle-driven evaluation

**Files:**
- Modify: `scripts/run_jesse_live_loop.py`
- Test: `tests/test_run_jesse_live_loop.py`

- [ ] **Step 1: Add a candle-driven state builder**

In `scripts/run_jesse_live_loop.py`, add:

```python
def build_loop_state_from_candles(snapshot: dict) -> dict:
    close_prices = snapshot["close_prices"]
    price = close_prices[-1]

    if len(close_prices) < 3:
        action = "none"
        bias = "flat"
        position = None
    else:
        prev_price = close_prices[-2]
        prev_prev_price = close_prices[-3]
        position = None
        if price > prev_price > prev_prev_price:
            action = "open_long"
            bias = "long"
            position = {"side": "long", "qty": 1.0, "entry_price": price}
        elif price < prev_price < prev_prev_price:
            action = "open_short"
            bias = "short"
            position = {"side": "short", "qty": 1.0, "entry_price": price}
        else:
            action = "none"
            bias = "flat"

    return {
        "timestamp": snapshot["timestamp"],
        "price": price,
        "candle_timestamp": snapshot["latest_timestamp"],
        "bias": bias,
        "position": position,
        "action": action,
        "last_action": action,
    }
```

The first version only needs to be materially more plausible than the old modulo mapping, not fully identical to backtest.

- [ ] **Step 2: Use Binance klines in `run_cycle()`**

Replace the ticker-price-only action mapping with:

- fetch recent Binance Futures klines
- set snapshot timestamp
- build loop state from candles

If kline fetch fails, keep the current safe “log and skip emission” behavior.

- [ ] **Step 3: Run the targeted tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_fetch_binance_kline_snapshot.py tests/test_run_jesse_live_loop.py -q
```

Expected: PASS.

### Task 4: Practical validation

**Files:**
- No new files required

- [ ] **Step 1: Restart dry-run**

Run:

```bash
set -a && source .env && set +a
bash scripts/dryrun_stop.sh
bash scripts/dryrun_start.sh
```

- [ ] **Step 2: Observe one-line logs**

Run:

```bash
tail -f runtime/dryrun/logs/jesse-dryrun.log
```

Expected: action patterns should be materially more plausible than the old rapid modulo-based alternation.

- [ ] **Step 3: Run full tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest
```

Expected: PASS.

## Self-Review

- Spec coverage: The plan introduces candle-driven market input and replaces the lightweight action mapping.
- Placeholder scan: Tasks include exact files, helper code, and concrete commands.
- Type consistency: The plan consistently moves dry-run toward candle-driven strategy consistency without pretending to be a full native Jesse live engine.
