# Executor Ignored Rejected E2E Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 executor 增加最小 current-side 读取能力，并在端到端链路上补齐 `ignored` 和 `rejected` 两条状态回归测试。

**Architecture:** 继续复用现有 `signal_events -> run_once -> execution_events` 主链路，只在 executor service 增加一个读取 `position_state` 最新 side 的函数，并把该 side 传给 `decide_action`。测试层新增一个专门 E2E 测试文件，插入 `position_state` 预置状态后验证 `open_long` 在不同仓位方向下产出 `ignored/rejected`。

**Tech Stack:** Python 3.11+, pytest, psycopg2, PostgreSQL

---

## File Structure

- Modify: `apps/executor_service/service.py`
  - 责任：增加 `fetch_current_side`，并在 `run_once()` 中使用该结果参与决策。
- Create: `tests/test_executor_ignored_rejected_e2e.py`
  - 责任：新增两条端到端用例覆盖 `ignored/rejected`。

### Task 1: 新增 ignored/rejected 端到端失败测试

**Files:**
- Create: `tests/test_executor_ignored_rejected_e2e.py`

- [ ] **Step 1: 写失败测试文件（先定义预期行为）**

创建 `tests/test_executor_ignored_rejected_e2e.py`，写入以下完整内容：

```python
import os

import pytest
from psycopg2.extras import RealDictCursor

from apps.executor_service.service import run_once
from apps.shared.db import connect
from apps.signal_service.writer import insert_signal
from tests.db_testkit import apply_test_db_env, clear_event_tables, init_db_schema


def _insert_position_side(*, symbol: str, side: str) -> None:
    conn = connect()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO position_state (symbol, side, qty, entry_price, state_json)
                    VALUES (%s, %s, %s, %s, %s::jsonb)
                    """,
                    (symbol, side, 1, 2500, "{}"),
                )
    finally:
        conn.close()


def _fetch_signal_and_execution(*, strategy: str, symbol: str, timeframe: str, signal_time: str, action: str) -> tuple[dict, dict]:
    conn = connect()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, strategy, symbol, action, status
                    FROM signal_events
                    WHERE strategy = %s
                      AND symbol = %s
                      AND timeframe = %s
                      AND signal_time = %s::timestamptz
                      AND action = %s
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (strategy, symbol, timeframe, signal_time, action),
                )
                signal = cur.fetchone()

                assert signal is not None, "signal row not found for test case"

                cur.execute(
                    """
                    SELECT id, signal_id, symbol, mode, status
                    FROM execution_events
                    WHERE signal_id = %s
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (signal["id"],),
                )
                execution = cur.fetchone()

                assert execution is not None, "execution row not found for test case"
                return signal, execution
    finally:
        conn.close()


def test_open_long_ignored_when_current_side_is_long():
    if os.getenv("PYTEST_XDIST_WORKER"):
        pytest.skip("uses clear_event_tables on shared tables; run without xdist workers")

    apply_test_db_env()
    init_db_schema()
    clear_event_tables()

    strategy = "Ott2butKAMA"
    symbol = "ETHUSDT"
    timeframe = "5m"
    signal_time = "2024-04-05T00:00:00Z"
    action = "open_long"

    _insert_position_side(symbol=symbol, side="long")

    insert_signal(
        strategy=strategy,
        symbol=symbol,
        timeframe=timeframe,
        signal_time=signal_time,
        action=action,
        payload={"source": "ignored-e2e"},
    )

    run_once()

    signal, execution = _fetch_signal_and_execution(
        strategy=strategy,
        symbol=symbol,
        timeframe=timeframe,
        signal_time=signal_time,
        action=action,
    )

    assert signal["status"] == "ignored", signal
    assert execution["status"] == "ignored", execution
    assert execution["mode"] == "dry_run", execution
    assert execution["signal_id"] == signal["id"], {"signal": signal, "execution": execution}


def test_open_long_rejected_when_current_side_is_short():
    if os.getenv("PYTEST_XDIST_WORKER"):
        pytest.skip("uses clear_event_tables on shared tables; run without xdist workers")

    apply_test_db_env()
    init_db_schema()
    clear_event_tables()

    strategy = "Ott2butKAMA"
    symbol = "ETHUSDT"
    timeframe = "5m"
    signal_time = "2024-04-05T00:05:00Z"
    action = "open_long"

    _insert_position_side(symbol=symbol, side="short")

    insert_signal(
        strategy=strategy,
        symbol=symbol,
        timeframe=timeframe,
        signal_time=signal_time,
        action=action,
        payload={"source": "rejected-e2e"},
    )

    run_once()

    signal, execution = _fetch_signal_and_execution(
        strategy=strategy,
        symbol=symbol,
        timeframe=timeframe,
        signal_time=signal_time,
        action=action,
    )

    assert signal["status"] == "rejected", signal
    assert execution["status"] == "rejected", execution
    assert execution["mode"] == "dry_run", execution
    assert execution["signal_id"] == signal["id"], {"signal": signal, "execution": execution}
```

