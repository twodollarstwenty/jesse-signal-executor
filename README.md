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
PGPASSWORD=password psql -h 127.0.0.1 -p 5432 -U jesse_user -d jesse_db -f db/init.sql
bash scripts/dryrun_start.sh
bash scripts/dryrun_status.sh
```

查看 worker 日志：

```bash
python3 - <<'PY'
from pathlib import Path
path = Path("runtime/dryrun/instances/ott_eth_5m/logs/worker.log")
print(path.read_text()[-4000:] if path.exists() else "missing")
PY
```

验证 decision trace 是否写入数据库：

```bash
PGPASSWORD=password psql -h 127.0.0.1 -p 5432 -U jesse_user -d jesse_db -c "select id, instance_id, strategy, symbol, timeframe, signal_time, candle_timestamp, intent, action, emitted, decision_status, reason_code from signal_decision_events order by id desc limit 20;"
```

只看总数：

```bash
PGPASSWORD=password psql -h 127.0.0.1 -p 5432 -U jesse_user -d jesse_db -c "select count(*) from signal_decision_events;"
```

停止：

```bash
bash scripts/dryrun_stop.sh
```
