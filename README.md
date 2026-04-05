# jesse-signal-executor

一个独立的新项目，用于搭建 `Jesse 信号 + Executor 模拟执行` 的 Binance Perpetual Futures 自动交易闭环。

当前活跃阶段路径：`backtest -> dry-run -> tiny live`

当前仓库回测脚本与 Jesse runtime 的默认杠杆基线为 `10x`。

## 第一阶段目标

- 使用 Jesse 作为策略信号来源
- 使用独立 Executor 进行 dry-run / paper 模拟执行，并为 tiny live 提供验证依据
- 使用 PostgreSQL 记录信号、执行、仓位和状态
- 使用 Docker Compose 作为标准运行方式

## 当前阶段不做

- 多交易所
- 多策略并发
- 分批止盈
- 非 tiny-live 范围的真实资金自动交易
- Web UI

## 目录说明

- `apps/`：服务代码
- `db/`：数据库初始化与迁移
- `infra/docker/`：容器相关文件
- `configs/`：环境配置
- `rules/`：强制规则
- `skills/`：AI 可执行工作流
- `scripts/`：运维脚本
- `docs/`：项目文档

## 启动方式

后续通过 `docker compose up -d` 运行。

## Dry-Run Quick Start

最小启动流程：

```bash
cp .env.example .env
# 按实际环境修改 .env

source .venv/bin/activate
python3 scripts/init_db.py

set -a && source .env && set +a
bash scripts/dryrun_start.sh
bash scripts/dryrun_status.sh
python3 scripts/summarize_dryrun_validation.py --minutes 60
```

查看日志：

```bash
python3 - <<'PY'
from pathlib import Path
for name in ["executor.log", "jesse-dryrun.log"]:
    path = Path("runtime/dryrun/logs") / name
    print(f"\n===== {name} =====")
    if path.exists():
        print(path.read_text()[-4000:])
    else:
        print("missing")
PY
```

停止：

```bash
bash scripts/dryrun_stop.sh
```
