# Dynamic Dry-Run Signal Driver Design

## Background

The current `run_jesse_live_loop.py` is good enough to prove that the dry-run pipeline can emit signals and drive executor, but it still behaves like a fixed pseudo-state generator more than a true evolving signal driver.

That creates two problems:

1. signals do not change naturally with time and market state
2. terminal visibility is poor for real observation, especially when a position is open and the operator wants to know current floating PnL rather than just whether the process is alive

The user wants this script upgraded into a more realistic dry-run driver that:

- reacts to changing market data
- keeps running continuously
- prints useful one-line terminal summaries
- prioritizes floating PnL information while a position is open

## Goal

Upgrade `run_jesse_live_loop.py` from a fixed pseudo-state generator into a dynamic dry-run signal driver with terminal output that highlights current position profit and loss.

## Scope

### In Scope

- Make the signal-generation loop depend on changing runtime data rather than fixed hardcoded values.
- Print one-line terminal summaries each loop.
- Show current floating PnL while a position is open.
- Keep compatibility with the existing signal bridge and executor flow.

### Out of Scope

- Full portfolio accounting.
- Multi-position support.
- Rewriting the strategy itself.
- Building a dashboard or UI.

## Proposed Approach

Instead of hardcoding `price`, `cross_up`, `cross_down`, and related state, the loop should derive its current decision from changing data inputs each cycle.

The driver should maintain a minimal local position context for observability:

- whether there is an open position
- side
- quantity
- entry price

This local context is not meant to replace database truth. It exists to make the terminal output immediately useful while the operator watches the loop.

## Terminal Output Design

### When Flat

Print one concise line per loop showing:

- timestamp
- strategy
- symbol
- current price
- current bias/judgment
- action
- whether a new signal was emitted

Example:

```text
[2026-04-05T21:03:20+08:00] strategy=Ott2butKAMA symbol=ETHUSDT price=2488.1 position=flat bias=flat action=none emitted=no
```

### When In Position

Print one concise line per loop showing:

- timestamp
- strategy
- symbol
- side
- qty
- entry price
- current price
- floating PnL
- floating PnL percent
- action
- whether a new signal was emitted

Example:

```text
[2026-04-05T21:03:30+08:00] strategy=Ott2butKAMA symbol=ETHUSDT side=long qty=5.12 entry=2450.0 price=2488.1 pnl=+195.07 pnl_pct=+1.59% action=hold emitted=no
```

## Dynamic Signal Driver Requirements

The loop should no longer rely on fixed values like:

- `price = 2500.0`
- `cross_up = False`
- `cross_down = True`
- fixed `current_candle`

Instead, each cycle should derive the current signal state from evolving data.

The implementation may still use a lightweight internal driver rather than full Jesse live mode, but it must be data-driven rather than static.

## Minimal Position Context

The loop should track at least:

- `position_open`
- `position_side`
- `position_qty`
- `entry_price`

When price changes each cycle, it should compute:

- `pnl`
- `pnl_pct`

For longs:

```text
pnl = (current_price - entry_price) * qty
```

For shorts:

```text
pnl = (entry_price - current_price) * qty
```

## Integration Boundary

This enhancement should remain focused on `run_jesse_live_loop.py` and related tests. It should not require rewriting executor or the signal database schema.

## Acceptance Criteria

This work is complete when:

1. `run_jesse_live_loop.py` no longer depends on fixed static pseudo-state values for each cycle
2. the loop prints one-line summaries continuously
3. the flat-state summary shows price, bias, action, and emitted flag
4. the in-position summary shows floating PnL information
5. dry-run still emits signals into the existing bridge/executor path

## Risks and Mitigations

### Risk: terminal output becomes noisy

Mitigation:

- keep it to one line per loop
- avoid multi-line debug dumps in the first version

### Risk: local position context diverges from actual execution state

Mitigation:

- keep the first version lightweight and explicitly scoped for observability
- avoid pretending this local context is authoritative portfolio truth

### Risk: data-driven signal generation still depends on brittle Jesse runtime assumptions

Mitigation:

- prefer the smallest data-driven approach that can be tested directly
- avoid reintroducing unstable fixed pseudo-state hacks

## Follow-Up

Once this becomes stable, the next useful step would be event deduplication and more explicit live loop health/status reporting.
