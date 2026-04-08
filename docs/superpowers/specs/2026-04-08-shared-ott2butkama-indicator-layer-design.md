# Shared Ott2butKAMA Indicator Layer Design

## Background

The project has already started extracting a shared strategy core, but the current shared piece is still too narrow: only the final direction decision is shared. The actual indicator inputs that drive `Ott2butKAMA` are still produced separately in backtest strategy code and in dry-run approximation logic.

This means backtest and dry-run still do not truly operate on the same strategy state.

## Goal

Extract a shared indicator-input layer for `Ott2butKAMA` so that backtest and dry-run can derive direction decisions from the same underlying strategy features.

## Core Principle

The system should not only share the last decision step; it should share the indicator-derived state that the decision depends on.

## Proposed Shared Layer

The shared layer should compute the key ingredients of `Ott2butKAMA` strategy logic:

- OTT-derived values
- `cross_up`
- `cross_down`
- `chop` / RSI value
- `chop_upper_band`
- `chop_lower_band`

The dry-run and backtest paths should both consume these shared values.

## Why This Matters

As long as dry-run approximates `cross_up`, `cross_down`, and `chop` from simplified heuristics, it will continue to drift from backtest behavior even if the final `evaluate_direction()` function is shared.

The real source of inconsistency is not just the final decision function; it is the indicator state feeding that function.

## Proposed Architecture

### 1. Shared Indicator Module

Add a reusable module that accepts candle close prices and strategy parameters, and returns an `Ott2butKAMA` feature snapshot containing:

- current price
- OTT moving-average state
- OTT line state
- cross flags
- current chop/RSI value
- upper and lower chop bands

### 2. Shared Decision Module

The existing shared direction evaluator remains, but it should operate on values produced by the shared indicator layer.

### 3. Adapter Layers

- the Jesse strategy wrapper should use the shared indicator layer when practical
- dry-run should use the same indicator layer on market candles

## Acceptance Criteria

This work is complete when:

1. `Ott2butKAMA` indicator-derived state is available through a shared module
2. dry-run uses the shared indicator layer instead of heuristic approximations
3. the existing shared direction evaluator consumes the shared indicator-derived values
4. dry-run and backtest become materially closer in behavior because they now depend on the same underlying features

## Risks and Mitigations

### Risk: extracting indicator logic may accidentally change backtest behavior

Mitigation:

- preserve the original strategy wrapper and migrate incrementally
- compare outputs carefully through tests

### Risk: full fidelity with Jesse runtime is still not guaranteed

Mitigation:

- keep the scope honest: this step shares indicator logic and state derivation, not the full Jesse engine

## Follow-Up

Once indicator-layer sharing is complete, the next step is to reduce or eliminate the remaining dry-run-only logic so the strategy path becomes even more unified.
