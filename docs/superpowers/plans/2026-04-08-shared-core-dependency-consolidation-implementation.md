# Shared Core Dependency Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate shared strategy-core dependencies into a stable package boundary so backtest and dry-run can import the shared core consistently.

**Architecture:** Move the reusable indicator dependency path into `strategies/shared/`, update the shared feature builder to depend only on stable shared imports, then extend strategy sync so runtime workspace gets the full shared subtree. Verify both backtest and dry-run import paths after the move.

**Tech Stack:** Python 3.13, pytest, shared strategy modules, runtime sync script

---

## File Structure

- Create: `strategies/shared/custom_indicators_ottkama/`
  - Shared package home for the reusable indicator dependency.
- Modify: `strategies/shared/ott2butkama_features.py`
  - Use stable shared-package imports instead of loose runtime imports.
- Modify: `scripts/sync_jesse_strategy.py`
  - Sync the entire shared package subtree into runtime workspace.
- Modify: `tests/test_sync_jesse_strategy.py`
  - Verify shared subtree sync includes indicator support packages.
- Modify: `tests/test_ott2butkama_features.py`
  - Verify the feature builder still works after import consolidation.

### Task 1: Add failing tests for shared dependency consolidation

**Files:**
- Modify: `tests/test_sync_jesse_strategy.py`
- Modify: `tests/test_ott2butkama_features.py`

- [ ] **Step 1: Add a failing sync-subtree test**

Append this test to `tests/test_sync_jesse_strategy.py`:

```python
def test_sync_strategy_copies_shared_indicator_package_subtree(tmp_path, monkeypatch):
    import scripts.sync_jesse_strategy as module

    monkeypatch.setattr(module, "ROOT", tmp_path)

    strategy_source = tmp_path / "strategies" / "jesse" / "Ott2butKAMA"
    strategy_source.mkdir(parents=True)
    (strategy_source / "__init__.py").write_text("# strategy")

    shared_core = tmp_path / "strategies" / "shared"
    shared_core.mkdir(parents=True)
    (shared_core / "ott2butkama_core.py").write_text("CORE = True")
    (shared_core / "ott2butkama_features.py").write_text("FEATURES = True")

    shared_indicator_pkg = shared_core / "custom_indicators_ottkama"
    shared_indicator_pkg.mkdir()
    (shared_indicator_pkg / "__init__.py").write_text("INDICATOR = True")

    for directory_name in ("custom_indicators_ottkama", "custom_indicators"):
        source = tmp_path / "strategies" / "jesse" / directory_name
        source.mkdir(parents=True)
        (source / "__init__.py").write_text("# indicator")

    module.sync_strategy("Ott2butKAMA")

    runtime_pkg = tmp_path / "runtime" / "jesse_workspace" / "strategies" / "shared" / "custom_indicators_ottkama"
    assert (runtime_pkg / "__init__.py").exists()
```

- [ ] **Step 2: Add a failing shared-feature import-path test**

Append this test to `tests/test_ott2butkama_features.py`:

```python
def test_build_feature_state_imports_indicator_from_shared_package(monkeypatch):
    import importlib
    import sys
    import types

    fake_talib = types.SimpleNamespace(RSI=lambda closes, length: [50.0, 55.0, 60.0, 65.0])
    fake_ott_value = types.SimpleNamespace(mavg=[10.0, 10.0, 10.0, 11.0], ott=[10.0, 10.0, 10.0, 10.5])
    fake_indicator_pkg = types.SimpleNamespace(ott=lambda closes, ott_len, ott_percent, ma_type="kama", sequential=True: fake_ott_value)

    monkeypatch.setitem(sys.modules, "talib", fake_talib)
    monkeypatch.setitem(sys.modules, "strategies.shared.custom_indicators_ottkama", fake_indicator_pkg)

    module = importlib.import_module("strategies.shared.ott2butkama_features")

    state = module.build_feature_state(
        closes=[2500.0, 2510.0, 2520.0, 2530.0],
        ott_len=36,
        ott_percent=5.4,
        chop_rsi_len=17,
        chop_bandwidth=144,
    )

    assert state["cross_up"] is True
```

- [ ] **Step 3: Run the targeted tests to verify they fail**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_sync_jesse_strategy.py tests/test_ott2butkama_features.py -q
```

Expected: FAIL because the shared package subtree and imports are not yet consolidated.

### Task 2: Consolidate the shared package boundary

**Files:**
- Create: `strategies/shared/custom_indicators_ottkama/__init__.py`
- Modify: `strategies/shared/ott2butkama_features.py`
- Modify: `scripts/sync_jesse_strategy.py`

- [ ] **Step 1: Create the shared indicator package**

Create `strategies/shared/custom_indicators_ottkama/__init__.py` by moving or copying the reusable indicator package entrypoint into the shared package boundary.

- [ ] **Step 2: Update the feature builder import**

Change `strategies/shared/ott2butkama_features.py` so it imports from:

```python
from strategies.shared import custom_indicators_ottkama as cta
```

instead of importing a loose top-level `custom_indicators_ottkama` module.

- [ ] **Step 3: Update runtime sync**

Extend `scripts/sync_jesse_strategy.py` so syncing a strategy also copies the full `strategies/shared/` subtree into:

```text
runtime/jesse_workspace/strategies/shared/
```

### Task 3: Verify runtime import stability

**Files:**
- No new files required

- [ ] **Step 1: Run targeted tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_sync_jesse_strategy.py tests/test_ott2butkama_features.py tests/test_ott2butkama_core.py -q
```

Expected: PASS.

- [ ] **Step 2: Sync the strategy into runtime workspace**

Run:

```bash
PYTHONPATH=. ./.venv/bin/python3 -c "from scripts.sync_jesse_strategy import sync_strategy; sync_strategy('Ott2butKAMA')"
```

- [ ] **Step 3: Re-run a one-month backtest**

Run:

```bash
source runtime/jesse_workspace/.venv/bin/activate
PYTHONPATH=. python3 scripts/run_backtest_compare.py \
  --symbol ETHUSDT \
  --timeframe 5m \
  --start 2026-03-08 \
  --end 2026-04-08 \
  --baseline-strategy Ott2butKAMA \
  --candidate-strategy Ott2butKAMA
```

Expected: shared-core imports no longer break runtime backtest.

- [ ] **Step 4: Re-run a fresh dry-run startup**

Run:

```bash
make dryrun-reset-up
```

Expected: shared-core imports no longer break dry-run startup.

### Task 4: Full verification

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

Expected: only the shared package consolidation files appear.

## Self-Review

- Spec coverage: The plan consolidates shared dependencies into a stable package and verifies both runtime sync and imports.
- Placeholder scan: Tasks include exact files, import paths, and commands.
- Type consistency: The plan keeps the shared package boundary explicit and avoids ad hoc runtime-only imports.
