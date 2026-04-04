# Open Short Symmetric E2E Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 ignored/rejected E2E 基础上补齐 `open_short` 的对称路径测试覆盖。

**Architecture:** 不改动 executor 业务逻辑，仅扩展 `tests/test_executor_ignored_rejected_e2e.py`，新增两条与 `open_long` 同构的 `open_short` 用例。测试流程继续复用现有 DB 初始化、数据清理、状态查询与断言口径，确保最小改动完成覆盖补齐。

**Tech Stack:** Python 3.11+, pytest, psycopg2, PostgreSQL

---

## File Structure

- Modify: `tests/test_executor_ignored_rejected_e2e.py`
  - 责任：新增 `open_short` 对称 E2E 用例并保持现有测试结构一致。

### Task 1: 添加 open_short 对称失败测试（红灯）

**Files:**
- Modify: `tests/test_executor_ignored_rejected_e2e.py`

- [ ] **Step 1: 先写两条新测试（预期先红灯）**

在现有文件末尾追加以下两条测试：

```python
def test_open_short_ignored_when_current_side_is_short(monkeypatch):
    if os.getenv("PYTEST_XDIST_WORKER"):
        pytest.skip("uses clear_event_tables on shared tables; run without xdist workers")

    apply_test_db_env(monkeypatch)
    init_db_schema()
    clear_event_tables()

    strategy = "Ott2butKAMA"
    symbol = "ETHUSDT"
    timeframe = "5m"
    signal_time = "2024-04-05T00:10:00Z"
    action = "open_short"

    _insert_position_side(symbol=symbol, side="short")

    insert_signal(
        strategy=strategy,
        symbol=symbol,
        timeframe=timeframe,
        signal_time=signal_time,
        action=action,
        payload={"source": "ignored-open-short-e2e"},
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


def test_open_short_rejected_when_current_side_is_long(monkeypatch):
    if os.getenv("PYTEST_XDIST_WORKER"):
        pytest.skip("uses clear_event_tables on shared tables; run without xdist workers")

    apply_test_db_env(monkeypatch)
    init_db_schema()
    clear_event_tables()

    strategy = "Ott2butKAMA"
    symbol = "ETHUSDT"
    timeframe = "5m"
    signal_time = "2024-04-05T00:15:00Z"
    action = "open_short"

    _insert_position_side(symbol=symbol, side="long")

    insert_signal(
        strategy=strategy,
        symbol=symbol,
        timeframe=timeframe,
        signal_time=signal_time,
        action=action,
        payload={"source": "rejected-open-short-e2e"},
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

- [ ] **Step 2: 运行目标测试确认红灯（若行为未实现）或记录当前结果**

Run:

```bash
.venv/bin/python -m pytest tests/test_executor_ignored_rejected_e2e.py -q
```

Expected: 如果实现已支持对称规则，该步可能直接 PASS；若尚未覆盖对称路径，将在新测试处 FAIL。

- [ ] **Step 3: 提交新增测试**

```bash
git add tests/test_executor_ignored_rejected_e2e.py
git commit -m "test: add open short symmetric ignored rejected e2e cases"
```

### Task 2: 让 open_short 对称用例转绿并做回归验证

**Files:**
- Modify: `tests/test_executor_ignored_rejected_e2e.py` (仅当 Task 1 出现失败时)
- Verify: `apps/executor_service/service.py`

- [ ] **Step 1: 如果测试失败，按最小改动修复并保持口径一致**

若 Task 1 第 2 步出现 FAIL，只允许做最小修复：

- 优先修复测试数据问题（如 signal_time/action/filter 条件不一致）
- 若涉及业务逻辑，确保不改变 `open_long` 既有行为
- 不扩展范围到 close 路径

本步骤结束要求：`open_short` 两条新用例通过。

- [ ] **Step 2: 运行 ignored/rejected E2E 全量文件**

Run:

```bash
.venv/bin/python -m pytest tests/test_executor_ignored_rejected_e2e.py -q
```

Expected: PASS（包含 `open_long` 与 `open_short` 全部用例）。

- [ ] **Step 3: 运行关键 execute 回归用例**

Run:

```bash
.venv/bin/python -m pytest tests/test_signal_executor_flow.py::test_signal_executor_flow_execute_path -q
.venv/bin/python -m pytest tests/test_ott2butkama_bridge_smoke.py::test_bridge_execute_path_end_to_end -q
```

Expected: PASS（新增 open_short 覆盖不影响 execute 主链路）。

- [ ] **Step 4: 提交必要修复（若有）**

若 Task 2 Step 1 发生代码修复，提交：

```bash
git add apps/executor_service/service.py tests/test_executor_ignored_rejected_e2e.py
git commit -m "fix: keep symmetric open short e2e behavior consistent"
```

若无修复（仅新增测试且全部通过），跳过此提交步骤。

### Task 3: 全量测试与状态确认

**Files:**
- No additional file changes required

- [ ] **Step 1: 跑全量测试**

Run:

```bash
.venv/bin/python -m pytest tests -q
```

Expected: PASS。

- [ ] **Step 2: 查看最终状态**

Run:

```bash
git status --short
```

Expected: 只包含本计划相关改动（或空工作区，取决于是否已提交）。

## Self-Review

- Spec coverage: 已覆盖 open_short 对称两条 E2E、保持断言口径一致、全量回归验证。
- Placeholder scan: 无 TBD/TODO/后补占位描述；每步含明确命令与预期。
- Type consistency: 复用现有 helper 与测试函数命名体系，无新命名冲突。
