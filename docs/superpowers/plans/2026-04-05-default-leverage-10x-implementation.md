# Default Leverage 10x Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Change the repository's default leverage baseline from `2x` to `10x` in code defaults, runtime config, tests, and active documentation.

**Architecture:** Keep the change narrow. Update only the places that define or assert the repository default leverage baseline: script CLI defaults, runtime config defaults, tests that encode those defaults, and active docs that describe the baseline. Do not change strategy signal logic or fixed-risk sizing formulas.

**Tech Stack:** Python 3.13, pytest, Markdown, Jesse runtime config

---

## File Structure

- Modify: `scripts/run_backtest_compare.py`
  - Change default CLI leverage from `2` to `10`.
- Modify: `scripts/export_backtest_trades.py`
  - Change default CLI leverage from `2` to `10`.
- Modify: `runtime/jesse_workspace/config.py`
  - Change default futures leverage from `2` to `10`.
- Modify: `tests/test_run_backtest_compare.py`
  - Update expectations that rely on the default leverage baseline.
- Modify: `README.md`
  - Update active wording where the repository baseline currently implies `2x`.
- Modify: `docs/runbook.md`
  - Update active wording where the repository baseline currently implies `2x`.

### Task 1: Add failing tests for the new 10x defaults

**Files:**
- Modify: `tests/test_run_backtest_compare.py`

- [ ] **Step 1: Add a failing default-leverage parser test**

Append this test to `tests/test_run_backtest_compare.py`:

```python
def test_parse_args_defaults_leverage_to_10(monkeypatch):
    from scripts.run_backtest_compare import parse_args

    monkeypatch.setattr(
        "sys.argv",
        [
            "run_backtest_compare.py",
            "--symbol",
            "ETHUSDT",
            "--timeframe",
            "5m",
            "--start",
            "2026-03-05",
            "--end",
            "2026-04-05",
            "--baseline-strategy",
            "Ott2butKAMA",
            "--candidate-strategy",
            "Ott2butKAMA_RiskManaged25",
        ],
    )

    args = parse_args()

    assert args.leverage == 10
```

- [ ] **Step 2: Run the targeted test to verify it fails**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_run_backtest_compare.py::test_parse_args_defaults_leverage_to_10 -q
```

Expected: FAIL because the default leverage is still `2`.

### Task 2: Update code defaults to 10x

**Files:**
- Modify: `scripts/run_backtest_compare.py`
- Modify: `scripts/export_backtest_trades.py`
- Modify: `runtime/jesse_workspace/config.py`

- [ ] **Step 1: Change compare-script default leverage**

In `scripts/run_backtest_compare.py`, change:

```python
parser.add_argument("--leverage", type=int, default=2)
```

to:

```python
parser.add_argument("--leverage", type=int, default=10)
```

- [ ] **Step 2: Change trade-export default leverage**

In `scripts/export_backtest_trades.py`, change:

```python
parser.add_argument("--leverage", type=int, default=2)
```

to:

```python
parser.add_argument("--leverage", type=int, default=10)
```

- [ ] **Step 3: Change Jesse runtime config default leverage**

In `runtime/jesse_workspace/config.py`, change the futures leverage default from `2` to `10`.

- [ ] **Step 4: Run targeted tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_run_backtest_compare.py -q
```

Expected: PASS.

### Task 3: Update active documentation wording

**Files:**
- Modify: `README.md`
- Modify: `docs/runbook.md`

- [ ] **Step 1: Update README leverage wording**

Adjust README wording anywhere the active default leverage baseline is described or implied so it reflects `10x`, not `2x`.

- [ ] **Step 2: Update runbook leverage wording**

Adjust `docs/runbook.md` where the active default leverage baseline is described or implied so it reflects `10x`, not `2x`.

- [ ] **Step 3: Inspect the doc diff**

Run:

```bash
git diff -- README.md docs/runbook.md
```

Expected: only leverage-baseline wording changes.

### Task 4: Final verification

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

Expected: only the intended default-leverage files appear.

## Self-Review

- Spec coverage: The plan covers script defaults, runtime config, affected tests, and active docs.
- Placeholder scan: All tasks include exact file paths, explicit changed values, and direct commands.
- Type consistency: The plan consistently treats `10x` as the new repository default baseline.
