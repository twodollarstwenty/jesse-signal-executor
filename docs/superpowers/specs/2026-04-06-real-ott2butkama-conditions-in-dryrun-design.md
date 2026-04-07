# Real Ott2butKAMA Conditions In Dry-Run Design

## Background

The current dry-run has gradually improved from a synthetic loop into a candle-driven loop, but its decision logic is still only a rough proxy. Earlier iterations were too reactive; newer iterations can become too passive. This is happening because the loop is still not using the actual strategy conditions that were validated in backtests.

The user has repeatedly pointed out the core issue: if the dry-run is not using the real strategy conditions, then it is not very meaningful as a strategy-validation environment.

## Goal

Make dry-run decision generation use the core `Ott2butKAMA` strategy conditions rather than a simplified heuristic.

## Scope

### In Scope

- Use real `Ott2butKAMA` condition components in dry-run evaluation.
- Compute signals from candle-driven indicator state.
- Preserve the current dry-run execution chain (signal bridge -> executor -> summaries/logs).

### Out of Scope

- Full native Jesse live mode integration.
- Multi-exchange support.
- Full real-time streaming engine in the first version.

## Core Strategy Conditions To Reuse

The dry-run should move toward using these same broad conditions from `Ott2butKAMA`:

- OTT-derived state
- `cross_up` / `cross_down`
- `chop` / RSI filter behavior

That means the dry-run should not just look at the last three close prices. It should evaluate the same kinds of conditions the backtest strategy actually relies on.

## Proposed Approach

Create a dry-run evaluation layer that:

1. fetches recent Binance Futures candles
2. computes the indicator inputs needed for `Ott2butKAMA`
3. derives a directional intent from the real strategy conditions
4. normalizes that intent into a legal action based on current position state

## Architectural Principle

The strategy's directional logic should be reused; the dry-run's executor and observability layers should remain separate.

This keeps the project architecture understandable:

- strategy logic decides intent
- dry-run controller normalizes intent into legal action
- executor remains the execution decision sink

## Acceptance Criteria

This work is complete when:

1. dry-run no longer uses the simplistic 3-close heuristic as its main decision rule
2. dry-run intent is derived from real `Ott2butKAMA`-style conditions
3. the resulting action cadence is qualitatively closer to the backtest strategy behavior
4. existing dry-run execution, summaries, and notification paths continue to work

## Follow-Up

If this version is still not close enough to backtest behavior, the next step should be a deeper Jesse-native runtime integration rather than more heuristic tuning.
