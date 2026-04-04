# Bridge Smoke Test 固化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把现有 Ott2butKAMA bridge smoke 链路固化为可重复的 pytest 测试，并移除对系统 `python3` 子进程的依赖。

**Architecture:** 保留现有业务实现不变，新增一层测试基建用于统一 DB 环境、schema 初始化和数据清理。新增一条专用 bridge 集成 smoke 测试覆盖 `execute` 路径，并让现有 flow 测试复用同一初始化方式。手工 smoke 脚本继续保留为开发辅助，不再作为回归验收标准。

**Tech Stack:** Python 3.11+, pytest, psycopg2-binary, PostgreSQL

---

## File Structure

- Create: `tests/db_testkit.py`
  - 责任：提供测试专用 DB 工具（环境注入、schema 初始化、表清理、查询辅助）。
- Create: `tests/test_ott2butkama_bridge_smoke.py`
  - 责任：验证 bridge -> signal_events -> executor -> execution_events 的 execute 主路径。
- Modify: `tests/test_signal_executor_flow.py`
  - 责任：复用 `tests/db_testkit.py`，移除 `subprocess + python3` 初始化路径。
- Modify: `docs/runbook.md`
  - 责任：补充“回归验证以 pytest 为准”的命令。

### Task 1: 建立测试 DB 工具模块并切换现有 flow 测试

**Files:**
- Create: `tests/db_testkit.py`
- Modify: `tests/test_signal_executor_flow.py`

- [ ] **Step 1: 先写失败测试，约束新的 DB 工具接口**

在 `tests/test_signal_executor_flow.py` 顶部新增导入并替换原 `_apply_test_db_env` 使用方式：

```python
from tests.db_testkit import apply_test_db_env, init_db_schema, clear_event_tables
```

并在测试函数开头使用：

```python
apply_test_db_env()
init_db_schema()
clear_event_tables()
```

然后删掉这一行（让测试先红灯）：

```python
subprocess.run(["python3", "scripts/init_db.py"], check=True, env=env)
```

- [ ] **Step 2: 运行目标测试确认红灯**

Run:

```bash
.venv/bin/python -m pytest tests/test_signal_executor_flow.py::test_signal_executor_flow_execute_path -q
```

Expected: FAIL，错误为 `ModuleNotFoundError: No module named 'tests.db_testkit'`。

- [ ] **Step 3: 实现最小 DB 工具模块**

创建 `tests/db_testkit.py`：

```python
import os
from pathlib import Path

from apps.shared.db import connect


def apply_test_db_env() -> None:
    os.environ["POSTGRES_HOST"] = "127.0.0.1"
    os.environ["POSTGRES_PORT"] = "5432"
    os.environ["POSTGRES_DB"] = "jesse_db"
    os.environ["POSTGRES_USER"] = "jesse_user"
    os.environ["POSTGRES_PASSWORD"] = "password"


def init_db_schema() -> None:
    sql = Path("db/init.sql").read_text()
    conn = connect()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql)
    finally:
        conn.close()


def clear_event_tables() -> None:
    conn = connect()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM execution_events")
                cur.execute("DELETE FROM signal_events")
    finally:
        conn.close()
```

同时更新 `tests/test_signal_executor_flow.py`（删 `subprocess` 和旧 `_apply_test_db_env`，改为新工具函数）。

- [ ] **Step 4: 运行目标测试确认转绿**

Run:

```bash
.venv/bin/python -m pytest tests/test_signal_executor_flow.py::test_signal_executor_flow_execute_path -q
```

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add tests/db_testkit.py tests/test_signal_executor_flow.py
git commit -m "test: unify db init path for flow test"
```

### Task 2: 把 bridge smoke 链路固化为 pytest 集成测试

**Files:**
- Create: `tests/test_ott2butkama_bridge_smoke.py`

- [ ] **Step 1: 写失败测试（先只断言事件存在）**

创建 `tests/test_ott2butkama_bridge_smoke.py`：

```python
from apps.executor_service.service import run_once
from apps.shared.db import connect
from apps.signal_service.jesse_bridge.emitter import emit_signal
from tests.db_testkit import apply_test_db_env, init_db_schema, clear_event_tables


