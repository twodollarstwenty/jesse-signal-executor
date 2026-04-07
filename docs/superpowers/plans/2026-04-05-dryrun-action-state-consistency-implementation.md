# Dry-Run Action and Position-State Consistency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure dry-run computes directional intent first, then maps it into a legal action consistent with the current persisted position state.

**Architecture:** Keep the current candle-driven direction inference, but split it from action emission. Add one small normalization layer that converts `long/short/flat` intent into `open_long/open_short/close_long/close_short/none` based on the current persistent position. Keep the executor and signal schema unchanged.

**Tech Stack:** Python 3.13, pytest, PostgreSQL, existing dry-run scripts

---

## File Structure

- Modify: `scripts/run_jesse_live_loop.py`
  - Add intent-to-action normalization against persistent position state.
- Modify: `tests/test_run_jesse_live_loop.py`
  - Add targeted tests for legal action normalization.

### Task 1: Add failing tests for action normalization

**Files:**
- Modify: `tests/test_run_jesse_live_loop.py`

- [ ] **Step 1: Add a failing `short -> long intent` normalization test**

Append this test to `tests/test_run_jesse_live_loop.py`:

```python
def test_normalize_action_converts_long_intent_to_close_short_when_short_position_exists():
    from scripts.run_jesse_live_loop import normalize_intent_to_action

    position = {"side": "short", "qty": 1.0, "entry_price": 2130.0}

    action = normalize_intent_to_action(intent="long", position=position)

    assert action == "close_short"
```

- [ ] **Step 2: Add a failing `long -> short intent` normalization test**

Append this test to `tests/test_run_jesse_live_loop.py`:

```python
def test_normalize_action_converts_short_intent_to_close_long_when_long_position_exists():
    from scripts.run_jesse_live_loop import normalize_intent_to_action

    position = {"side": "long", "qty": 1.0, "entry_price": 2130.0}

    action = normalize_intent_to_action(intent="short", position=position)

    assert action == "close_long"
```

- [ ] **Step 3: Add a failing same-side suppression test**

Append this test to `tests/test_run_jesse_live_loop.py`:

```python
def test_normalize_action_returns_none_for_same_side_intent():
    from scripts.run_jesse_live_loop import normalize_intent_to_action

    position = {"side": "short", "qty": 1.0, "entry_price": 2130.0}

    action = normalize_intent_to_action(intent="short", position=position)

    assert action == "none"
```

- [ ] **Step 4: Run the targeted tests to verify they fail**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_run_jesse_live_loop.py -q
```

Expected: FAIL because the normalization helper does not exist yet and the loop still emits raw open actions against existing opposite positions.

### Task 2: Implement intent-to-action normalization

**Files:**
- Modify: `scripts/run_jesse_live_loop.py`
- Test: `tests/test_run_jesse_live_loop.py`

- [ ] **Step 1: Add a normalization helper**

In `scripts/run_jesse_live_loop.py`, add:

```python
def normalize_intent_to_action(*, intent: str, position: dict | None) -> str:
    if position is None:
        return {"long": "open_long", "short": "open_short", "flat": "none"}.get(intent, "none")

    side = position["side"]
    if side == "long":
        return {"long": "none", "short": "close_long", "flat": "close_long"}.get(intent, "none")
    if side == "short":
        return {"short": "none", "long": "close_short", "flat": "close_short"}.get(intent, "none")
    return {"long": "open_long", "short": "open_short", "flat": "none"}.get(intent, "none")
```

- [ ] **Step 2: Split intent from action in the candle-driven state builder**

Instead of directly assigning `action=open_long/open_short`, make `build_loop_state_from_candles(...)` produce a directional `intent` field such as:

- `long`
- `short`
- `flat`

Then in `run_cycle()` or just before emission, fetch the current persistent position and normalize `intent -> action` using the helper.

- [ ] **Step 3: Ensure summaries reflect normalized action**

The one-line summary should display the normalized legal action, not the raw intent.

- [ ] **Step 4: Run targeted tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_run_jesse_live_loop.py -q
```

Expected: PASS.

### Task 3: Practical validation

**Files:**
- No new files required

- [ ] **Step 1: Fresh restart**

Run:

```bash
make dryrun-reset-up
```

- [ ] **Step 2: Observe log output**

Run:

```bash
make dryrun-log
```

Expected: if the current position is short, the system should not emit `open_long`; it should emit `close_short` first, and vice versa for long positions.

- [ ] **Step 3: Run full tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest
```

Expected: PASS.

## Self-Review

- Spec coverage: The plan adds explicit intent/action normalization and aligns terminal display with legal actions.
- Placeholder scan: Tasks include exact helper behavior, file paths, and commands.
- Type consistency: The plan consistently distinguishes `intent` from `action`.
