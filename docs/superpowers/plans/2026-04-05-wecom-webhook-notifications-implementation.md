# WeCom Webhook Notifications Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Enterprise WeCom webhook notifications for dry-run execution/abnormal states and backtest summary results without destabilizing existing scripts.

**Architecture:** Build one small WeCom sender and formatter layer, hook it into `run_backtest_compare.py` for summary notifications, and add a lightweight dry-run notifier script that polls `execution_events` and dry-run health. Notifications must be optional, env-configured, and fail safe.

**Tech Stack:** Python 3.13, PostgreSQL, pytest, HTTP requests

---

## File Structure

- Create: `apps/notifications/wecom.py`
  - WeCom webhook sender and text-message formatting helpers.
- Create: `scripts/notify_dryrun_events.py`
  - Poll recent execution events and dry-run health, then send WeCom messages.
- Modify: `scripts/run_backtest_compare.py`
  - Send WeCom backtest summary after successful compare report generation.
- Create: `tests/test_wecom_notifications.py`
  - Verify sender payload formatting and fail-safe behavior.
- Create: `tests/test_notify_dryrun_events.py`
  - Verify dry-run notification polling behavior.

### Task 1: Add failing tests for the WeCom sender and dry-run notifier

**Files:**
- Create: `tests/test_wecom_notifications.py`
- Create: `tests/test_notify_dryrun_events.py`

- [ ] **Step 1: Write failing sender tests**

Create `tests/test_wecom_notifications.py` with the following content:

```python
def test_build_wecom_text_payload_uses_text_message_shape():
    from apps.notifications.wecom import build_text_payload

    payload = build_text_payload("hello world")

    assert payload == {
        "msgtype": "text",
        "text": {"content": "hello world"},
    }


def test_send_wecom_message_noops_when_webhook_missing(monkeypatch):
    from apps.notifications.wecom import send_text_message

    monkeypatch.delenv("WECOM_BOT_WEBHOOK", raising=False)

    sent = send_text_message("hello")

    assert sent is False
```

- [ ] **Step 2: Write failing dry-run notifier tests**

Create `tests/test_notify_dryrun_events.py` with the following content:

```python
def test_format_execution_event_message_contains_core_fields():
    from scripts.notify_dryrun_events import format_execution_event_message

    row = {
        "created_at": "2026-04-05T12:35:00+08:00",
        "strategy": "Ott2butKAMA_RiskManaged25",
        "symbol": "ETHUSDT",
        "action": "open_long",
        "decision": "execute",
        "reason": None,
    }

    text = format_execution_event_message(row)

    assert "[DRY-RUN]" in text
    assert "strategy: Ott2butKAMA_RiskManaged25" in text
    assert "action: open_long" in text
    assert "decision: execute" in text


def test_format_backtest_summary_message_contains_key_metrics():
    from apps.notifications.wecom import format_backtest_summary_message

    text = format_backtest_summary_message(
        baseline="Ott2butKAMA",
        candidate="Ott2butKAMA_RiskManaged25",
        symbol="ETHUSDT",
        timeframe="5m",
        window="2025-10-05 -> 2026-04-05",
        trades="93",
        win_rate="43.01%",
        net_profit="94.26%",
        max_drawdown="-20.12%",
    )

    assert "[BACKTEST]" in text
    assert "candidate: Ott2butKAMA_RiskManaged25" in text
    assert "net_profit: 94.26%" in text
```

- [ ] **Step 3: Run the tests to verify they fail**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_wecom_notifications.py tests/test_notify_dryrun_events.py -q
```

Expected: FAIL because the new sender/notifier modules do not exist yet.

### Task 2: Implement the WeCom sender and formatting layer

**Files:**
- Create: `apps/notifications/wecom.py`
- Test: `tests/test_wecom_notifications.py`

- [ ] **Step 1: Create the sender module**

Create `apps/notifications/wecom.py` with the following content:

```python
import os

import requests


def notifications_enabled() -> bool:
    return os.getenv("NOTIFY_ENABLED", "0") == "1"


def build_text_payload(content: str) -> dict:
    return {
        "msgtype": "text",
        "text": {"content": content},
    }


