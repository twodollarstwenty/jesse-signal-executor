# Live Signal WeCom Notification Design

## Goal

Send an Enterprise WeCom notification immediately when the live signal pipeline emits an open or close trading signal, without changing signal persistence behavior or waiting for executor results.

## Scope

### In Scope

- Notify on `open_long`, `open_short`, `close_long`, and `close_short`.
- Reuse the existing WeCom webhook sender in `apps/notifications/wecom.py`.
- Trigger notifications from the shared signal emission path.
- Keep notifications best-effort so signal persistence remains the primary behavior.
- Add focused tests for the new notification behavior.

### Out of Scope

- Notifications for executor success, failure, or rejection.
- Polling scripts or background notification workers.
- Database schema changes.
- Rich media or markdown WeCom messages.

## Approach

Hook the notification into `apps/signal_service/jesse_bridge/emitter.py::emit_signal()` after `insert_signal(...)` succeeds.

This is the narrowest correct integration point because all persisted live trading signals already pass through this function. By placing the notification here, open and close events are covered consistently without coupling the behavior to `scripts/run_jesse_live_loop.py` or introducing a second watcher process.

Only the four trading actions listed in scope should notify. Any other action values continue to be persisted without sending a WeCom message.

## Message Shape

The WeCom text message should use a compact Chinese format:

```text
[交易信号]
策略: Ott2butKAMA
交易对: ETHUSDT
周期: 5m
动作: 开多
信号时间: 2026-04-12T10:35:00Z
价格: 2521.4
仓位方向: long
来源: jesse
```

Field rules:

- `策略`: `strategy`
- `交易对`: `symbol`
- `周期`: `timeframe`
- `动作`: translate `open_long/open_short/close_long/close_short` to Chinese labels
- `信号时间`: derived from `candle_timestamp`
- `价格`: `payload["price"]` when present, otherwise `N/A`
- `仓位方向`: `payload["position_side"]` when present, otherwise infer from action
- `来源`: `payload["source"]` when present, otherwise `N/A`

## Failure Handling

`insert_signal(...)` remains the primary side effect and keeps its current behavior.

If the WeCom notification fails because notifications are disabled, the webhook is missing, the request fails, or the sender raises an exception, the failure must not stop signal emission. The signal should still be written successfully.

The notification path is therefore best-effort:

1. persist signal
2. attempt WeCom send for supported actions
3. suppress notification failures so the live loop stays healthy

## Testing

Add targeted tests around `emit_signal()` covering:

1. open actions trigger a WeCom notification after persistence
2. close actions trigger a WeCom notification after persistence
3. unsupported actions do not trigger a notification
4. notification failures do not prevent successful signal persistence

## Acceptance Criteria

1. Live signal emission sends a WeCom text notification for `open_long`, `open_short`, `close_long`, and `close_short`.
2. Notifications are sent through the existing webhook helper in `apps/notifications/wecom.py`.
3. Signal persistence still succeeds even if notification sending fails.
4. Tests cover the new notification behavior and failure tolerance.
