# Persistent Position State Design

## Background

The repository currently keeps a `position_state` table, but executor only uses it as a direction marker. It writes:

- `side`
- `qty = 0`
- `entry_price = 0`

That is enough for state-machine direction control, but not enough for trustworthy terminal position display.

As a result, terminal output cannot rely on `position_state` for stable `entry_price` and `qty`, which is why `run_jesse_live_loop.py` had to fall back to transient local position display.

## Goal

Upgrade persistent position state so it stores enough information to support stable dry-run position display.

## Scope

### In Scope

- Persist meaningful `qty`
- Persist meaningful `entry_price`
- Keep `side` authoritative
- Allow terminal output to display a stable persistent position view

### Out of Scope

- Full account equity tracking
- Historical realized PnL ledger
- Multi-position support

## Proposed Approach

Use the existing `position_state` table as the source of truth for the current dry-run position, but begin populating it with real values rather than zeros.

The executor already writes rows into `position_state` when a state transition is executed. That path should be extended so it stores:

- `side`
- `qty`
- `entry_price`

based on the triggering signal and the transition outcome.

## Data Model Intent

### Open Long / Open Short

When executor executes an opening signal:

- `side` becomes `long` or `short`
- `qty` is taken from signal payload if available, else a default placeholder value consistent with current dry-run behavior
- `entry_price` is taken from signal payload `price`

### Close Long / Close Short

When executor executes a closing signal:

- `side` becomes `flat`
- `qty` becomes `0`
- `entry_price` becomes `0`

### Ignored / Rejected

When a signal is `ignored` or `rejected`, persistent position state should not be changed.

## Signal Payload Requirement

To support this, the emitted signal payload must contain enough information for executor to persist a meaningful position state, especially:

- `price`
- `position_side` when relevant
- optional `qty` if available

If `qty` is not available from the signal source yet, the first version may persist a known placeholder quantity consistent with the local dry-run driver, but this should be explicit and limited.

## Executor Changes

The main executor change is not to the decision matrix, but to the `upsert_position_side()` behavior.

It should evolve from:

- writing only side with zero qty and zero entry price

to:

- writing a full current-position snapshot when an `execute` decision changes position state

## Terminal Display Impact

Once `position_state` contains real `qty` and `entry_price`, `run_jesse_live_loop.py` can safely display:

- stable `side`
- stable `entry_price`
- stable `qty`
- floating PnL computed from current market price

This solves the current operator confusion where `entry` appears to jump between lines.

## Acceptance Criteria

This work is complete when:

1. `position_state` rows contain meaningful `side`, `qty`, and `entry_price`
2. open executions write a non-zero `entry_price`
3. close executions reset persistent position state to flat/zero
4. ignored/rejected signals do not mutate position state
5. terminal output can reliably use `position_state` as its display source

## Risks and Mitigations

### Risk: payload shape is not rich enough

Mitigation:

- use `price` immediately
- if `qty` is not yet available, carry a temporary explicit placeholder until signal payloads are enriched

### Risk: persistent state and signal semantics drift apart

Mitigation:

- limit updates to `execute` transitions only
- keep the decision matrix unchanged

## Follow-Up

Once persistent position state is correct, a later step can add richer dry-run summaries such as realized/unrealized PnL and account-equity views.
