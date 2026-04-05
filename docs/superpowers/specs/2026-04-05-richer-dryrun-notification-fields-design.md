# Richer Dry-Run Notification Fields Design

## Background

The first version of dry-run notifications already sends the core execution information:

- strategy
- symbol
- action
- decision
- a single timestamp
- reason

But that message shape is still ambiguous in practice because the operator cannot easily distinguish:

- when the signal originally occurred
- when executor recorded the execution event
- what price was attached to the signal
- whether a close action refers to a long or short position

The user wants the notification content to be clearer without broadening the scope into deduplication, email delivery, or formatting redesign.

## Goal

Enhance dry-run notification messages so they show the most useful execution context directly in the WeCom text message.

## Scope

### In Scope

- Add `signal_time` to the dry-run execution notification.
- Rename the existing generic `time` field to `execution_time`.
- Extract `price` from `signal_events.payload_json` when present.
- Extract `position_side` from `signal_events.payload_json` when present.

### Out of Scope

- Deduplication.
- Notification state tracking.
- Email delivery.
- Markdown/card formatting.
- Schema changes.

## Proposed Message Shape

Current notification shape is roughly:

```text
[DRY-RUN]
strategy: Ott2butKAMA
symbol: ETHUSDT
action: close_long
decision: execute
time: 2026-04-05T17:13:50.964454+08:00
reason: N/A
```

The enhanced shape should become:

```text
[DRY-RUN]
strategy: Ott2butKAMA
symbol: ETHUSDT
action: close_long
decision: execute
signal_time: 2024-04-04T08:00:00+08:00
execution_time: 2026-04-05T17:13:50.964454+08:00
price: 2500.0
position_side: long
reason: N/A
```

## Data Source

The notifier already joins `execution_events` to `signal_events` via `signal_id`. The enhancement should simply extend the query and formatting layer so the message can include:

- `signal_events.signal_time`
- `execution_events.created_at`
- `signal_events.payload_json`

## Field Rules

- `signal_time`: use `signal_events.signal_time`
- `execution_time`: use `execution_events.created_at`
- `price`: use `payload_json["price"]` if present, else `N/A`
- `position_side`: use `payload_json["position_side"]` if present, else `N/A`
- `reason`: keep the current behavior unless a better explicit reason is present

## Acceptance Criteria

This work is complete when:

1. dry-run notifications include `signal_time`
2. dry-run notifications include `execution_time`
3. dry-run notifications include `price` when present
4. dry-run notifications include `position_side` when present
5. the notifier remains backward-safe when payload fields are missing

## Follow-Up

If this message shape proves useful, the next natural step is deduplication and stateful “new events only” delivery.
