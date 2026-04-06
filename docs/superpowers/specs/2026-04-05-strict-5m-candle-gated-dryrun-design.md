# Strict 5m Candle-Gated Dry-Run Design

## Background

The current candle-driven dry-run is already a major improvement over the earlier price-mapped version, but it still evaluates actions on every loop iteration. That means it can react multiple times within the life of a single 5-minute candle, which does not align well with a strategy that is backtested on `5m` candles.

The user correctly asked whether the current dry-run behavior is really in `5m` mode. The honest answer is: not yet.

## Goal

Make dry-run evaluate strategy actions only when a **new 5-minute candle** is available.

## Scope

### In Scope

- Gate strategy evaluation on new 5m candle boundaries.
- Prevent repeated action evaluation within the same candle.
- Keep the current market-data polling approach.
- Preserve existing signal bridge and executor flow.

### Out of Scope

- WebSocket streaming.
- Full native Jesse live engine integration.
- Strategy redesign.

## Proposed Approach

Continue polling Binance Futures REST klines, but add one strict rule:

- only evaluate and emit strategy actions when the latest candle timestamp changes

This means the loop may still wake up every few seconds, but most iterations will simply observe that the current 5m candle is still the same and skip action evaluation.

## Desired Behavior

### Same Candle

If the latest 5m candle timestamp is unchanged from the last processed candle:

- do not compute a new strategy action
- do not emit a new signal
- optionally print a light status line such as “等待新 5m K 线”

### New Candle

If the latest 5m candle timestamp is newer than the last processed candle:

- compute the strategy state from candle data
- evaluate the action once
- emit if appropriate
- remember this candle timestamp as processed

## Why This Matters

This change moves dry-run closer to the backtest regime by aligning the decision cadence with the strategy timeframe.

It will reduce:

- rapid repeated decisions
- action oscillation within one candle
- the feeling that dry-run is “too fast” compared to a 5m backtest

## Acceptance Criteria

This work is complete when:

1. dry-run only evaluates actions when a new 5m candle is observed
2. same-candle iterations do not emit new actions
3. terminal output makes it clear when the loop is waiting for the next candle
4. the existing signal bridge and executor flow remain unchanged

## Follow-Up

If this works well, later steps can refine the actual strategy condition evaluation further to match backtest logic more closely.
