# Jesse Runtime Bootstrap 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `jesse-signal-executor` 内部建立一个可验证的最小 Jesse runtime 基础环境，为后续接入真实 `Ott2butKAMA` 信号做准备。

**Architecture:** 本阶段不直接接策略信号，只建立运行时基础：目录结构、独立 venv、依赖安装脚本、运行时环境检测脚本和 import 验证脚本。目标是把“Jesse 是否可运行”这件事先单独证明，再进入策略接入。

**Tech Stack:** Python 3.11, virtualenv, Jesse, TA-Lib, shell scripts, pytest

---

### Task 1: 补运行时结构测试与基础文件

**Files:**
- Create: `tests/test_jesse_runtime_bootstrap_layout.py`
- Create: `runtime/jesse_workspace/requirements.txt`
- Create: `runtime/jesse_workspace/.env.example`

- [ ] **Step 1: 写失败测试，验证 runtime bootstrap 关键文件存在**

```python
from pathlib import Path


def test_jesse_runtime_bootstrap_files_exist():
    assert Path("runtime/jesse_workspace/requirements.txt").exists()
    assert Path("runtime/jesse_workspace/.env.example").exists()
```

- [ ] **Step 2: 运行测试确认红灯**

Run:

```bash
source .venv/bin/activate && python3 -m pytest tests/test_jesse_runtime_bootstrap_layout.py -q
```

Expected: FAIL because bootstrap files do not exist yet.

- [ ] **Step 3: 增加最小 runtime 文件**

`requirements.txt` 至少包含：

- `jesse`
- `TA-Lib`

`.env.example` 至少包含：

- PostgreSQL 连接配置
- Redis 连接配置
- Jesse 运行所需基础配置占位

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
source .venv/bin/activate && python3 -m pytest tests/test_jesse_runtime_bootstrap_layout.py -q
```

Expected: PASS.

### Task 2: 增加 Jesse runtime 独立 venv bootstrap 脚本

**Files:**
- Create: `scripts/bootstrap_jesse_runtime.sh`
- Test: `tests/test_bootstrap_jesse_runtime_script.py`

- [ ] **Step 1: 写失败测试，验证 bootstrap 脚本存在且可读**

```python
from pathlib import Path


def test_bootstrap_jesse_runtime_script_exists():
    path = Path("scripts/bootstrap_jesse_runtime.sh")
    assert path.exists()
    assert path.read_text().startswith("#!/usr/bin/env bash")
```

- [ ] **Step 2: 运行测试确认红灯**

Run:

```bash
source .venv/bin/activate && python3 -m pytest tests/test_bootstrap_jesse_runtime_script.py -q
```

Expected: FAIL because script does not exist.

- [ ] **Step 3: 实现最小 bootstrap 脚本**

脚本要求：

- 在 `runtime/jesse_workspace/.venv` 创建独立虚拟环境
- 安装 `runtime/jesse_workspace/requirements.txt`
- 输出成功提示

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
source .venv/bin/activate && python3 -m pytest tests/test_bootstrap_jesse_runtime_script.py -q
```

Expected: PASS.

### Task 3: 增加 Jesse runtime 环境检查脚本

**Files:**
- Create: `scripts/check_jesse_runtime.py`
- Test: `tests/test_check_jesse_runtime_script.py`

- [ ] **Step 1: 写失败测试，验证环境检查脚本存在**

```python
from pathlib import Path


def test_check_jesse_runtime_script_exists():
    assert Path("scripts/check_jesse_runtime.py").exists()
```

- [ ] **Step 2: 运行测试确认红灯**

Run:

```bash
source .venv/bin/activate && python3 -m pytest tests/test_check_jesse_runtime_script.py -q
```

Expected: FAIL because script does not exist.

- [ ] **Step 3: 实现最小 runtime 检查脚本**

检查内容至少包括：

- Jesse 是否可导入
- talib 是否可导入
- runtime venv 是否存在

输出要求：

- `jesse_ok=true/false`
- `talib_ok=true/false`
- `venv_ok=true/false`

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
source .venv/bin/activate && python3 -m pytest tests/test_check_jesse_runtime_script.py -q
```

Expected: PASS.

### Task 4: 增加 runtime import 验证脚本

**Files:**
- Create: `scripts/verify_jesse_imports.py`
- Test: `tests/test_verify_jesse_imports_script.py`

- [ ] **Step 1: 写失败测试，验证 import 验证脚本存在**

```python
from pathlib import Path


def test_verify_jesse_imports_script_exists():
    assert Path("scripts/verify_jesse_imports.py").exists()
```

- [ ] **Step 2: 运行测试确认红灯**

Run:

```bash
source .venv/bin/activate && python3 -m pytest tests/test_verify_jesse_imports_script.py -q
```

Expected: FAIL because script does not exist.

- [ ] **Step 3: 实现最小 import 验证脚本**

脚本要求：

- 从 Jesse runtime 环境执行
- 检查：
  - `import jesse`
  - `import talib`
- 输出明确结果

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
source .venv/bin/activate && python3 -m pytest tests/test_verify_jesse_imports_script.py -q
```

Expected: PASS.

### Task 5: 更新 runbook 并做最终验证

**Files:**
- Modify: `docs/runbook.md`

- [ ] **Step 1: 在 runbook 中增加 Jesse runtime bootstrap 步骤**

至少包括：

- 如何创建 Jesse runtime venv
- 如何安装 Jesse 依赖
- 如何运行环境检查脚本

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