- [ ] **Step 2: 运行新增测试确认红灯**

Run:

```bash
.venv/bin/python -m pytest tests/test_executor_ignored_rejected_e2e.py -q
```

Expected: FAIL（当前 `run_once()` 仍把 `current_side` 固定为 `None`，会得到 `execute` 而不是 `ignored/rejected`）。

- [ ] **Step 3: Commit 失败测试**

```bash
git add tests/test_executor_ignored_rejected_e2e.py
git commit -m "test: add failing e2e coverage for ignored and rejected paths"
```

### Task 2: 为 executor 增加 current-side 读取并让测试转绿

**Files:**
- Modify: `apps/executor_service/service.py`
- Test: `tests/test_executor_ignored_rejected_e2e.py`

- [ ] **Step 1: 实现最小 current-side 读取与接入逻辑**

将 `apps/executor_service/service.py` 更新为以下完整内容：

```python
import json

from apps.executor_service.rules import decide_action
from apps.shared.db import connect


def build_execution_payload(*, signal_id: int, symbol: str, status: str) -> dict:
    return {
        "signal_id": signal_id,
        "symbol": symbol,
        "side": "unknown",
        "mode": "dry_run",
        "status": status,
        "detail_json": {"source": "executor_service"},
    }


def fetch_current_side(*, symbol: str) -> str | None:
    conn = connect()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT side
                    FROM position_state
                    WHERE symbol = %s
                    ORDER BY updated_at DESC, id DESC
                    LIMIT 1
                    """,
                    (symbol,),
                )
                row = cur.fetchone()
                return None if row is None else row[0]
    finally:
        conn.close()


def run_once() -> None:
    conn = connect()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, symbol, action
                    FROM signal_events
                    WHERE status = 'new'
                    ORDER BY id ASC
                    LIMIT 1
                    """
                )
                row = cur.fetchone()
                if row is None:
                    return

                signal_id, symbol, action = row
                current_side = fetch_current_side(symbol=symbol)
                decision = decide_action(action, current_side)

                cur.execute(
                    "UPDATE signal_events SET status = %s, updated_at = NOW() WHERE id = %s AND status = 'new'",
                    (decision, signal_id),
                )

                payload = build_execution_payload(signal_id=signal_id, symbol=symbol, status=decision)
                cur.execute(
                    """
                    INSERT INTO execution_events (signal_id, symbol, side, mode, status, detail_json)
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    (
                        payload["signal_id"],
                        payload["symbol"],
                        payload["side"],
                        payload["mode"],
                        payload["status"],
                        json.dumps(payload["detail_json"]),
                    ),
                )
    finally:
        conn.close()
```

- [ ] **Step 2: 运行新增测试确认通过**

Run:

```bash
.venv/bin/python -m pytest tests/test_executor_ignored_rejected_e2e.py -q
```

Expected: PASS（2 条用例通过）。

- [ ] **Step 3: 回归 execute 路径测试**

Run:

```bash
.venv/bin/python -m pytest tests/test_signal_executor_flow.py::test_signal_executor_flow_execute_path -q
.venv/bin/python -m pytest tests/test_ott2butkama_bridge_smoke.py::test_bridge_execute_path_end_to_end -q
```

Expected: PASS（既有 execute 回归不受影响）。

- [ ] **Step 4: Commit 实现与回归通过结果**

```bash
git add apps/executor_service/service.py tests/test_executor_ignored_rejected_e2e.py
git commit -m "feat: support ignored and rejected e2e decisions from position side"
```

### Task 3: 全量验证与改动确认

**Files:**
- No additional file changes required

- [ ] **Step 1: 跑全量测试**

Run:

```bash
.venv/bin/python -m pytest tests -q
```

Expected: PASS（全量通过）。

- [ ] **Step 2: 查看最终改动范围**

Run:

```bash
git status --short
```

Expected: 仅包含本计划涉及文件和预期未跟踪文件。

- [ ] **Step 3: 不新增提交，仅确认工作区状态**

该任务只做全量验证和状态检查，不新增代码提交，避免重复提交或误包含无关文件。

## Self-Review

- Spec coverage: 已覆盖 `position_state` current-side 读取、`run_once()` 接入、`ignored/rejected` 两条 E2E 用例、全量回归验证。
- Placeholder scan: 文档无 TBD/TODO/后补描述，步骤均含具体代码与命令。
- Type consistency: `fetch_current_side`、`run_once`、`apply_test_db_env/init_db_schema/clear_event_tables` 命名在任务间一致。
