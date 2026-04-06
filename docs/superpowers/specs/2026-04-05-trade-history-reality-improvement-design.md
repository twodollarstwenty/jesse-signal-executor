# Trade History Reality Improvement Design

## Background

The first version of the trade-history panel is now available, but several fields are still placeholders or inconsistent:

- realized PnL is not yet meaningfully populated per row
- fee is always `--`
- role is always `dry-run`
- some rows can still show `price = 0.0`

The panel shape is now correct, so the next step is to improve the realism of the data it shows without pretending to be a full exchange-grade execution ledger.

## Goal

Improve the trade-history panel so that its data is more believable and more useful for operator review.

## Scope

### In Scope

- Per-row realized PnL for close rows when it can be inferred from current dry-run execution history.
- Better handling of `price = 0` cases.
- First-version fee estimation if a simple rule is acceptable.
- More explicit role labeling.

### Out of Scope

- Exact exchange-grade fee accounting.
- Real maker/taker classification.
- Full trade ledger redesign.

## Proposed Approach

Keep the panel structure the same, but improve the values through a best-effort inference model.

## Target Improvements

### 1. Realized PnL

For `close_long` and `close_short`, compute realized PnL by pairing each close event with the most recent open event for the same direction in the dry-run event stream.

This should follow the same first-version pairing philosophy already used in the dry-run account summary.

### 2. Zero Price Handling

If a row has `price = 0`, do not display it as if it were a real execution price.

Preferred first-version behavior:

- replace with `--`
- or skip rows that cannot produce a meaningful execution price

The panel should not display `0.0` as though it were a valid market execution.

### 3. Fee Field

First-version options:

- keep `--`
- or estimate with a fixed fee rate if the repository already assumes one for backtests

Recommendation:

- first use an explicit estimated fee model if it can be tied to current known assumptions
- otherwise keep `--` and do not fake precision

### 4. Role Field

The panel should not pretend to know `吃单方 / 挂单方` if no real fill source exists.

Recommendation:

- keep `dry-run`

This is more honest than fabricating maker/taker labels.

## Acceptance Criteria

1. close rows can show a meaningful realized PnL when pairing is possible
2. rows no longer display `price = 0.0` as if it were a valid execution price
3. fee handling is explicit and not misleading
4. role labeling remains honest for dry-run

## Follow-Up

If this panel becomes important for operational review, the long-term solution is a dedicated dry-run trade ledger with explicit fill records, realized PnL, fee fields, and execution metadata.
