# 最小 DB 闭环实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `jesse-signal-executor` 中实现最小数据库闭环，使 signal-service CLI 能写入信号，executor-service CLI 能消费一条信号并写入模拟 `executions` 记录。

**Architecture:** 本次只扩展数据库内的闭环，不接入真实交易所，不更新真实仓位状态。Signal Service 通过 CLI 调用 `insert_signal(...)` 写入 `signals`；Executor Service 通过 CLI 调用 `run_once()` 消费一条 `new` 信号，更新 `signals.status` 并新增一条 `executions` 记录。测试重点放在 DB 生命周期而不是撮合逻辑。

**Tech Stack:** Python 3.11, PostgreSQL, psycopg2, pytest, argparse

---

### Task 1: 为 signal-service CLI 增加写信号入口

**Files:**
- Create: `apps/signal_service/cli.py`
- Test: `tests/test_signal_cli.py`

- [ ] **Step 1: 写失败测试，验证 CLI 参数入口可调用写信号函数**

```python
from apps.signal_service.cli import build_parser


def test_signal_cli_parser_accepts_required_args():
    parser = build_parser()
    args = parser.parse_args(
        [
            "--strategy", "Ott2butKAMA",
            "--symbol", "ETHUSDT",
            "--timeframe", "5m",
            "--signal-time", "2026-04-04T00:00:00Z",
            "--action", "open_long",
        ]
    )
    assert args.strategy == "Ott2butKAMA"
    assert args.action == "open_long"
```

- [ ] **Step 2: 运行测试确认红灯**

Run:

```bash
source .venv/bin/activate && python3 -m pytest tests/test_signal_cli.py -q
```

Expected: FAIL because `apps/signal_service/cli.py` does not exist.

- [ ] **Step 3: 实现 signal CLI**

```python
import argparse

from apps.signal_service.writer import insert_signal


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--timeframe", required=True)
    parser.add_argument("--signal-time", required=True)
    parser.add_argument("--action", required=True)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    insert_signal(
        strategy=args.strategy,
        symbol=args.symbol,
        timeframe=args.timeframe,
        signal_time=args.signal_time,
        action=args.action,
        payload={"source": "cli"},
    )


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
source .venv/bin/activate && python3 -m pytest tests/test_signal_cli.py -q
```

Expected: PASS.

### Task 2: 为 executor-service 增加单次消费 CLI

**Files:**
- Create: `apps/executor_service/cli.py`
- Test: `tests/test_executor_cli.py`

- [ ] **Step 1: 写失败测试，验证 executor CLI 暴露 main 入口**

```python
from apps.executor_service.cli import main


def test_executor_cli_exposes_main():
    assert callable(main)
```

- [ ] **Step 2: 运行测试确认红灯**

Run:

```bash
source .venv/bin/activate && python3 -m pytest tests/test_executor_cli.py -q
```

Expected: FAIL because `apps/executor_service/cli.py` does not exist.

- [ ] **Step 3: 实现 executor CLI**

```python
from apps.executor_service.service import run_once


def main() -> None:
    run_once()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
source .venv/bin/activate && python3 -m pytest tests/test_executor_cli.py -q
```

Expected: PASS.

### Task 3: 扩展 executor 写入模拟 `executions`

**Files:**
- Modify: `apps/executor_service/service.py`
- Test: `tests/test_executor_service_unit.py`

- [ ] **Step 1: 写失败测试，验证执行后会写入 `executions` 记录构造函数**

```python
from apps.executor_service.service import build_execution_payload


def test_build_execution_payload_uses_dry_run_mode():
    payload = build_execution_payload(signal_id=1, symbol="ETHUSDT", status="execute")
    assert payload["signal_id"] == 1
    assert payload["mode"] == "dry_run"
    assert payload["status"] == "execute"
```

- [ ] **Step 2: 运行测试确认红灯**

Run:

```bash
source .venv/bin/activate && python3 -m pytest tests/test_executor_service_unit.py -q
```

Expected: FAIL because `build_execution_payload` does not exist.

- [ ] **Step 3: 在 service 中增加 execution payload 与 insert 逻辑**

```python
def build_execution_payload(*, signal_id: int, symbol: str, status: str) -> dict:
    return {
        "signal_id": signal_id,
        "symbol": symbol,
        "side": "unknown",
        "mode": "dry_run",
        "status": status,
        "detail_json": {"source": "executor_service"},
    }
```

并在 `run_once()` 中在更新 `signals.status` 后执行：

```python
payload = build_execution_payload(signal_id=signal_id, symbol=symbol, status=decision)
cur.execute(
    """
    INSERT INTO executions (signal_id, symbol, side, mode, status, detail_json)
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
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
source .venv/bin/activate && python3 -m pytest tests/test_executor_service_unit.py -q
```

Expected: PASS.

### Task 4: 增加 DB 闭环集成测试

**Files:**
- Create: `tests/test_signal_executor_flow.py`

- [ ] **Step 1: 写失败测试，验证 execute 路径完整闭环**

```python
def test_signal_executor_flow_execute_path():
    # 1. init db schema
    # 2. insert one signal
    # 3. run executor once
    # 4. assert signals.status updated
    # 5. assert one executions row exists
    assert False
```

- [ ] **Step 2: 运行测试确认红灯**

Run:

```bash
source .venv/bin/activate && python3 -m pytest tests/test_signal_executor_flow.py -q
```

Expected: FAIL because test is placeholder red.

- [ ] **Step 3: 实现最小集成测试**

测试步骤必须包括：

- 调用 `scripts/init_db.py`
- 清理 `signals` 和 `executions`
- 调用 `insert_signal(...)`
- 调用 `run_once()`
- 查询数据库确认：
  - `signals.status = 'execute'`
  - `executions` 新增一条，且 `status = 'execute'`

- [ ] **Step 4: 运行集成测试确认通过**

Run:

```bash
source .venv/bin/activate && export POSTGRES_PASSWORD=app_password && python3 -m pytest tests/test_signal_executor_flow.py -q
```

Expected: PASS.

### Task 5: 最终验证最小 DB 闭环

**Files:**
- Modify: `docs/runbook.md`

- [ ] **Step 1: 在 runbook 中新增最小 DB 闭环命令示例**

```markdown
## 最小 DB 闭环

```bash
source .venv/bin/activate
python3 scripts/init_db.py
python3 -m apps.signal_service.cli --strategy Ott2butKAMA --symbol ETHUSDT --timeframe 5m --signal-time 2026-04-04T00:00:00Z --action open_long
python3 -m apps.executor_service.cli
```
```

- [ ] **Step 2: 运行全部测试**

Run:

```bash
source .venv/bin/activate && python3 -m pytest tests -q
```

Expected: PASS.

- [ ] **Step 3: 查看最终仓库状态**

Run:

```bash
git status --short
```

Expected: only intended files changed.
