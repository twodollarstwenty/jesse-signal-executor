# Jesse Signal Executor 第一阶段实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 `jesse-signal-executor` 搭建第一阶段可运行骨架，使其具备 Jesse 信号写库、Executor 规则判定、PostgreSQL 状态初始化和 Docker Compose 启动基础。

**Architecture:** 先完成最小可运行闭环，不引入真实交易所执行。项目分为 `signal-service`、`executor-service`、`postgres` 三个核心部分，使用数据库记录信号、执行和仓位状态，使用治理层约束后续迭代方式。第一阶段只实现 dry-run 风格基础设施和最小逻辑路径。

**Tech Stack:** Python 3.11, Docker Compose, PostgreSQL, psycopg2, pydantic, pytest

---

### Task 1: 增加项目结构测试并补齐最小代码目录

**Files:**
- Create: `tests/test_project_layout.py`
- Create: `apps/signal_service/main.py`
- Create: `apps/executor_service/main.py`
- Create: `apps/shared/settings.py`

- [ ] **Step 1: 写失败测试，验证关键文件存在**

```python
from pathlib import Path


def test_project_runtime_files_exist():
    assert Path("apps/signal_service/main.py").exists()
    assert Path("apps/executor_service/main.py").exists()
    assert Path("apps/shared/settings.py").exists()
```

- [ ] **Step 2: 运行测试确认红灯**

Run:

```bash
python3 -m pytest tests/test_project_layout.py -q
```

Expected: FAIL because runtime files do not exist yet.

- [ ] **Step 3: 创建最小服务入口和共享配置文件**

```python
# apps/shared/settings.py
from pydantic import BaseModel


class Settings(BaseModel):
    exchange: str = "binance_perpetual_futures"
    execution_mode: str = "dry_run"
    default_symbol: str = "ETHUSDT"
```
```

```python
# apps/signal_service/main.py
from apps.shared.settings import Settings


def main() -> None:
    settings = Settings()
    print(f"signal-service ready for {settings.default_symbol}")


if __name__ == "__main__":
    main()
```
```

```python
# apps/executor_service/main.py
from apps.shared.settings import Settings


def main() -> None:
    settings = Settings()
    print(f"executor-service ready in {settings.execution_mode}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
python3 -m pytest tests/test_project_layout.py -q
```

Expected: PASS.

### Task 2: 建立数据库初始化 SQL 和初始化脚本

**Files:**
- Create: `db/init.sql`
- Create: `scripts/init_db.py`
- Create: `tests/test_db_init.py`

- [ ] **Step 1: 写失败测试，验证三张核心表存在于 SQL 文件**

```python
from pathlib import Path


def test_db_init_sql_contains_core_tables():
    sql = Path("db/init.sql").read_text()
    assert "CREATE TABLE IF NOT EXISTS signals" in sql
    assert "CREATE TABLE IF NOT EXISTS executions" in sql
    assert "CREATE TABLE IF NOT EXISTS positions" in sql
```

- [ ] **Step 2: 运行测试确认红灯**

Run:

```bash
python3 -m pytest tests/test_db_init.py -q
```

Expected: FAIL because `db/init.sql` does not exist yet.

- [ ] **Step 3: 创建最小 SQL 和初始化脚本**

```sql
CREATE TABLE IF NOT EXISTS signals (
  id BIGSERIAL PRIMARY KEY,
  strategy TEXT NOT NULL,
  symbol TEXT NOT NULL,
  timeframe TEXT NOT NULL,
  signal_time TIMESTAMPTZ NOT NULL,
  action TEXT NOT NULL,
  signal_hash TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL,
  payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS executions (
  id BIGSERIAL PRIMARY KEY,
  signal_id BIGINT NOT NULL REFERENCES signals(id) ON DELETE RESTRICT,
  symbol TEXT NOT NULL,
  side TEXT NOT NULL,
  mode TEXT NOT NULL,
  status TEXT NOT NULL,
  detail_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS positions (
  id BIGSERIAL PRIMARY KEY,
  symbol TEXT NOT NULL,
  side TEXT,
  qty NUMERIC NOT NULL,
  entry_price NUMERIC,
  state_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

```python
import os
from pathlib import Path

import psycopg2


