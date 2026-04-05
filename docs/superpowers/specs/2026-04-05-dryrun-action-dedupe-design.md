# Dry-Run Action Dedupe Design

## Background

After switching dry-run price sourcing to Binance Futures REST, the terminal output became more realistic on the price side, but the current lightweight action mapping can still emit the same action repeatedly across consecutive loop iterations.

This makes the terminal noisy and makes the system feel less trustworthy, even when the underlying loop is functioning correctly.

## Goal

Reduce repeated identical action emission in the dry-run live loop by adding a minimal per-process action dedupe/throttle layer.

## Scope

### In Scope

- Prevent consecutive identical actions from being emitted repeatedly by the same `run_jesse_live_loop.py` process.
- Keep terminal summaries visible.
- Mark repeated identical actions as non-emitted in the summary.

### Out of Scope

- Database-level deduplication.
- Cross-process deduplication.
- Notification-layer deduplication.
- Full strategy redesign.

## Proposed Approach

Add a very small in-memory memory of the last emitted action inside `run_jesse_live_loop.py`.

Rules:

1. if the current loop action is `none`, do not emit
2. if the current loop action is the same as the last emitted action, do not emit
3. if the current loop action differs from the last emitted action, emit and update the remembered action

This should turn many repeated `emitted=yes` lines into `emitted=no` while preserving visibility of the current action recommendation.

## Example

Before:

```text
... action=open_short emitted=yes
... action=open_short emitted=yes
... action=open_short emitted=yes
```

After:

```text
... action=open_short emitted=yes
... action=open_short emitted=no
... action=open_short emitted=no
```

## Acceptance Criteria

1. repeated consecutive identical actions are not re-emitted every loop
2. terminal summaries still show the current action
3. the first occurrence of a new action still emits normally

## Follow-Up

If this helps but is still not enough, the next step should be stateful deduplication or a more realistic action decision model.
