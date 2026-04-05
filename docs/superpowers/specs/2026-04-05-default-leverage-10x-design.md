# Default Leverage 10x Design

## Background

The repository currently uses `2x` leverage as the default baseline in several places:

- backtest compare script defaults
- trade export script defaults
- Jesse runtime workspace config
- tests and docs that assume the default leverage baseline is `2x`

The user wants the repository's default leverage baseline to become `10x`.

This is not just one numeric change. If the repository changes the default leverage without updating the surrounding scripts, runtime config, tests, and documentation, the codebase becomes internally inconsistent.

## Goal

Change the repository's default leverage baseline from `2x` to `10x` in a consistent way.

## Scope

### In Scope

- Update script defaults that currently assume `2x`.
- Update the Jesse runtime config default leverage.
- Update active documentation that describes the default leverage baseline.
- Update tests that assert default leverage behavior.

### Out of Scope

- Changing strategy signal logic.
- Changing fixed-risk sizing formulas.
- Rewriting historical backtest artifacts already stored under `docs/backtests/`.

## Proposed Approach

Treat `10x` as the repository's new default experiment baseline.

This means:

1. CLI tools should default to `10` when the user does not pass `--leverage`
2. Jesse runtime config should use `10` as the default futures leverage baseline
3. tests that encode the old default should be updated
4. documentation should describe `10x` as the new default baseline where it currently names a default leverage value

## Affected Areas

### Script Defaults

Update these script defaults from `2` to `10`:

- `scripts/run_backtest_compare.py`
- `scripts/export_backtest_trades.py`

`scripts/run_single_backtest_case.py` currently requires `--leverage`, so it does not define a default and should remain explicit unless there is a separate reason to change it.

### Runtime Config

Update:

- `runtime/jesse_workspace/config.py`

So the runtime's default futures leverage baseline is also `10`.

### Tests

Update tests that currently hardcode the old default baseline for script defaults or config assumptions, especially around:

- compare command construction
- default CLI parsing expectations
- any tests that explicitly say the default leverage is `2`

Tests that pass a leverage explicitly do not need semantic changes.

### Documentation

Update active documentation to reflect that the repository baseline is now `10x` wherever it currently states or implies `2x` as the default.

Likely touch points include:

- `README.md`
- `docs/runbook.md`
- any active spec/plan or skill text that describes default leverage behavior rather than historical experiment outputs

## Acceptance Criteria

This work is complete when:

1. backtest compare defaults to `10x`
2. trade export defaults to `10x`
3. Jesse runtime config defaults to `10x`
4. affected tests pass with the new default baseline
5. active documentation no longer describes `2x` as the default baseline

## Risks and Mitigations

### Risk: historical artifacts still show `2x`

Mitigation:

- do not rewrite historical generated compare reports
- only update active defaults and active guidance

### Risk: changing defaults is mistaken for changing strategy logic

Mitigation:

- keep this step limited to defaults, config, tests, and docs
- do not change strategy signal or sizing logic in this work

## Follow-Up

After this change lands, future backtests and trade exports will naturally use `10x` unless the caller passes a different leverage explicitly.
