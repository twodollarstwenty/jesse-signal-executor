# Persistent Position State Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `position_state` so it stores meaningful `side`, `qty`, and `entry_price`, enabling stable dry-run position display.

**Architecture:** Keep the existing state machine unchanged, but enhance the executor write path so executed open signals persist real `entry_price` and `qty`, executed close signals reset the state to flat/zero, and ignored/rejected signals leave state untouched. Once that data is trustworthy, rebind `run_jesse_live_loop.py` terminal output to use `position_state` as the source of truth.

**Tech Stack:** Python 3.13, PostgreSQL, pytest

---

## File Structure

- Modify: `apps/executor_service/service.py`
  - Persist meaningful `qty` and `entry_price` into `position_state`.
- Modify: `scripts/run_jesse_live_loop.py`
  - Re-enable persistent-position-backed terminal display once `position_state` is trustworthy.
- Modify: `tests/test_executor_service_unit.py`
  - Verify executor writes real position values on execute transitions.
- Modify: `tests/test_run_jesse_live_loop.py`
  - Verify terminal summaries now use persistent position values.

### Task 1: Add failing tests for persistent position values

**Files:**
- Modify: `tests/test_executor_service_unit.py`
- Modify: `tests/test_run_jesse_live_loop.py`

- [ ] **Step 1: Add a failing executor persistence test**

Append this test to `tests/test_executor_service_unit.py`:

```python
def test_upsert_position_side_persists_qty_and_entry_price_for_open_position():
    from apps.executor_service.service import build_position_payload

    payload = build_position_payload(
        symbol="ETHUSDT",
        side="long",
        signal_payload={"price": 2450.0, "qty": 2.5},
    )

    assert payload == {
        "symbol": "ETHUSDT",
        "side": "long",
        "qty": 2.5,
        "entry_price": 2450.0,
        "state_json": {},
    }
```

- [ ] **Step 2: Add a failing flat-reset test**

Append this test to `tests/test_executor_service_unit.py`:

```python
def test_build_position_payload_resets_qty_and_entry_for_flat_state():
    from apps.executor_service.service import build_position_payload

    payload = build_position_payload(
        symbol="ETHUSDT",
        side="flat",
        signal_payload={"price": 2450.0, "qty": 2.5},
    )

    assert payload == {
        "symbol": "ETHUSDT",
        "side": "flat",
        "qty": 0.0,
        "entry_price": 0.0,
        "state_json": {},
    }
```

- [ ] **Step 3: Re-add the failing persistent-display test**

Append this test to `tests/test_run_jesse_live_loop.py`:

```python
def test_print_cycle_summary_uses_persistent_position_for_display(monkeypatch, capsys):
    import scripts.run_jesse_live_loop as module

    loop_state = {
        "timestamp": "2026-04-05T21:33:30+08:00",
        "price": 2488.1,
        "bias": "long",
        "action": "hold",
        "emitted": False,
        "position": {"side": "long", "qty": 1.0, "entry_price": 2508.2},
    }

    monkeypatch.setattr(module, "fetch_persistent_position", lambda symbol: {"side": "long", "qty": 5.12, "entry_price": 2450.0})

    module.print_cycle_summary(loop_state)

    output = capsys.readouterr().out.strip()

    assert "qty=5.12" in output
    assert "entry=2450.0" in output
    assert "price=2488.1" in output
```

- [ ] **Step 4: Run the targeted tests to verify they fail**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_executor_service_unit.py tests/test_run_jesse_live_loop.py -q
```

Expected: FAIL because the executor does not yet build full position payloads and the display is not yet re-bound.

### Task 2: Persist real position values in executor

**Files:**
- Modify: `apps/executor_service/service.py`
- Test: `tests/test_executor_service_unit.py`

- [ ] **Step 1: Add a position payload builder**

In `apps/executor_service/service.py`, add:

```python
def build_position_payload(*, symbol: str, side: str, signal_payload: dict) -> dict:
    if side == "flat":
        return {
            "symbol": symbol,
            "side": "flat",
            "qty": 0.0,
            "entry_price": 0.0,
            "state_json": {},
        }

    return {
        "symbol": symbol,
        "side": side,
        "qty": float(signal_payload.get("qty", 1.0)),
        "entry_price": float(signal_payload.get("price", 0.0)),
        "state_json": {},
    }
```

- [ ] **Step 2: Update `upsert_position_side()` to use the payload**

Change `upsert_position_side()` so it accepts the built payload and inserts the real `qty` and `entry_price` instead of zeros.

- [ ] **Step 3: Update `run_once()` to pass signal payload through**

In `run_once()`, fetch `payload_json` along with `id`, `symbol`, and `action`, then when `decision == "execute" and next_state != normalized_current_side`, build a position payload and upsert it.

- [ ] **Step 4: Run targeted tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_executor_service_unit.py -q
```

Expected: PASS.

### Task 3: Rebind dry-run terminal output to persistent position state

**Files:**
- Modify: `scripts/run_jesse_live_loop.py`
- Test: `tests/test_run_jesse_live_loop.py`

- [ ] **Step 1: Add persistent position fetch helper**

Reintroduce a `fetch_persistent_position(symbol=...)` helper that reads the latest non-flat `position_state` row with `side`, `qty`, and `entry_price`.

- [ ] **Step 2: Prefer persistent position for displayed summaries**

In `print_cycle_summary(...)`, use the persistent position as the `position=` input for `render_position_summary(...)` whenever a non-flat row exists.

- [ ] **Step 3: Run targeted tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_run_jesse_live_loop.py -q
```

Expected: PASS.

### Task 4: Practical validation

**Files:**
- No new files required

- [ ] **Step 1: Restart dry-run from a clean state**

Run:

```bash
pkill -f "scripts/run_jesse_dryrun_loop.py" || true
pkill -f "scripts/run_executor_loop.py" || true
rm -f runtime/dryrun/pids/executor.pid runtime/dryrun/pids/jesse-dryrun.pid runtime/dryrun/last_action.txt
set -a && source .env && set +a
source .venv/bin/activate
python3 - <<'PY'
import os, psycopg2
conn = psycopg2.connect(
    host=os.getenv('POSTGRES_HOST','127.0.0.1'),
    port=int(os.getenv('POSTGRES_PORT','5432')),
    dbname=os.getenv('POSTGRES_DB','jesse_db'),
    user=os.getenv('POSTGRES_USER','jesse_user'),
    password=os.getenv('POSTGRES_PASSWORD','password'),
)
with conn:
    with conn.cursor() as cur:
        cur.execute('DELETE FROM execution_events')
        cur.execute('DELETE FROM signal_events')
        cur.execute('DELETE FROM position_state')
conn.close()
PY
bash scripts/dryrun_start.sh
```

- [ ] **Step 2: Observe terminal/log output**

Run:

```bash
tail -f runtime/dryrun/logs/jesse-dryrun.log
```

Expected: while the same position remains open, the displayed `entry=` no longer jumps between unrelated values.

- [ ] **Step 3: Run full tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest
```

Expected: PASS.

## Self-Review

- Spec coverage: The plan upgrades `position_state` to persist meaningful values and then uses that state for stable terminal display.
- Placeholder scan: All tasks include exact files, explicit code, and direct commands.
- Type consistency: The plan consistently treats `position_state` as the persistent source of `side`, `qty`, and `entry_price`.
