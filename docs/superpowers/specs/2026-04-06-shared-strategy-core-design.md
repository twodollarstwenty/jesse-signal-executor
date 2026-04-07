# Shared Strategy Core Design

## Background

The project has now reached the point where the distinction between “strategy behavior” and “execution environment behavior” matters a lot. The user explicitly pointed out the core architectural risk: if backtest uses one logic path and dry-run uses another, then the two modes stop being meaningfully comparable.

This is exactly what has happened during the evolution of dry-run. The system became good at chain validation and observability, but strategy behavior in dry-run drifted away from the true strategy conditions used in backtests.

## Goal

Create a shared strategy core so that backtest and dry-run can rely on the same strategy-decision logic.

## Core Principle

There should be one canonical implementation of the strategy's directional decision logic.

That shared core should be used by:

- backtest execution
- dry-run execution
- future live-like execution layers

## Proposed Architecture

Split the system into three layers.

### 1. Strategy Core

One reusable evaluator that accepts:

- candle data
- strategy parameters
- current position state (if needed)

and returns a normalized strategy decision such as:

- `long`
- `short`
- `flat`

or an equivalent intermediate intent representation.

This layer should not:

- write to the database
- send notifications
- perform process control

### 2. Backtest Adapter

The backtest path should become a consumer of the shared strategy core.

Its responsibility is to:

- replay historical candles
- feed the core evaluator
- collect performance statistics

### 3. Dry-Run Adapter

The dry-run path should also consume the same shared strategy core.

Its responsibility is to:

- fetch or receive market candles
- feed the core evaluator
- normalize intent into legal actions given current position state
- emit those actions into the existing signal bridge

## Why This Matters

Without this architecture, the system will keep drifting into:

- backtest validates one thing
- dry-run tests another thing

At that point, dry-run becomes mainly a chain validator rather than a strategy validator.

The user has already noticed this mismatch.

## Suggested Shape For Ott2butKAMA

The first extracted shared strategy core should focus on the actual ingredients that define `Ott2butKAMA` behavior:

- OTT-derived state
- `cross_up` / `cross_down`
- `chop` / RSI filter behavior

This shared evaluator should be the only place where those conditions are implemented.

## Acceptance Criteria

This work is complete when:

1. one shared strategy core exists for `Ott2butKAMA`
2. backtest and dry-run both use that same core logic
3. dry-run no longer relies on a separate heuristic action model
4. strategy behavior across backtest and dry-run becomes qualitatively more consistent

## Risks and Mitigations

### Risk: extracting strategy logic without breaking existing backtests is delicate

Mitigation:

- extract the core in small pieces
- keep tests around both backtest and dry-run usage

### Risk: trying to make dry-run identical to backtest in one step creates too much refactor risk

Mitigation:

- separate the core evaluator first
- then migrate backtest and dry-run adapters onto it incrementally

## Follow-Up

Once a shared strategy core exists, later work can extend it to more strategies and support richer live-like execution adapters.