def main() -> None:
    sql = Path("db/init.sql").read_text()
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "jesse_signal_executor"),
        user=os.getenv("POSTGRES_USER", "app_user"),
        password=os.getenv("POSTGRES_PASSWORD", "app_password"),
    )
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
python3 -m pytest tests/test_db_init.py -q
```

Expected: PASS.

### Task 3: 实现 Signal Service 最小信号模型与 hash 工具

**Files:**
- Create: `apps/signal_service/models.py`
- Create: `apps/signal_service/writer.py`
- Create: `tests/test_signal_writer.py`

- [ ] **Step 1: 写失败测试，验证 signal hash 幂等**

```python
from apps.signal_service.writer import build_signal_hash


def test_signal_hash_is_deterministic():
    payload = dict(
        strategy="Ott2butKAMA",
        symbol="ETHUSDT",
        timeframe="5m",
        signal_time="2026-04-04T00:00:00Z",
        action="open_long",
    )
    assert build_signal_hash(**payload) == build_signal_hash(**payload)
```

- [ ] **Step 2: 运行测试确认红灯**

Run:

```bash
python3 -m pytest tests/test_signal_writer.py -q
```

Expected: FAIL because writer does not exist.

- [ ] **Step 3: 实现最小模型和 hash 工具**

```python
import hashlib
from pydantic import BaseModel


class Signal(BaseModel):
    strategy: str
    symbol: str
    timeframe: str
    signal_time: str
    action: str
    payload: dict = {}


def build_signal_hash(*, strategy: str, symbol: str, timeframe: str, signal_time: str, action: str) -> str:
    payload = f"{strategy}|{symbol}|{timeframe}|{signal_time}|{action}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
python3 -m pytest tests/test_signal_writer.py -q
```

Expected: PASS.

### Task 4: 实现 Executor 最小规则引擎

**Files:**
- Create: `apps/executor_service/rules.py`
- Create: `tests/test_executor_rules.py`

- [ ] **Step 1: 写失败测试，验证单仓位规则**

```python
from apps.executor_service.rules import decide_action


def test_same_side_signal_is_ignored():
    assert decide_action("open_long", "long") == "ignored"


def test_reverse_side_signal_is_rejected():
    assert decide_action("open_long", "short") == "rejected"
```

- [ ] **Step 2: 运行测试确认红灯**

Run:

```bash
python3 -m pytest tests/test_executor_rules.py -q
```

Expected: FAIL because rules file does not exist.

- [ ] **Step 3: 实现最小规则函数**

```python
def decide_action(signal_action: str, current_side: str | None) -> str:
    if signal_action == "open_long":
        if current_side == "long":
            return "ignored"
        if current_side == "short":
            return "rejected"
        return "execute"

    if signal_action == "open_short":
        if current_side == "short":
            return "ignored"
        if current_side == "long":
            return "rejected"
        return "execute"

    if signal_action in {"close_long", "close_short", "flat"}:
        return "execute"

    return "rejected"
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
python3 -m pytest tests/test_executor_rules.py -q
```

Expected: PASS.

### Task 5: 增加最小运维脚本与运行手册

**Files:**
- Create: `scripts/start.sh`
- Create: `scripts/stop.sh`
- Create: `scripts/status.sh`
- Create: `scripts/close_only.sh`
- Create: `docs/runbook.md`

- [ ] **Step 1: 编写最小运行手册**

```markdown
# Runbook

## 初始化
- 复制 `.env.example` 为 `.env`
- 启动 `docker compose up -d`

## 启动
- `bash scripts/start.sh`

## 停止
- `bash scripts/stop.sh`

## 状态
- `bash scripts/status.sh`

## 切换只平不开
- `bash scripts/close_only.sh on`
- `bash scripts/close_only.sh off`
```

- [ ] **Step 2: 实现最小脚本**

```bash
#!/usr/bin/env bash
docker compose up -d
```

```bash
#!/usr/bin/env bash
docker compose down
```

```bash
#!/usr/bin/env bash
docker compose ps
```

```bash
#!/usr/bin/env bash
echo "close_only=$1"
```

- [ ] **Step 3: 手动验证状态脚本**

Run:

```bash
bash scripts/status.sh
```

Expected: exits successfully and prints compose status.

### Task 6: 最终验证骨架可运行性

**Files:**
- No new files required

- [ ] **Step 1: 运行全部测试**

Run:

```bash
python3 -m pytest tests -q
```

Expected: PASS.

- [ ] **Step 2: 运行 compose 配置校验**

Run:

```bash
docker compose config
```

Expected: valid compose configuration output.

- [ ] **Step 3: 查看最终变更状态**

Run:

```bash
git status --short
```

Expected: only intended project files are changed.
