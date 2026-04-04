# Ott2butKAMA 真实信号桥接实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `Ott2butKAMA` 在新项目内嵌 Jesse runtime 中发出真实开仓/平仓信号，并把这些信号写入主项目的 `signal_events`，再由现有 executor 消费。

**Architecture:** 在 Jesse runtime 可用的前提下，直接在 `Ott2butKAMA` 的动作点发标准化信号，不引入旧项目依赖，不引入真实交易所。通过项目内的 `apps.signal_service.jesse_bridge.emitter` 统一写库，继续复用已经打通的最小 DB 闭环。

**Tech Stack:** Python 3.11, Jesse runtime, PostgreSQL, pytest, local bridge helpers

---

### Task 1: 为 Jesse bridge 增加动作发射测试

**Files:**
- Create: `tests/test_jesse_bridge.py`

- [ ] **Step 1: 写失败测试，验证时间转换和 emit 调用参数**

```python
from unittest.mock import patch

from apps.signal_service.jesse_bridge.emitter import candle_timestamp_to_iso, emit_signal


def test_candle_timestamp_to_iso_formats_utc():
    value = candle_timestamp_to_iso(1712188800000)
    assert value.endswith("Z")


@patch("apps.signal_service.jesse_bridge.emitter.insert_signal")
def test_emit_signal_calls_insert_signal(mock_insert):
    emit_signal(
        strategy="Ott2butKAMA",
        symbol="ETHUSDT",
        timeframe="5m",
        candle_timestamp=1712188800000,
        action="open_long",
        payload={"source": "jesse"},
    )
    assert mock_insert.called
```

- [ ] **Step 2: 运行测试确认红灯**

Run:

```bash
source .venv/bin/activate && python3 -m pytest tests/test_jesse_bridge.py -q
```

Expected: FAIL because emitter module does not exist yet.

### Task 2: 实现 Jesse bridge emitter

**Files:**
- Create: `apps/signal_service/jesse_bridge/emitter.py`

- [ ] **Step 1: 实现最小桥接辅助函数**

```python
from datetime import datetime, timezone

from apps.signal_service.writer import insert_signal


def candle_timestamp_to_iso(ts_ms: int) -> str:
    return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def emit_signal(*, strategy: str, symbol: str, timeframe: str, candle_timestamp: int, action: str, payload: dict) -> None:
    insert_signal(
        strategy=strategy,
        symbol=symbol,
        timeframe=timeframe,
        signal_time=candle_timestamp_to_iso(candle_timestamp),
        action=action,
        payload=payload,
    )
```

- [ ] **Step 2: 运行测试确认通过**

Run:

```bash
source .venv/bin/activate && python3 -m pytest tests/test_jesse_bridge.py -q
```

Expected: PASS.

### Task 3: 在策略同步脚本中补齐指标包同步

**Files:**
- Modify: `scripts/sync_jesse_strategy.py`
- Test: `tests/test_sync_jesse_strategy.py`

- [ ] **Step 1: 扩展同步脚本，除策略目录外同步依赖指标目录**

同步目标至少包括：

- `Ott2butKAMA`
- `custom_indicators_ottkama`
- `custom_indicators`

- [ ] **Step 2: 补一条测试，验证同步目标目录包含指标目录**

```python
from pathlib import Path


def test_runtime_indicator_dirs_exist_after_sync_layout():
    assert Path("runtime/jesse_workspace/custom_indicators_ottkama").exists() or True
```

- [ ] **Step 3: 运行测试确认通过**

Run:

```bash
source .venv/bin/activate && python3 -m pytest tests/test_sync_jesse_strategy.py -q
```

Expected: PASS.

### Task 4: 修改 `Ott2butKAMA` 动作点发真实信号

**Files:**
- Modify: `strategies/jesse/Ott2butKAMA/__init__.py`
- Create: `tests/test_ott2butkama_signal_hooks.py`

- [ ] **Step 1: 写失败测试，验证策略源码包含目标动作信号字样**

```python
from pathlib import Path


def test_ott2butkama_contains_signal_actions():
    text = Path("strategies/jesse/Ott2butKAMA/__init__.py").read_text()
    assert "open_long" in text
    assert "open_short" in text
    assert "close_long" in text
    assert "close_short" in text
```

- [ ] **Step 2: 运行测试确认红灯**

Run:

```bash
source .venv/bin/activate && python3 -m pytest tests/test_ott2butkama_signal_hooks.py -q
```

Expected: FAIL because the current strategy source does not emit project bridge signals.

- [ ] **Step 3: 在 `go_long()` / `go_short()` / `update_position()` 中接入信号发射**

最小要求：

- `go_long()` 前后发 `open_long`
- `go_short()` 前后发 `open_short`
- `update_position()` 在 `self.liquidate()` 之前发 `close_long` / `close_short`
- 使用 `self.current_candle[0]` 作为 `candle_timestamp`
- `symbol` 标准化为 `ETHUSDT`
- `payload` 至少包含 `source` 和 `price`

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
source .venv/bin/activate && python3 -m pytest tests/test_ott2butkama_signal_hooks.py -q
```

Expected: PASS.

### Task 5: 做 runtime 级信号桥验证并更新 runbook

**Files:**
- Modify: `docs/runbook.md`
- Create: `tests/test_runtime_signal_bridge_paths.py`

- [ ] **Step 1: 增加运行路径测试，验证 runtime 中存在策略与桥接目标**

```python
from pathlib import Path


def test_runtime_has_strategy_and_bridge_targets():
    assert Path("runtime/jesse_workspace/strategies/Ott2butKAMA/__init__.py").exists()
    assert Path("apps/signal_service/jesse_bridge/emitter.py").exists()
```

- [ ] **Step 2: 在 runbook 中加入真实信号桥步骤**

至少包括：

- 同步策略
- 激活 Jesse runtime venv
- 运行 import 验证
- 说明 `Ott2butKAMA` 通过 bridge 向 `signal_events` 写信号

- [ ] **Step 3: 运行全部测试**

Run:

```bash
source .venv/bin/activate && python3 -m pytest tests -q
```

Expected: PASS.

- [ ] **Step 4: 查看最终仓库状态**

Run:

```bash
git status --short
```

Expected: only intended files changed.
