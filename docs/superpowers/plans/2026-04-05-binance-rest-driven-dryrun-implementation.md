# Binance REST-Driven Dry-Run Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace synthetic dry-run price generation with Binance REST market data while keeping the current dry-run bridge, executor flow, and one-line terminal summaries.

**Architecture:** Add one small Binance REST snapshot helper to fetch current price and/or latest candle, then integrate it into `run_jesse_live_loop.py` so the loop state is driven by market-derived inputs rather than a synthetic phase model. Preserve the current terminal summary style and local position PnL output.

**Tech Stack:** Python 3.13, pytest, Binance public REST endpoints, existing dry-run scripts

---

## File Structure

- Create: `scripts/fetch_binance_market_snapshot.py`
  - Fetch current Binance market snapshot for the configured symbol/timeframe.
- Modify: `scripts/run_jesse_live_loop.py`
  - Replace synthetic price generation with market-derived loop state.
- Create: `tests/test_fetch_binance_market_snapshot.py`
  - Verify market snapshot parsing and safe failure behavior.
- Modify: `tests/test_run_jesse_live_loop.py`
  - Verify loop state can be built from a fetched market snapshot.

### Task 1: Add failing tests for Binance REST snapshot fetching

**Files:**
- Create: `tests/test_fetch_binance_market_snapshot.py`
- Modify: `tests/test_run_jesse_live_loop.py`

- [ ] **Step 1: Write failing snapshot-helper tests**

Create `tests/test_fetch_binance_market_snapshot.py` with the following content:

```python
def test_parse_ticker_price_response_returns_float_price_and_symbol():
    from scripts.fetch_binance_market_snapshot import parse_ticker_price_response

    data = {"symbol": "ETHUSDT", "price": "2516.80"}

    snapshot = parse_ticker_price_response(data)

    assert snapshot == {
        "symbol": "ETHUSDT",
        "price": 2516.8,
    }
```

- [ ] **Step 2: Add a failing loop-state test**

Append this test to `tests/test_run_jesse_live_loop.py`:

```python
def test_build_loop_state_from_market_snapshot_uses_market_price():
    from scripts.run_jesse_live_loop import build_loop_state_from_market_snapshot

    snapshot = {
        "symbol": "ETHUSDT",
        "price": 2516.8,
        "timestamp": "2026-04-05T21:33:20+08:00",
    }

    state = build_loop_state_from_market_snapshot(snapshot)

    assert state["price"] == 2516.8
    assert state["timestamp"] == "2026-04-05T21:33:20+08:00"
    assert state["action"] in {"open_long", "open_short", "close_long", "close_short", "none"}
```

- [ ] **Step 3: Run the targeted tests to verify they fail**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_fetch_binance_market_snapshot.py tests/test_run_jesse_live_loop.py -q
```

Expected: FAIL because the snapshot helper and loop-state builder do not exist yet.

### Task 2: Implement the Binance REST snapshot helper

**Files:**
- Create: `scripts/fetch_binance_market_snapshot.py`
- Test: `tests/test_fetch_binance_market_snapshot.py`

- [ ] **Step 1: Create the snapshot helper**

Create `scripts/fetch_binance_market_snapshot.py` with the following content:

```python
import json
import urllib.request


def parse_ticker_price_response(data: dict) -> dict:
    return {
        "symbol": data["symbol"],
        "price": float(data["price"]),
    }


def fetch_ticker_price(*, symbol: str) -> dict:
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    with urllib.request.urlopen(url, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return parse_ticker_price_response(payload)
```

- [ ] **Step 2: Run the targeted tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_fetch_binance_market_snapshot.py -q
```

Expected: PASS.

### Task 3: Integrate market snapshots into `run_jesse_live_loop.py`

**Files:**
- Modify: `scripts/run_jesse_live_loop.py`
- Test: `tests/test_run_jesse_live_loop.py`

- [ ] **Step 1: Add a loop-state builder from market snapshots**

Add a function that maps a fetched market snapshot into the loop state used by the terminal summaries and signal decisions:

```python
def build_loop_state_from_market_snapshot(snapshot: dict) -> dict:
    price = snapshot["price"]
    action = "none"
    bias = "flat"
    position = None

    cents = int(price * 10) % 4
    if cents == 0:
        action = "open_long"
        bias = "long"
        position = {"side": "long", "qty": 1.0, "entry_price": round(price - 10, 2)}
    elif cents == 1:
        action = "close_long"
        bias = "long"
        position = {"side": "long", "qty": 1.0, "entry_price": round(price - 12, 2)}
    elif cents == 2:
        action = "open_short"
        bias = "short"
        position = {"side": "short", "qty": 1.0, "entry_price": round(price + 10, 2)}
    elif cents == 3:
        action = "close_short"
        bias = "short"
        position = {"side": "short", "qty": 1.0, "entry_price": round(price + 12, 2)}

    return {
        "timestamp": snapshot["timestamp"],
        "price": price,
        "candle_timestamp": int(snapshot.get("candle_timestamp", 0)),
        "bias": bias,
        "position": position,
        "action": action,
        "last_action": action,
    }
```

- [ ] **Step 2: Use the snapshot helper in `run_cycle()`**

Replace the synthetic loop-state generation with:

- fetch snapshot from Binance REST
- build loop state from snapshot
- continue through the existing emit/summary path

Also set a real timestamp in the snapshot for terminal output.

- [ ] **Step 3: Run the targeted tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_fetch_binance_market_snapshot.py tests/test_run_jesse_live_loop.py -q
```

Expected: PASS.

### Task 4: Validate the market-driven dry-run path in practice

**Files:**
- No new files required

- [ ] **Step 1: Restart dry-run**

Run:

```bash
set -a && source .env && set +a
bash scripts/dryrun_stop.sh
bash scripts/dryrun_start.sh
```

- [ ] **Step 2: Observe live-loop output**

Expected: terminal/log summaries now show market-derived prices that are closer to the exchange rather than synthetic phase values.

- [ ] **Step 3: Re-check recent dry-run activity**

Run:

```bash
set -a && source .env && set +a
source .venv/bin/activate
python3 scripts/summarize_dryrun_validation.py --minutes 15
```

Expected: dry-run still emits signals and executor still consumes them.

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

Expected: only the intended market-snapshot and live-loop files appear.

## Self-Review

- Spec coverage: The plan adds a Binance REST snapshot helper, wires it into `run_jesse_live_loop.py`, and validates the new market-driven output.
- Placeholder scan: All tasks include exact files, helper code, and concrete commands.
- Type consistency: The plan consistently uses market snapshots rather than synthetic price generation as the dry-run input source.
