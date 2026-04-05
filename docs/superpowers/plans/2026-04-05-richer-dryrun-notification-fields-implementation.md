# Richer Dry-Run Notification Fields Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve dry-run notification clarity by including `signal_time`, `execution_time`, `price`, and `position_side` in the WeCom dry-run message.

**Architecture:** Keep the existing WeCom sender unchanged. Update only the dry-run notifier query and formatter so it joins the needed signal fields and renders the richer message shape while remaining safe when payload keys are missing.

**Tech Stack:** Python 3.13, PostgreSQL, pytest

---

## File Structure

- Modify: `scripts/notify_dryrun_events.py`
  - Extend the SQL join and message formatter with the new fields.
- Modify: `tests/test_notify_dryrun_events.py`
  - Add coverage for richer message fields and payload fallbacks.

### Task 1: Add failing tests for richer dry-run notification fields

**Files:**
- Modify: `tests/test_notify_dryrun_events.py`

- [ ] **Step 1: Add a failing formatter test**

Append this test to `tests/test_notify_dryrun_events.py`:

```python
def test_format_execution_event_message_includes_signal_and_execution_context():
    from scripts.notify_dryrun_events import format_execution_event_message

    row = {
        "signal_time": "2024-04-04T08:00:00+08:00",
        "created_at": "2026-04-05T17:13:50+08:00",
        "strategy": "Ott2butKAMA",
        "symbol": "ETHUSDT",
        "action": "close_long",
        "decision": "execute",
        "reason": None,
        "price": 2500.0,
        "position_side": "long",
    }

    text = format_execution_event_message(row)

    assert "signal_time: 2024-04-04T08:00:00+08:00" in text
    assert "execution_time: 2026-04-05T17:13:50+08:00" in text
    assert "price: 2500.0" in text
    assert "position_side: long" in text
```

- [ ] **Step 2: Add a failing fetch-shape test**

Append this test to `tests/test_notify_dryrun_events.py`:

```python
def test_fetch_recent_execution_events_extracts_price_and_position_side(monkeypatch):
    from scripts.notify_dryrun_events import fetch_recent_execution_events

    rows = [
        (
            "2026-04-05T17:13:50+08:00",
            "2024-04-04T08:00:00+08:00",
            "Ott2butKAMA",
            "ETHUSDT",
            "close_long",
            "execute",
            None,
            {"price": 2500.0, "position_side": "long"},
        )
    ]

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query, params):
            self.query = query
            self.params = params

        def fetchall(self):
            return rows

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return FakeCursor()

        def close(self):
            return None

    monkeypatch.setattr("scripts.notify_dryrun_events.connect", lambda: FakeConnection())

    events = fetch_recent_execution_events(limit=5)

    assert events == [
        {
            "created_at": "2026-04-05T17:13:50+08:00",
            "signal_time": "2024-04-04T08:00:00+08:00",
            "strategy": "Ott2butKAMA",
            "symbol": "ETHUSDT",
            "action": "close_long",
            "decision": "execute",
            "reason": None,
            "price": 2500.0,
            "position_side": "long",
        }
    ]
```

- [ ] **Step 3: Run the targeted tests to verify they fail**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_notify_dryrun_events.py -q
```

Expected: FAIL because the notifier does not yet include the new fields.

### Task 2: Implement richer dry-run notification fields

**Files:**
- Modify: `scripts/notify_dryrun_events.py`
- Test: `tests/test_notify_dryrun_events.py`

- [ ] **Step 1: Extend the SQL join and extraction**

In `scripts/notify_dryrun_events.py`, update the query to fetch:

```sql
e.created_at,
s.signal_time,
s.strategy,
e.symbol,
s.action,
e.status,
NULL,
s.payload_json
```

Then extend the returned dict with:

```python
"signal_time": ...,
"price": payload.get("price", "N/A"),
"position_side": payload.get("position_side", "N/A"),
```

Use the same datetime-to-string fallback approach already used for `created_at`.

- [ ] **Step 2: Update the formatter**

Change `format_execution_event_message()` so the message includes these lines in this order:

```text
signal_time: ...
execution_time: ...
price: ...
position_side: ...
```

Replace the old generic `time:` label with `execution_time:`.

- [ ] **Step 3: Run targeted tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_notify_dryrun_events.py -q
```

Expected: PASS.

### Task 3: Final verification

**Files:**
- No new files required

- [ ] **Step 1: Run full tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest
```

Expected: PASS.

- [ ] **Step 2: Run the notifier manually**

Run:

```bash
set -a && source .env && set +a
source .venv/bin/activate
python3 scripts/notify_dryrun_events.py
```

Expected: WeCom receives dry-run messages with richer fields.

- [ ] **Step 3: Inspect worktree status**

Run:

```bash
git status --short
```

Expected: only the notifier script, notifier tests, and the spec/plan files appear.

## Self-Review

- Spec coverage: The plan covers all four requested field additions and keeps scope narrow.
- Placeholder scan: All tasks include exact files, exact fields, and concrete commands.
- Type consistency: The plan consistently uses `signal_time`, `execution_time`, `price`, and `position_side` as the enhanced dry-run fields.
