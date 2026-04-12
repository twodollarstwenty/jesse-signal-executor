# Live Signal WeCom Notifications Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Send a WeCom text notification whenever the live signal bridge emits an open or close trading signal, without breaking signal persistence when notification delivery fails.

**Architecture:** Keep signal persistence in `apps/signal_service/jesse_bridge/emitter.py` as the primary behavior and add a best-effort notification call immediately after `insert_signal(...)` succeeds. Reuse `apps/notifications/wecom.py` for delivery and extend the bridge tests so the notification behavior is covered at the shared emission boundary.

**Tech Stack:** Python, pytest, unittest.mock/monkeypatch, existing WeCom webhook helper

---

## File Structure

- Modify: `apps/signal_service/jesse_bridge/emitter.py`
  Purpose: keep the shared signal emission entrypoint, add notification formatting helpers, and send WeCom notifications for supported live trading actions.
- Modify: `tests/test_jesse_bridge.py`
  Purpose: cover message formatting, supported-action notification dispatch, unsupported-action suppression, and notification failure tolerance.

### Task 1: Add Failing Bridge Tests For Notification Behavior

**Files:**
- Modify: `tests/test_jesse_bridge.py`
- Test: `tests/test_jesse_bridge.py`

- [ ] **Step 1: Write the failing tests**

Add these tests to `tests/test_jesse_bridge.py`:

```python
from unittest.mock import patch

import pytest

from apps.signal_service.jesse_bridge.emitter import (
    build_signal_notification_message,
    candle_timestamp_to_iso,
    emit_signal,
)


def test_build_signal_notification_message_formats_open_long_payload():
    message = build_signal_notification_message(
        strategy="Ott2butKAMA",
        symbol="ETHUSDT",
        timeframe="5m",
        signal_time="2024-04-04T00:00:00Z",
        action="open_long",
        payload={"source": "jesse", "price": 2500.0, "position_side": "long"},
    )

    assert message == "\n".join(
        [
            "[交易信号]",
            "策略: Ott2butKAMA",
            "交易对: ETHUSDT",
            "周期: 5m",
            "动作: 开多",
            "信号时间: 2024-04-04T00:00:00Z",
            "价格: 2500.0",
            "仓位方向: long",
            "来源: jesse",
        ]
    )


@patch("apps.signal_service.jesse_bridge.emitter.send_text_message")
@patch("apps.signal_service.jesse_bridge.emitter.insert_signal")
def test_emit_signal_sends_notification_for_supported_action(mock_insert, mock_send):
    emit_signal(
        strategy="Ott2butKAMA",
        symbol="ETHUSDT",
        timeframe="5m",
        candle_timestamp=1712188800000,
        action="open_long",
        payload={"source": "jesse", "price": 2500.0},
    )

    mock_insert.assert_called_once()
    mock_send.assert_called_once_with(
        "\n".join(
            [
                "[交易信号]",
                "策略: Ott2butKAMA",
                "交易对: ETHUSDT",
                "周期: 5m",
                "动作: 开多",
                "信号时间: 2024-04-04T00:00:00Z",
                "价格: 2500.0",
                "仓位方向: long",
                "来源: jesse",
            ]
        )
    )


@patch("apps.signal_service.jesse_bridge.emitter.send_text_message")
@patch("apps.signal_service.jesse_bridge.emitter.insert_signal")
def test_emit_signal_skips_notification_for_unsupported_action(mock_insert, mock_send):
    emit_signal(
        strategy="Ott2butKAMA",
        symbol="ETHUSDT",
        timeframe="5m",
        candle_timestamp=1712188800000,
        action="none",
        payload={"source": "jesse"},
    )

    mock_insert.assert_called_once()
    mock_send.assert_not_called()


@patch("apps.signal_service.jesse_bridge.emitter.send_text_message", side_effect=RuntimeError("boom"))
@patch("apps.signal_service.jesse_bridge.emitter.insert_signal")
def test_emit_signal_suppresses_notification_failure(mock_insert, _mock_send):
    emit_signal(
        strategy="Ott2butKAMA",
        symbol="ETHUSDT",
        timeframe="5m",
        candle_timestamp=1712188800000,
        action="close_short",
        payload={"source": "jesse", "price": 2490.5},
    )

    mock_insert.assert_called_once()
```

- [ ] **Step 2: Run the bridge tests to verify they fail**

Run: `pytest tests/test_jesse_bridge.py -v`

