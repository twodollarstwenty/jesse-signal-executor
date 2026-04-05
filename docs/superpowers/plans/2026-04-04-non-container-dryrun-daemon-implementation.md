# Non-Container Dry-Run Daemon Implementation Plan

> Superseded by `docs/superpowers/plans/2026-04-05-final-jesse-dryrun-daemon-implementation.md`. Keep this file as historical implementation context only.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 以宿主机双进程守护方式运行 Jesse dry-run 与 executor loop，并提供 start/stop/status/log/heartbeat 基础运维能力。

**Architecture:** 复用现有 `run_executor_loop.py` 与 `run_jesse_dryrun_loop.py` 作为长期进程核心，新增 shell 启停状态脚本管理两个后台进程，并将 pid/log/heartbeat 统一放到 `runtime/dryrun/`。通过心跳与 DB 事件增长双重验证运行状态，完全不依赖 Docker。

**Tech Stack:** Bash, Python 3.11+, pytest, PostgreSQL, Jesse runtime workspace

---

## File Structure

- Create: `scripts/dryrun_start.sh`
  - 责任：启动 executor / jesse-dryrun 两个后台进程并写 pid/log/heartbeat 路径。
- Create: `scripts/dryrun_stop.sh`
  - 责任：停止两个后台进程并清理失效 pid。
- Create: `scripts/dryrun_status.sh`
  - 责任：展示进程存活与 heartbeat 状态。
- Modify: `scripts/run_executor_loop.py`
  - 责任：确保支持可配置 heartbeat 路径与轮询间隔，便于 daemon 管理。
- Modify: `scripts/run_jesse_dryrun_loop.py`
  - 责任：确保支持可配置 heartbeat 路径、命令与间隔，便于 daemon 管理。
- Create: `tests/test_dryrun_daemon_scripts.py`
  - 责任：验证 shell 脚本对 runtime/dryrun 路径、pid/heartbeat/log 的行为。
- Modify: `docs/runbook.md`
  - 责任：新增非容器 dry-run 启停与排障步骤。

### Task 1: 先写 dry-run 守护脚本测试（红灯）

**Files:**
- Create: `tests/test_dryrun_daemon_scripts.py`

- [ ] **Step 1: 写失败测试文件**

创建 `tests/test_dryrun_daemon_scripts.py`：

```python
from pathlib import Path


def test_dryrun_start_script_exists():
    assert Path("scripts/dryrun_start.sh").exists()


def test_dryrun_stop_script_exists():
    assert Path("scripts/dryrun_stop.sh").exists()


def test_dryrun_status_script_exists():
    assert Path("scripts/dryrun_status.sh").exists()
```

- [ ] **Step 2: 运行测试确认红灯**

Run:

```bash
.venv/bin/python -m pytest tests/test_dryrun_daemon_scripts.py -q
```

Expected: FAIL（脚本尚不存在）。

- [ ] **Step 3: Commit 红灯测试**

```bash
git add tests/test_dryrun_daemon_scripts.py
git commit -m "test: add failing coverage for dryrun daemon shell scripts"
```

### Task 2: 实现 start/stop/status 脚本最小骨架

**Files:**
- Create: `scripts/dryrun_start.sh`
- Create: `scripts/dryrun_stop.sh`
- Create: `scripts/dryrun_status.sh`
- Test: `tests/test_dryrun_daemon_scripts.py`

- [ ] **Step 1: 实现脚本文件最小骨架**

创建 `scripts/dryrun_start.sh`：

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
RUNTIME_DIR="${REPO_ROOT}/runtime/dryrun"

mkdir -p "${RUNTIME_DIR}/pids" "${RUNTIME_DIR}/logs" "${RUNTIME_DIR}/heartbeats"
```

创建 `scripts/dryrun_stop.sh`：

```bash
#!/usr/bin/env bash
set -euo pipefail
```

创建 `scripts/dryrun_status.sh`：

```bash
#!/usr/bin/env bash
set -euo pipefail
```

- [ ] **Step 2: 运行测试确认转绿**

Run:

```bash
.venv/bin/python -m pytest tests/test_dryrun_daemon_scripts.py -q
```

Expected: PASS。

- [ ] **Step 3: Commit 脚本骨架**

```bash
git add scripts/dryrun_start.sh scripts/dryrun_stop.sh scripts/dryrun_status.sh tests/test_dryrun_daemon_scripts.py
git commit -m "feat: add dryrun daemon shell script skeletons"
```

### Task 3: 扩展脚本为双进程守护控制

**Files:**
- Modify: `scripts/dryrun_start.sh`
- Modify: `scripts/dryrun_stop.sh`
- Modify: `scripts/dryrun_status.sh`
- Modify: `tests/test_dryrun_daemon_scripts.py`

- [ ] **Step 1: 为启动脚本补行为测试（先红灯）**

在 `tests/test_dryrun_daemon_scripts.py` 追加：

```python
import subprocess


