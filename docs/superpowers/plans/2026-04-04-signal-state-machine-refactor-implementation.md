# Signal State Machine Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 executor 信号判定升级为完整状态机，并补齐 close_long/close_short 端到端覆盖。

**Architecture:** 新增一个纯函数状态机模块，定义 `(current_side, signal_action) -> (decision, next_state)` 的唯一语义来源；`run_once()` 只做应用层编排（读信号、调用状态机、写事件、在 execute 时更新 position_state）。测试分为状态机全矩阵单元测试 + close 路径 E2E 回归测试，确保语义清晰且可维护。

**Tech Stack:** Python 3.11+, pytest, psycopg2, PostgreSQL

---

## File Structure

- Create: `apps/executor_service/state_machine.py`
  - 责任：定义状态机 transition matrix 与纯函数接口。
- Modify: `apps/executor_service/service.py`
  - 责任：调用状态机并在 execute 时更新 `position_state`。
- Create: `tests/test_executor_state_machine.py`
  - 责任：参数化覆盖 15 个状态机组合。
- Modify: `tests/test_executor_ignored_rejected_e2e.py`
  - 责任：新增 close_long/close_short 的 E2E 场景。

### Task 1: 先写状态机矩阵单元测试（红灯）

**Files:**
- Create: `tests/test_executor_state_machine.py`

- [ ] **Step 1: 写失败测试覆盖完整 15 组合**

创建 `tests/test_executor_state_machine.py`：

```python
import pytest

from apps.executor_service.state_machine import decide_transition


@pytest.mark.parametrize(
    "current_side,signal_action,expected_decision,expected_next_state",
    [
        ("flat", "open_long", "execute", "long"),
        ("flat", "open_short", "execute", "short"),
        ("flat", "close_long", "ignored", "flat"),
        ("flat", "close_short", "ignored", "flat"),
        ("flat", "flat", "ignored", "flat"),
        ("long", "open_long", "ignored", "long"),
        ("long", "open_short", "rejected", "long"),
        ("long", "close_long", "execute", "flat"),
        ("long", "close_short", "rejected", "long"),
        ("long", "flat", "execute", "flat"),
        ("short", "open_short", "ignored", "short"),
        ("short", "open_long", "rejected", "short"),
        ("short", "close_short", "execute", "flat"),
        ("short", "close_long", "rejected", "short"),
        ("short", "flat", "execute", "flat"),
    ],
)
def test_decide_transition_matrix(current_side, signal_action, expected_decision, expected_next_state):
    decision, next_state = decide_transition(current_side=current_side, signal_action=signal_action)
    assert decision == expected_decision
    assert next_state == expected_next_state
```

- [ ] **Step 2: 运行测试确认红灯**

Run:

```bash
.venv/bin/python -m pytest tests/test_executor_state_machine.py -q
```

Expected: FAIL，报 `ModuleNotFoundError: No module named 'apps.executor_service.state_machine'`。

- [ ] **Step 3: Commit 红灯测试**

```bash
git add tests/test_executor_state_machine.py
git commit -m "test: add failing matrix coverage for executor state machine"
```

### Task 2: 实现状态机模块并让单元测试转绿

**Files:**
- Create: `apps/executor_service/state_machine.py`
- Test: `tests/test_executor_state_machine.py`

- [ ] **Step 1: 实现状态机纯函数模块**

创建 `apps/executor_service/state_machine.py`：

```python
from typing import Literal


Side = Literal["flat", "long", "short"]
Action = Literal["open_long", "open_short", "close_long", "close_short", "flat"]
Decision = Literal["execute", "ignored", "rejected"]

Transition = tuple[Decision, Side]


TRANSITION_MATRIX: dict[tuple[Side, Action], Transition] = {
    ("flat", "open_long"): ("execute", "long"),
    ("flat", "open_short"): ("execute", "short"),
    ("flat", "close_long"): ("ignored", "flat"),
    ("flat", "close_short"): ("ignored", "flat"),
    ("flat", "flat"): ("ignored", "flat"),
    ("long", "open_long"): ("ignored", "long"),
    ("long", "open_short"): ("rejected", "long"),
    ("long", "close_long"): ("execute", "flat"),
    ("long", "close_short"): ("rejected", "long"),
    ("long", "flat"): ("execute", "flat"),
    ("short", "open_short"): ("ignored", "short"),
    ("short", "open_long"): ("rejected", "short"),
    ("short", "close_short"): ("execute", "flat"),
    ("short", "close_long"): ("rejected", "short"),
    ("short", "flat"): ("execute", "flat"),
}


def normalize_side(current_side: str | None) -> Side:
    if current_side in {"long", "short"}:
        return current_side
    return "flat"


def decide_transition(*, current_side: str | None, signal_action: str) -> Transition:
    side = normalize_side(current_side)
    key = (side, signal_action)
    if key not in TRANSITION_MATRIX:
        return "rejected", side
    return TRANSITION_MATRIX[key]
```

- [ ] **Step 2: 运行状态机单元测试确认通过**

Run:

```bash
.venv/bin/python -m pytest tests/test_executor_state_machine.py -q
```

Expected: PASS。

- [ ] **Step 3: Commit 状态机实现**