Expected: FAIL because `build_signal_notification_message` does not exist yet and `emit_signal()` does not call `send_text_message()`.

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/test_jesse_bridge.py
git commit -m "test: cover live signal wecom notifications"
```

### Task 2: Implement Best-Effort WeCom Notifications In The Bridge

**Files:**
- Modify: `apps/signal_service/jesse_bridge/emitter.py`
- Test: `tests/test_jesse_bridge.py`

- [ ] **Step 1: Implement the minimal bridge notification code**

Update `apps/signal_service/jesse_bridge/emitter.py` to:

```python
from datetime import datetime, timezone

from apps.notifications.wecom import send_text_message
from apps.signal_service.writer import insert_signal


NOTIFIABLE_ACTION_LABELS = {
    "open_long": "开多",
    "open_short": "开空",
    "close_long": "平多",
    "close_short": "平空",
}


def candle_timestamp_to_iso(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def infer_position_side(action: str) -> str:
    if action in {"open_long", "close_long"}:
        return "long"
    if action in {"open_short", "close_short"}:
        return "short"
    return "N/A"


def build_signal_notification_message(
    *, strategy: str, symbol: str, timeframe: str, signal_time: str, action: str, payload: dict
) -> str:
    return "\n".join(
        [
            "[交易信号]",
            f"策略: {strategy}",
            f"交易对: {symbol}",
            f"周期: {timeframe}",
            f"动作: {NOTIFIABLE_ACTION_LABELS[action]}",
            f"信号时间: {signal_time}",
            f"价格: {payload.get('price', 'N/A')}",
            f"仓位方向: {payload.get('position_side') or infer_position_side(action)}",
            f"来源: {payload.get('source', 'N/A')}",
        ]
    )


def notify_signal_if_supported(
    *, strategy: str, symbol: str, timeframe: str, signal_time: str, action: str, payload: dict
) -> None:
    if action not in NOTIFIABLE_ACTION_LABELS:
        return

    message = build_signal_notification_message(
        strategy=strategy,
        symbol=symbol,
        timeframe=timeframe,
        signal_time=signal_time,
        action=action,
        payload=payload,
    )
    try:
        send_text_message(message)
    except Exception:
        return


def emit_signal(*, strategy: str, symbol: str, timeframe: str, candle_timestamp: int, action: str, payload: dict) -> None:
    signal_time = candle_timestamp_to_iso(candle_timestamp)
    insert_signal(
        strategy=strategy,
        symbol=symbol,
        timeframe=timeframe,
        signal_time=signal_time,
        action=action,
        payload=payload,
    )
    notify_signal_if_supported(
        strategy=strategy,
        symbol=symbol,
        timeframe=timeframe,
        signal_time=signal_time,
        action=action,
        payload=payload,
    )
```

- [ ] **Step 2: Run the targeted bridge tests to verify they pass**

Run: `pytest tests/test_jesse_bridge.py -v`

Expected: PASS for the message-formatting test, supported-action notification test, unsupported-action suppression test, and notification failure tolerance test.

- [ ] **Step 3: Run the WeCom helper tests to verify no regression**

Run: `pytest tests/test_wecom_notifications.py -v`

Expected: PASS and no changes needed in the webhook helper behavior.

- [ ] **Step 4: Commit the bridge implementation**

```bash
git add apps/signal_service/jesse_bridge/emitter.py tests/test_jesse_bridge.py
git commit -m "feat: notify live signal emissions via wecom"
```

### Task 3: Final Verification

**Files:**
- Modify: none
- Test: `tests/test_jesse_bridge.py`
- Test: `tests/test_wecom_notifications.py`
- Test: `tests/test_ott2butkama_bridge_smoke.py`

- [ ] **Step 1: Run the focused verification suite**

Run: `pytest tests/test_jesse_bridge.py tests/test_wecom_notifications.py tests/test_ott2butkama_bridge_smoke.py -v`

Expected: PASS. The smoke test should still show that signal emission writes a signal row and drives the existing executor path.

- [ ] **Step 2: Inspect the working tree before handoff**

Run: `git status --short`

Expected: the bridge, test, and plan/spec files for this work appear as changed. If unrelated files are also modified, leave them untouched and verify they are not part of this implementation.

- [ ] **Step 3: Prepare handoff summary**

Document the exact files changed, the verification commands that passed, and the required runtime configuration (`NOTIFY_ENABLED=1` and `WECOM_BOT_WEBHOOK`) before asking whether to create a commit.
