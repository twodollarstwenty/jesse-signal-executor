# WeCom Webhook Notifications Design

## Background

The project can already:

- run backtests
- run host-level dry-run continuously
- record signals and execution decisions in PostgreSQL
- produce validation summaries

But the operator still has to manually check scripts, logs, database tables, or generated reports to know what happened.

The user wants the system to proactively notify them via an Enterprise WeCom group robot webhook about both:

- dry-run execution activity
- backtest summary results

## Goal

Add a first-version notification layer that sends webhook messages for:

1. dry-run execution events and abnormal dry-run states
2. backtest summary results

## Scope

### In Scope

- Webhook-based group notifications.
- Dry-run execution notifications.
- Dry-run abnormal-state notifications.
- Backtest summary notifications.
- A lightweight notification sender/formatter layer inside the repository.

### Out of Scope

- SMTP email sending.
- UI or dashboard notifications.
- A full event bus or message queue.
- Historical replay of all past events.

## Channel

The first version should target **Enterprise WeCom robot webhooks** directly.

Reasoning:

- this matches the user's chosen delivery channel
- WeCom robot payloads are simple and stable for text messages
- it still leaves room for a later abstraction if other channels are needed

## Notification Categories

### 1. Dry-Run Execution Notifications

Send notifications when the system records new execution decisions, especially:

- `execute`
- `ignored`
- `rejected`

These notifications should include enough context to tell the operator:

- strategy
- symbol
- action
- decision
- reason if available
- timestamp

### 2. Dry-Run Abnormal-State Notifications

Send notifications when dry-run health indicates trouble, for example:

- `stale`
- startup failure
- repeated stop/fail state

These should be concise and operationally useful.

### 3. Backtest Summary Notifications

After a backtest compare run completes successfully, send a summary notification containing:

- baseline strategy
- candidate strategy
- symbol
- timeframe
- window
- trades
- win rate
- net profit
- max drawdown

This should be a short summary, not a full report body.

## Proposed Architecture

### Notification Sender

Add a small WeCom notification sender module that:

- reads a configured WeCom webhook URL from environment variables
- posts a WeCom-compatible JSON payload to the webhook
- no-ops cleanly if notifications are disabled or webhook is unset

### Notification Formatter

Add formatting helpers that convert internal events into readable notification messages.

### Dry-Run Notifier

Implement a lightweight notifier path for dry-run by polling recent `execution_events` and/or health state.

This can be done as:

- a dedicated script run in a loop, or
- a lightweight hook from existing scripts where appropriate

The first version should prefer the smallest approach that does not destabilize the existing execution flow.

### Backtest Notifier

Hook notification sending into `scripts/run_backtest_compare.py` after successful compare-report generation.

This is a natural integration point because the script already has all summary metrics assembled.

## Configuration

Suggested environment variables:

- `WECOM_BOT_WEBHOOK`
- `NOTIFY_ENABLED`
- `NOTIFY_DRYRUN_ENABLED`
- `NOTIFY_BACKTEST_ENABLED`

The system should fail safe:

- if webhook is not configured, continue normal operation without notification
- notification failure must not break backtest execution or dry-run execution

## Message Shape

### Dry-Run Execution Example

```json
{
  "msgtype": "text",
  "text": {
    "content": "[DRY-RUN]\nstrategy: Ott2butKAMA_RiskManaged25\nsymbol: ETHUSDT\naction: open_long\ndecision: execute\ntime: 2026-04-05T12:35:00+08:00\nreason: N/A"
  }
}
```

### Dry-Run Error Example

```json
{
  "msgtype": "text",
  "text": {
    "content": "[DRY-RUN ALERT]\ncomponent: jesse-dryrun\nstate: stale\ntime: 2026-04-05T12:40:00+08:00\nnext: check runtime/dryrun/logs/jesse-dryrun.log"
  }
}
```

### Backtest Summary Example

```json
{
  "msgtype": "text",
  "text": {
    "content": "[BACKTEST]\nbaseline: Ott2butKAMA\ncandidate: Ott2butKAMA_RiskManaged25\nsymbol: ETHUSDT\ntimeframe: 5m\nwindow: 2025-10-05 -> 2026-04-05\ntrades: 93\nwin_rate: 43.01%\nnet_profit: 94.26%\nmax_drawdown: -20.12%"
  }
}
```

## Safety Requirements

- Notification sending must never block or fail the core trading/dry-run path irrecoverably.
- Webhook errors must be logged or surfaced lightly, but not crash core operations.
- Duplicate dry-run notifications should be minimized by tracking the most recent delivered event or polling window.

## Acceptance Criteria

This work is complete when:

1. WeCom webhook notifications can be enabled through environment variables
2. a completed backtest compare run can emit a summary notification
3. dry-run execution events can emit notifications
4. dry-run abnormal states can emit notifications
5. notification failure does not break the main scripts

## Risks and Mitigations

### Risk: too many dry-run notifications

Mitigation:

- start with execution events and abnormal states only
- avoid sending low-value heartbeat-style messages

### Risk: notifications become tightly coupled to execution logic

Mitigation:

- keep a small, isolated sender/formatter layer
- integrate at script boundaries or polling boundaries where possible

### Risk: WeCom text messages are too plain

Mitigation:

- start with text because it is the most reliable first version
- add markdown/card formatting only after delivery is proven stable

## Follow-Up

Future enhancements can include:

1. email delivery
2. per-strategy notification routing
3. daily summary digests
4. richer WeCom markdown/card formatting