def test_bridge_execute_path_end_to_end():
    apply_test_db_env()
    init_db_schema()
    clear_event_tables()

    emit_signal(
        strategy="Ott2butKAMA",
        symbol="ETHUSDT",
        timeframe="5m",
        candle_timestamp=1712188800000,
        action="open_long",
        payload={"source": "smoke-test", "price": 2500.0},
    )

    run_once()

    conn = connect()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM signal_events ORDER BY id DESC LIMIT 1")
                signal_row = cur.fetchone()
                cur.execute("SELECT id FROM execution_events ORDER BY id DESC LIMIT 1")
                execution_row = cur.fetchone()

        assert signal_row is not None
        assert execution_row is not None
    finally:
        conn.close()
```

- [ ] **Step 2: 运行新测试确认红灯（若逻辑未齐全）或可通过**

Run:

```bash
.venv/bin/python -m pytest tests/test_ott2butkama_bridge_smoke.py::test_bridge_execute_path_end_to_end -q
```

Expected: 在实现完整断言前，可能 FAIL 或 PASS；无论结果如何，继续下一步补完整断言。

- [ ] **Step 3: 补完整断言和可定位失败信息**

把查询与断言替换为：

```python
from psycopg2.extras import RealDictCursor


def _latest_signal_and_execution() -> tuple[dict | None, dict | None]:
    conn = connect()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, strategy, symbol, action, status
                    FROM signal_events
                    ORDER BY id DESC
                    LIMIT 1
                    """
                )
                signal = cur.fetchone()

                cur.execute(
                    """
                    SELECT id, signal_id, symbol, mode, status
                    FROM execution_events
                    ORDER BY id DESC
                    LIMIT 1
                    """
                )
                execution = cur.fetchone()
        return signal, execution
    finally:
        conn.close()


def test_bridge_execute_path_end_to_end():
    apply_test_db_env()
    init_db_schema()
    clear_event_tables()

    emit_signal(
        strategy="Ott2butKAMA",
        symbol="ETHUSDT",
        timeframe="5m",
        candle_timestamp=1712188800000,
        action="open_long",
        payload={"source": "smoke-test", "price": 2500.0},
    )

    run_once()

    signal, execution = _latest_signal_and_execution()

    assert signal is not None, "signal row missing; bridge write may have failed"
    assert signal["strategy"] == "Ott2butKAMA", signal
    assert signal["symbol"] == "ETHUSDT", signal
    assert signal["action"] == "open_long", signal
    assert signal["status"] == "execute", signal

    assert execution is not None, "execution row missing; executor consume may have failed"
    assert execution["symbol"] == "ETHUSDT", execution
    assert execution["mode"] == "dry_run", execution
    assert execution["status"] == "execute", execution
    assert execution["signal_id"] == signal["id"], {"signal": signal, "execution": execution}
```

- [ ] **Step 4: 运行新测试确认通过**

Run:

```bash
.venv/bin/python -m pytest tests/test_ott2butkama_bridge_smoke.py::test_bridge_execute_path_end_to_end -q
```

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add tests/test_ott2butkama_bridge_smoke.py
git commit -m "test: add bridge smoke integration coverage"
```

### Task 3: 更新运行手册并做全量回归

**Files:**
- Modify: `docs/runbook.md`

- [ ] **Step 1: 在 runbook 增加 pytest 回归入口**

在 `docs/runbook.md` 追加：

```markdown
## Bridge 回归测试（推荐）

```bash
.venv/bin/python -m pytest tests/test_ott2butkama_bridge_smoke.py -q
.venv/bin/python -m pytest tests/test_signal_executor_flow.py -q
```

说明：

- 以 pytest 结果作为 bridge 回归验收标准。
- `scripts/smoke_test_ott2butkama_bridge.py` 仅保留为开发调试脚本。
```

- [ ] **Step 2: 跑全量测试**

Run:

```bash
.venv/bin/python -m pytest tests -q
```

Expected: PASS。

- [ ] **Step 3: 检查最终改动范围**

Run:

```bash
git status --short
```

Expected: 仅出现本计划涉及文件变更。

- [ ] **Step 4: Commit**

```bash
git add docs/runbook.md
git commit -m "docs: document pytest-based bridge regression checks"
```

## Self-Review

- Spec coverage: 已覆盖 execute 主链路固化、统一初始化路径、保留脚本但改验收口径、runbook 测试命令补充。
- Placeholder scan: 无 `TODO/TBD/implement later` 等占位语句。
- Type consistency: `apply_test_db_env/init_db_schema/clear_event_tables` 在所有任务中命名一致，`test_bridge_execute_path_end_to_end` 用例命名一致。