def send_text_message(content: str) -> bool:
    webhook = os.getenv("WECOM_BOT_WEBHOOK")
    if not notifications_enabled() or not webhook:
        return False

    try:
        response = requests.post(webhook, json=build_text_payload(content), timeout=5)
        response.raise_for_status()
    except Exception:
        return False
    return True


def format_backtest_summary_message(*, baseline: str, candidate: str, symbol: str, timeframe: str, window: str, trades: str, win_rate: str, net_profit: str, max_drawdown: str) -> str:
    return "\n".join(
        [
            "[BACKTEST]",
            f"baseline: {baseline}",
            f"candidate: {candidate}",
            f"symbol: {symbol}",
            f"timeframe: {timeframe}",
            f"window: {window}",
            f"trades: {trades}",
            f"win_rate: {win_rate}",
            f"net_profit: {net_profit}",
            f"max_drawdown: {max_drawdown}",
        ]
    )
```

- [ ] **Step 2: Run the sender tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_wecom_notifications.py -q
```

Expected: PASS.

### Task 3: Hook backtest compare summaries into WeCom notifications

**Files:**
- Modify: `scripts/run_backtest_compare.py`
- Test: `tests/test_notify_dryrun_events.py`

- [ ] **Step 1: Import the formatter and sender**

In `scripts/run_backtest_compare.py`, import:

```python
from apps.notifications.wecom import format_backtest_summary_message, send_text_message
```

- [ ] **Step 2: Send a summary after successful compare report generation**

After `write_compare_report(...)`, send a message with:

```python
send_text_message(
    format_backtest_summary_message(
        baseline=baseline_label,
        candidate=candidate_label,
        symbol=symbol,
        timeframe=timeframe,
        window=f"{start} -> {end}",
        trades=baseline_metrics["trades"] if baseline_label == candidate_label else candidate_metrics["trades"],
        win_rate=candidate_metrics["win_rate"],
        net_profit=candidate_metrics["net_profit"],
        max_drawdown=candidate_metrics["max_drawdown"],
    )
)
```

Keep notification sending non-fatal.

- [ ] **Step 3: Run related tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_run_backtest_compare.py tests/test_wecom_notifications.py -q
```

Expected: PASS.

### Task 4: Implement the dry-run notifier script

**Files:**
- Create: `scripts/notify_dryrun_events.py`
- Test: `tests/test_notify_dryrun_events.py`

- [ ] **Step 1: Create the notifier script**

Create `scripts/notify_dryrun_events.py` with the following content:

```python
from apps.notifications.wecom import send_text_message
from apps.shared.db import connect


def format_execution_event_message(row: dict) -> str:
    return "\n".join(
        [
            "[DRY-RUN]",
            f"strategy: {row['strategy']}",
            f"symbol: {row['symbol']}",
            f"action: {row['action']}",
            f"decision: {row['decision']}",
            f"time: {row['created_at']}",
            f"reason: {row['reason'] or 'N/A'}",
        ]
    )


def fetch_recent_execution_events(limit: int = 20) -> list[dict]:
    conn = connect()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT created_at, strategy, symbol, action, decision, reason
                FROM execution_events
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        {
            "created_at": row[0].isoformat(),
            "strategy": row[1],
            "symbol": row[2],
            "action": row[3],
            "decision": row[4],
            "reason": row[5],
        }
        for row in rows
    ]


def main() -> None:
    for row in reversed(fetch_recent_execution_events(limit=5)):
        send_text_message(format_execution_event_message(row))


if __name__ == "__main__":
    main()
```

This first version can be simple and stateless; deduplication can come later.

- [ ] **Step 2: Run dry-run notification tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_notify_dryrun_events.py -q
```

Expected: PASS.

### Task 5: Final verification

**Files:**
- No new files required

- [ ] **Step 1: Run full tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest
```

Expected: PASS.

- [ ] **Step 2: Inspect worktree status**

Run:

```bash
git status --short
```

Expected: only the intended WeCom notification files appear.

## Self-Review

- Spec coverage: The plan covers a WeCom sender, backtest notifications, dry-run notifications, and failure-safe behavior.
- Placeholder scan: All tasks contain exact file paths, concrete code, and direct commands.
- Type consistency: The plan consistently uses WeCom text webhook delivery with env-based optional enablement.
