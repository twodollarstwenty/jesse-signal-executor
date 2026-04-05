# Ott2butKAMA RiskManaged25 Candidate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a formal `Ott2butKAMA_RiskManaged25` candidate and export its trade details side-by-side with the original `Ott2butKAMA` strategy.

**Architecture:** Reuse the already validated fixed-risk sizing logic from `Ott2butKAMA_RiskManaged`, but create a new runtime-compatible strategy directory with `risk_per_trade` defaulted to `25` (`2.5%`). Validate it with minimal tests, sync it into the Jesse runtime workspace, and then export monthly trade tables for both the original and the new candidate.

**Tech Stack:** Python 3.13, Jesse strategy structure, pytest, existing compare/export scripts

---

## File Structure

- Create: `strategies/jesse/Ott2butKAMA_RiskManaged25/__init__.py`
  - Full Jesse-runtime-compatible fixed-risk strategy candidate with `risk_per_trade = 25`.
- Modify: `tests/test_ott2butkama_strategy_presence.py`
  - Verify the new candidate exists.
- Modify: `tests/test_ott2butkama_signal_hooks.py`
  - Verify the candidate still contains the same four signal actions.
- Modify: `tests/test_sync_jesse_strategy.py`
  - Verify sync-path support for the candidate name.

### Task 1: Add failing tests for the RiskManaged25 candidate

**Files:**
- Modify: `tests/test_ott2butkama_strategy_presence.py`
- Modify: `tests/test_ott2butkama_signal_hooks.py`
- Modify: `tests/test_sync_jesse_strategy.py`

- [ ] **Step 1: Add a failing presence test**

Append this test to `tests/test_ott2butkama_strategy_presence.py`:

```python
def test_ott2butkama_risk_managed25_strategy_exists():
    strategy_file = Path("strategies/jesse/Ott2butKAMA_RiskManaged25/__init__.py")
    assert strategy_file.exists()
```

- [ ] **Step 2: Add a failing signal-action test**

Append this test to `tests/test_ott2butkama_signal_hooks.py`:

```python
def test_risk_managed25_variant_contains_same_signal_actions():
    text = Path("strategies/jesse/Ott2butKAMA_RiskManaged25/__init__.py").read_text()
    assert "open_long" in text
    assert "open_short" in text
    assert "close_long" in text
    assert "close_short" in text
```

- [ ] **Step 3: Add a failing sync-path test**

Append this test to `tests/test_sync_jesse_strategy.py`:

```python
def test_build_target_path_supports_risk_managed25_variant_name():
    path = build_target_path("Ott2butKAMA_RiskManaged25")
    assert "runtime/jesse_workspace/strategies/Ott2butKAMA_RiskManaged25" in str(path)
```

- [ ] **Step 4: Run the targeted tests to verify they fail**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_ott2butkama_strategy_presence.py tests/test_ott2butkama_signal_hooks.py tests/test_sync_jesse_strategy.py -q
```

Expected: FAIL because `Ott2butKAMA_RiskManaged25` does not exist yet.

### Task 2: Implement the RiskManaged25 candidate

**Files:**
- Create: `strategies/jesse/Ott2butKAMA_RiskManaged25/__init__.py`
- Test: `tests/test_ott2butkama_strategy_presence.py`
- Test: `tests/test_ott2butkama_signal_hooks.py`

- [ ] **Step 1: Create the candidate strategy file**

Create `strategies/jesse/Ott2butKAMA_RiskManaged25/__init__.py` as a full Jesse-runtime-compatible copy of `Ott2butKAMA_RiskManaged`, then change only:

```python
{'name': 'risk_per_trade', 'type': int, 'min': 1, 'max': 50, 'default': 25}
```

And update emitted strategy names so they consistently use:

```python
strategy="Ott2butKAMA_RiskManaged25"
```

- [ ] **Step 2: Run the targeted tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_ott2butkama_strategy_presence.py tests/test_ott2butkama_signal_hooks.py tests/test_sync_jesse_strategy.py -q
```

Expected: PASS.

### Task 3: Sync and export trade details for original vs RiskManaged25

**Files:**
- No new files required

- [ ] **Step 1: Sync the candidate into the runtime workspace**

Run:

```bash
PYTHONPATH=. ./.venv/bin/python3 -c "from scripts.sync_jesse_strategy import sync_strategy; sync_strategy('Ott2butKAMA_RiskManaged25')"
```

- [ ] **Step 2: Export original strategy trades**

Run:

```bash
source runtime/jesse_workspace/.venv/bin/activate
python3 scripts/export_backtest_trades.py \
  --strategy Ott2butKAMA \
  --symbol ETHUSDT \
  --timeframe 5m \
  --start 2026-03-05 \
  --end 2026-04-05
```

Expected: a readable terminal table for the original strategy.

- [ ] **Step 3: Export RiskManaged25 trades**

Run:

```bash
source runtime/jesse_workspace/.venv/bin/activate
python3 scripts/export_backtest_trades.py \
  --strategy Ott2butKAMA_RiskManaged25 \
  --symbol ETHUSDT \
  --timeframe 5m \
  --start 2026-03-05 \
  --end 2026-04-05
```

Expected: a readable terminal table for the `2.5%` candidate.

- [ ] **Step 4: Inspect worktree status**

Run:

```bash
git status --short
```

Expected: only the candidate strategy, touched tests, and plan/spec files for this work appear.

## Self-Review

- Spec coverage: The plan formalizes the `2.5%` candidate and produces trade-detail exports for both original and candidate strategies.
- Placeholder scan: All tasks contain exact file paths, concrete inserted values, and direct commands.
- Type consistency: The plan consistently uses `Ott2butKAMA_RiskManaged25` as the formal candidate name.