def test_dryrun_start_script_creates_runtime_directories(tmp_path):
    script = Path("scripts/dryrun_start.sh")
    runtime_root = tmp_path / "runtime-root"

    completed = subprocess.run(
        ["bash", str(script)],
        env={"DRYRUN_RUNTIME_DIR": str(runtime_root)},
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert (runtime_root / "pids").exists()
    assert (runtime_root / "logs").exists()
    assert (runtime_root / "heartbeats").exists()
```

- [ ] **Step 2: 运行测试确认红灯**

Run:

```bash
.venv/bin/python -m pytest tests/test_dryrun_daemon_scripts.py -q
```

Expected: FAIL（当前脚本未支持 `DRYRUN_RUNTIME_DIR`）。

- [ ] **Step 3: 实现启动/停止/状态逻辑**

实现目标：

- `dryrun_start.sh`
  - 支持 `DRYRUN_RUNTIME_DIR` 覆盖默认目录
  - 使用项目 `.venv/bin/python` 启动 `run_executor_loop.py`
  - 使用 `runtime/jesse_workspace/.venv/bin/python` 启动 `run_jesse_dryrun_loop.py`
  - stdout/stderr 写入各自 log
  - pid 写入各自 pid 文件

- `dryrun_stop.sh`
  - 读取 pid 文件
  - 若进程存在则 `kill`
  - 清理无效 pid 文件

- `dryrun_status.sh`
  - 输出 executor / jesse-dryrun 的 pid、running/stopped/stale 状态
  - 基于 heartbeat 路径调用 `scripts/check_heartbeat.py`

- [ ] **Step 4: 运行脚本测试确认通过**

Run:

```bash
.venv/bin/python -m pytest tests/test_dryrun_daemon_scripts.py -q
```

Expected: PASS。

- [ ] **Step 5: Commit 守护控制逻辑**

```bash
git add scripts/dryrun_start.sh scripts/dryrun_stop.sh scripts/dryrun_status.sh tests/test_dryrun_daemon_scripts.py
git commit -m "feat: add non-container dryrun daemon control scripts"
```

### Task 4: 更新 runbook 并做宿主机 smoke 验收

**Files:**
- Modify: `docs/runbook.md`

- [ ] **Step 1: 新增 non-container dry-run 段落**

在 `docs/runbook.md` 中新增：

- `bash scripts/dryrun_start.sh`
- `bash scripts/dryrun_status.sh`
- `bash scripts/dryrun_stop.sh`
- 日志路径：`runtime/dryrun/logs/*.log`
- heartbeat 路径：`runtime/dryrun/heartbeats/*.heartbeat`
- 排障路径：先看 status，再看 logs，再看 `signal_events` / `execution_events`

- [ ] **Step 2: 执行宿主机 smoke 验收**

Run:

```bash
bash scripts/dryrun_start.sh
bash scripts/dryrun_status.sh
bash scripts/dryrun_stop.sh
```

Expected:

- start 成功
- status 输出两个进程状态
- stop 成功清理进程

- [ ] **Step 3: Commit runbook 与 smoke 验证结果**

```bash
git add docs/runbook.md
git commit -m "docs: add non-container dryrun daemon workflow"
```

### Task 5: 全量验证与工作区检查

**Files:**
- No additional files required

- [ ] **Step 1: 运行全量测试**

Run:

```bash
.venv/bin/python -m pytest tests -q
```

Expected: PASS。

- [ ] **Step 2: 检查工作区状态**

Run:

```bash
git status --short
```

Expected: 仅出现本计划相关改动。

## Self-Review

- Spec coverage: 覆盖了双进程 shell 管理、运行态目录、runbook、宿主机 smoke 验收。
- Placeholder scan: 无 TBD/TODO 占位；步骤含具体文件、命令与预期。
- Type consistency: `dryrun_start/stop/status`、`runtime/dryrun`、heartbeat/pid/log 命名一致。
