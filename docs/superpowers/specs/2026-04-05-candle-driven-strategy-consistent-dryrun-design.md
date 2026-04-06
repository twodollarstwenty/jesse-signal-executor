# Candle-Driven Strategy-Consistent Dry-Run Design

## Background

The current dry-run path is useful as a system-chain validator, but the user correctly pointed out its limitation: if the action logic is not truly aligned with the backtest strategy logic, then the dry-run is not very useful for judging how the strategy behaves in live-like conditions.

The next step is therefore to move dry-run closer to the strategy semantics used in backtests.

## Goal

Make dry-run decision generation as consistent as practical with the backtest strategy logic by driving it from real market candles rather than lightweight price-to-action mapping.

## Scope

### In Scope

- Use real Binance market candles as dry-run input.
- Evaluate strategy conditions from candle data instead of direct price mapping.
- Keep the existing signal bridge and executor flow.
- Preserve current observability features (terminal summaries, notifications, account summary, panel scripts).

### Out of Scope

- Full native Jesse live/paper engine integration.
- WebSocket streaming in the first version.
- Multi-exchange support.

## Proposed Approach

Use Binance REST klines as the market-input source and evaluate strategy conditions from recent candles each loop.

This keeps the dry-run path close to the backtest logic while remaining far simpler than a full live Jesse engine.

## Core Principle

The dry-run should converge on this property:

- given comparable candle input, the dry-run should produce a qualitatively similar action pattern to the backtest strategy

That does not mean identical results at every timestamp, but it should avoid the obviously artificial behavior produced by the current lightweight action mapping.

## Data Source

The first version should use:

- Binance Futures REST klines

The loop should fetch enough recent candles to compute the strategy's indicators and signal conditions.

## Driver Model

Each cycle should:

1. fetch recent candles for the symbol and timeframe
2. build a strategy evaluation context from those candles
3. compute the same broad signal conditions that matter in backtest
4. emit a new action only when strategy conditions justify it

## Strategy Consistency Target

The current strategy family (`Ott2butKAMA` and its variants) relies on:

- OTT-derived state
- RSI/chop filtering
- directional open and close conditions

The candle-driven dry-run should evaluate those same conditions directly from fresh candle data rather than an arbitrary modulo/price mapping.

## Terminal Output

Keep the current one-line summaries, but now they should describe a more trustworthy strategy state because the action comes from candle-based logic.

## Acceptance Criteria

This work is complete when:

1. dry-run market input comes from recent Binance Futures candles
2. dry-run action generation is driven by candle-based strategy logic
3. the observed action pattern is materially more plausible than the old lightweight mapping
4. the existing signal bridge and executor flow still work

## Risks and Mitigations

### Risk: REST candle polling is still coarser than a true live engine

Mitigation:

- accept this as a first-version tradeoff for strategy consistency without full live-mode complexity

### Risk: building the full strategy state outside Jesse becomes brittle

Mitigation:

- keep the first version focused on the minimum strategy conditions required for plausible open/close behavior
- avoid pretending this is full native Jesse live integration

## Follow-Up

If this version proves useful, the next step can be a deeper Jesse-native live/paper integration or WebSocket candle streaming.
