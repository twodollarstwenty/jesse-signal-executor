# 内嵌 Jesse Runtime 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `jesse-signal-executor` 内部建立独立 Jesse workspace，并接入 `Ott2butKAMA` 作为新项目自己的真实信号源。

**Architecture:** Jesse 被嵌入到 `runtime/jesse_workspace/` 中，策略源码由主项目维护在 `strategies/jesse/`，再同步到 Jesse runtime 使用。Jesse 策略直接调用新项目的 signal writer，将真实策略信号写入 `signal_events`，继续复用已经打通的最小 DB 闭环。

**Tech Stack:** Python 3.11, Jesse workspace, PostgreSQL, pytest, local scripts

---

### Task 1: 建立 Jesse runtime 目录与结构测试

**Files:**
- Create: `tests/test_embedded_jesse_layout.py`
- Create: `runtime/jesse_workspace/.gitkeep`
- Create: `strategies/jesse/.gitkeep`
- Create: `apps/signal_service/jesse_bridge/.gitkeep`

- [ ] **Step 1: 写失败测试，验证 Jesse runtime 目录存在**

```python
from pathlib import Path


def test_embedded_jesse_layout_exists():
    assert Path("runtime/jesse_workspace").exists()
    assert Path("strategies/jesse").exists()
    assert Path("apps/signal_service/jesse_bridge").exists()
```

- [ ] **Step 2: 运行测试确认红灯**

Run:

```bash
source .venv/bin/activate && python3 -m pytest tests/test_embedded_jesse_layout.py -q
```

Expected: FAIL because runtime directories do not exist yet.

- [ ] **Step 3: 创建 Jesse runtime 目录骨架**

使用以下结构：

- `runtime/jesse_workspace/`
- `strategies/jesse/`
- `apps/signal_service/jesse_bridge/`

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
source .venv/bin/activate && python3 -m pytest tests/test_embedded_jesse_layout.py -q
```

Expected: PASS.

### Task 2: 建立最小 Jesse runtime 基础结构

**Files:**
- Create: `runtime/jesse_workspace/strategies/.gitkeep`
- Create: `runtime/jesse_workspace/storage/.gitkeep`
- Create: `runtime/jesse_workspace/routes.py`
- Create: `runtime/jesse_workspace/config.py`
- Test: `tests/test_jesse_runtime_files.py`

- [ ] **Step 1: 写失败测试，验证 runtime 基础文件存在**

```python
from pathlib import Path


def test_embedded_jesse_runtime_core_files_exist():
    assert Path("runtime/jesse_workspace/routes.py").exists()
    assert Path("runtime/jesse_workspace/config.py").exists()
    assert Path("runtime/jesse_workspace/strategies").exists()
```

- [ ] **Step 2: 运行测试确认红灯**

Run:

```bash
source .venv/bin/activate && python3 -m pytest tests/test_jesse_runtime_files.py -q
```

Expected: FAIL because runtime files do not exist yet.

- [ ] **Step 3: 创建 Jesse runtime 最小基础结构**

最小要求：

- 有 `routes.py`
- 有 `config.py`
- 有 `strategies/`
- 有 `storage/`

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
source .venv/bin/activate && python3 -m pytest tests/test_jesse_runtime_files.py -q
```

Expected: PASS.

### Task 3: 把真实 `Ott2butKAMA` 策略源码纳入新项目

**Files:**
- Create: `strategies/jesse/Ott2butKAMA/__init__.py`
- Create: `tests/test_ott2butkama_import.py`
- Test: `tests/test_ott2butkama_strategy_presence.py`

- [ ] **Step 1: 写失败测试，验证项目内策略文件存在**

```python
from pathlib import Path


def test_project_has_ott2butkama_strategy_source():
    assert Path("strategies/jesse/Ott2butKAMA/__init__.py").exists()
```

- [ ] **Step 2: 运行测试确认红灯**

Run:

```bash
source .venv/bin/activate && python3 -m pytest tests/test_ott2butkama_strategy_presence.py -q
```

Expected: FAIL because the strategy source file does not exist.

- [ ] **Step 3: 放入真实 `Ott2butKAMA` 策略源码，而不是占位版本**

最小要求：

- 文件存在
- 包含真实策略类定义
- 能被 Python 成功 import

```python
from strategies.jesse.Ott2butKAMA import Ott2butKAMA


def test_project_can_import_ott2butkama_strategy():
    assert Ott2butKAMA is not None
```

- [ ] **Step 4: 运行存在性测试和 import 测试确认通过**

Run:

```bash
source .venv/bin/activate && python3 -m pytest tests/test_ott2butkama_strategy_presence.py tests/test_ott2butkama_import.py -q
```

Expected: PASS.

### Task 4: 新增 Jesse 桥接辅助函数

**Files:**
- Create: `apps/signal_service/jesse_bridge/emitter.py`
- Test: `tests/test_jesse_bridge.py`

- [ ] **Step 1: 写失败测试，验证 K 线时间转换与 signal emit 调用参数**

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

Expected: FAIL because emitter module does not exist.

- [ ] **Step 3: 实现最小桥接辅助函数**

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

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
source .venv/bin/activate && python3 -m pytest tests/test_jesse_bridge.py -q
```

Expected: PASS.

### Task 5: 增加策略同步脚本

**Files:**
- Create: `scripts/sync_jesse_strategy.py`
- Test: `tests/test_sync_jesse_strategy.py`

- [ ] **Step 1: 写失败测试，验证同步目标路径构造函数存在**

```python
from scripts.sync_jesse_strategy import build_target_path


def test_build_target_path_points_into_runtime_workspace():
    path = build_target_path("Ott2butKAMA")
    assert "runtime/jesse_workspace/strategies/Ott2butKAMA" in str(path)
```

- [ ] **Step 2: 运行测试确认红灯**

Run:

```bash
source .venv/bin/activate && python3 -m pytest tests/test_sync_jesse_strategy.py -q
```

Expected: FAIL because sync script does not exist.

- [ ] **Step 3: 实现最小同步脚本**

最小要求：

- 源路径：`strategies/jesse/<strategy_name>/`
- 目标路径：`runtime/jesse_workspace/strategies/<strategy_name>/`
- 覆盖复制
- 如果目标目录存在，先清空再复制
- 自动创建 `runtime/jesse_workspace/strategies/`
- 同步整个策略目录，不只同步单文件

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
source .venv/bin/activate && python3 -m pytest tests/test_sync_jesse_strategy.py -q
```

Expected: PASS.

### Task 6: 为 `Ott2butKAMA` 预留信号接入点说明并更新 runbook

**Files:**
- Modify: `docs/runbook.md`
- Modify: `docs/embedded-jesse-runtime-design.md`
- Create: `tests/test_jesse_runtime_import_path.py`

- [ ] **Step 1: 在 runbook 中加入 Jesse runtime 使用步骤**

至少包括：

- 同步策略到 runtime
- Jesse runtime 的位置
- Jesse 信号桥接的目标模块

- [ ] **Step 2: 在设计文档中补充第一阶段真实接入对象说明**

明确：

- 首个接入策略是 `Ott2butKAMA`
- 第一阶段先支持开仓和平仓信号写入

- [ ] **Step 3: 新增 Jesse runtime 级 import 验证**

至少验证：

- `runtime/jesse_workspace` 路径下能 import 到同步后的策略
- Jesse runtime 可以 import 新项目桥接模块

- [ ] **Step 4: 运行全部测试**

Run:

```bash
source .venv/bin/activate && python3 -m pytest tests -q
```

Expected: PASS.

- [ ] **Step 5: 查看最终仓库状态**

Run:

```bash
git status --short
```

Expected: only intended files changed.