```bash
git add apps/executor_service/state_machine.py tests/test_executor_state_machine.py
git commit -m "feat: add explicit signal state transition matrix"
```

### Task 3: 接入 executor service 并更新 position_state

**Files:**
- Modify: `apps/executor_service/service.py`

- [ ] **Step 1: 写失败测试（close 执行后应转 flat）**

在 `tests/test_executor_ignored_rejected_e2e.py` 追加（先写一条最小失败测试）：

```python
def test_close_long_execute_sets_position_flat(monkeypatch):
    if os.getenv("PYTEST_XDIST_WORKER"):
        pytest.skip("uses shared tables")

    apply_test_db_env(monkeypatch)
    init_db_schema()
    clear_event_tables()

    strategy = "Ott2butKAMA"
    symbol = "ETHUSDT"
    timeframe = "5m"
    signal_time = "2024-04-05T00:20:00Z"
    action = "close_long"

    _insert_position_side(symbol=symbol, side="long")
    insert_signal(strategy=strategy, symbol=symbol, timeframe=timeframe, signal_time=signal_time, action=action, payload={"source": "close-long-e2e"})

    run_once()

    signal, execution = _fetch_signal_and_execution(
        strategy=strategy,
        symbol=symbol,
        timeframe=timeframe,
        signal_time=signal_time,
        action=action,
    )

    assert signal["status"] == "execute"
    assert execution["status"] == "execute"
```

- [ ] **Step 2: 运行该测试确认红灯（当前 close 语义/状态更新未完整）**

Run:

```bash
.venv/bin/python -m pytest tests/test_executor_ignored_rejected_e2e.py::test_close_long_execute_sets_position_flat -q
```

Expected: FAIL（在 state update 校验补上前应失败）。

- [ ] **Step 3: 修改 service 接入状态机与状态落库**

更新 `apps/executor_service/service.py` 核心逻辑：

```python
from apps.executor_service.state_machine import decide_transition


def upsert_position_side(*, cur, symbol: str, side: str) -> None:
    cur.execute(
        """
        INSERT INTO position_state (symbol, side, qty, entry_price, state_json, updated_at)
        VALUES (%s, %s, %s, %s, %s::jsonb, NOW())
        """,
        (symbol, side, 0, 0, "{}"),
    )


def run_once() -> None:
    ...
    current_side = fetch_current_side(cur=cur, symbol=symbol)
    decision, next_state = decide_transition(current_side=current_side, signal_action=action)
    ...
    if decision == "execute" and next_state != (current_side or "flat"):
        upsert_position_side(cur=cur, symbol=symbol, side=next_state)
```

注意：只做最小行为实现，不改已有事件写入结构。

- [ ] **Step 4: 运行 close 单测确认转绿**

Run:

```bash
.venv/bin/python -m pytest tests/test_executor_ignored_rejected_e2e.py::test_close_long_execute_sets_position_flat -q
```

Expected: PASS。

- [ ] **Step 5: Commit service 接入**

```bash
git add apps/executor_service/service.py tests/test_executor_ignored_rejected_e2e.py
git commit -m "feat: wire executor service to state machine transitions"
```

### Task 4: 补齐 close_long/close_short 端到端矩阵

**Files:**
- Modify: `tests/test_executor_ignored_rejected_e2e.py`

- [ ] **Step 1: 新增 close 路径 6 条测试**

新增以下测试（可复用 helper）：

- `test_close_long_execute_when_current_side_is_long`
- `test_close_long_ignored_when_current_side_is_flat`
- `test_close_long_rejected_when_current_side_is_short`
- `test_close_short_execute_when_current_side_is_short`
- `test_close_short_ignored_when_current_side_is_flat`
- `test_close_short_rejected_when_current_side_is_long`

每条保持统一断言：

- signal/execution status
- execution mode=dry_run
- execution.signal_id 对应

- [ ] **Step 2: 运行文件级 E2E**

Run:

```bash
.venv/bin/python -m pytest tests/test_executor_ignored_rejected_e2e.py -q
```

Expected: PASS。

- [ ] **Step 3: 回归现有关键链路测试**

Run:

```bash
.venv/bin/python -m pytest tests/test_signal_executor_flow.py::test_signal_executor_flow_execute_path -q
.venv/bin/python -m pytest tests/test_ott2butkama_bridge_smoke.py::test_bridge_execute_path_end_to_end -q
```

Expected: PASS。

- [ ] **Step 4: Commit close E2E 覆盖**

```bash
git add tests/test_executor_ignored_rejected_e2e.py
git commit -m "test: add close action e2e coverage for state machine paths"
```

### Task 5: 全量验证与工作区确认

**Files:**
- No additional files required

- [ ] **Step 1: 运行全量测试**

Run:

```bash
.venv/bin/python -m pytest tests -q
```

Expected: PASS。

- [ ] **Step 2: 检查最终改动范围**

Run:

```bash
git status --short
```

Expected: 仅出现本计划相关变更。

## Self-Review

- Spec coverage: 已覆盖状态机模块、service 接入、close 路径 E2E、全量回归。
- Placeholder scan: 无 TBD/TODO 占位，步骤含具体代码与命令。
- Type consistency: `decide_transition` / `normalize_side` / `next_state` 命名前后一致。
