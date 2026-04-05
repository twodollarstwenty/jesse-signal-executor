# Binance REST-Driven Dry-Run Design

## Background

The current dynamic dry-run signal driver is already better than the earlier fixed pseudo-state loop, but its price values are still internally generated rather than coming from the market. That means the terminal output is useful for process observability, but not trustworthy as a representation of current exchange price.

The user wants the dry-run view to feel closer to a real live environment, especially so that the terminal shows prices that are meaningfully aligned with the exchange.

## Goal

Upgrade dry-run so that its market input comes from Binance REST data rather than synthetic price generation.

## Scope

### In Scope

- Add a small Binance REST market-data fetch path.
- Use that data to drive `run_jesse_live_loop.py`.
- Keep one-line terminal summaries with floating PnL when in position.
- Keep the current signal bridge and executor flow.

### Out of Scope

- WebSocket market streaming.
- Multi-exchange support.
- Full live trading mode.
- Rewriting the strategy.

## Proposed Approach

Add a small REST market snapshot layer that fetches current data from Binance and feeds it into the dry-run signal driver.

The first version should favor reliability and simplicity over perfect real-time precision.

## Data Source Choice

The first version should use **Binance REST polling** rather than local synthetic prices or WebSocket streaming.

Reasoning:

- more realistic than the current synthetic loop
- simpler and more reliable than WebSocket streaming
- sufficient for an initial dry-run upgrade

## Market Snapshot

Each loop should fetch a minimal market snapshot containing at least:

- symbol
- current price
- timestamp
- latest candle data if required by the strategy driver

The implementation may use Binance public REST endpoints for price and/or recent klines.

## Driver Behavior

`run_jesse_live_loop.py` should no longer invent market price. Instead it should:

1. fetch a Binance market snapshot
2. derive the current strategy input from that snapshot
3. decide whether to emit an action or hold
4. print a one-line summary using the real market-derived price

## Terminal Output

The one-line summary format can remain the same structure, but the `price` field should now reflect the fetched Binance market value rather than a synthetic loop value.

### Flat Example

```text
[2026-04-05T21:33:20+08:00] strategy=Ott2butKAMA symbol=ETHUSDT price=2516.8 position=flat bias=long action=open_long emitted=yes
```

### In-Position Example

```text
[2026-04-05T21:33:30+08:00] strategy=Ott2butKAMA symbol=ETHUSDT side=long qty=1.0 entry=2508.2 price=2516.8 pnl=+8.60 pnl_pct=+0.34% action=hold emitted=no
```

## Polling Frequency

The first version should keep a simple poll interval, such as using the existing dry-run loop interval (`10s` by default), rather than introducing a second independent scheduler.

## Safety Requirements

- If Binance REST fetch fails temporarily, dry-run should fail safely or skip emission for that cycle rather than inventing a fake price.
- The failure should be visible in logs and terminal output.
- The core executor and database schema should remain unchanged.

## Integration Boundary

The implementation should mainly touch:

- `run_jesse_live_loop.py`
- a small Binance REST fetch helper module or script
- related tests

It should not require large changes to executor, signal schema, or WeCom notifications.

## Acceptance Criteria

This work is complete when:

1. dry-run market price comes from Binance REST data
2. terminal output shows market-derived prices
3. in-position terminal output still shows floating PnL
4. dry-run continues to emit signals into the current bridge/executor path
5. failures in price fetch are handled visibly and safely

## Risks and Mitigations

### Risk: REST polling is not perfectly real-time

Mitigation:

- accept this as a first-version tradeoff for reliability and simplicity

### Risk: external API failure causes loop instability

Mitigation:

- handle fetch errors explicitly and avoid synthetic fallback that hides the failure

### Risk: strategy still is not truly running inside full Jesse live mode

Mitigation:

- keep scope honest: this step improves the realism of market input, not the full runtime model

## Follow-Up

If this version works well, the next logical step would be Binance WebSocket-driven dry-run or a deeper Jesse-native live/paper integration.
