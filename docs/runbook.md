# Runbook

默认命令上下文：除非特别说明，以下命令都在仓库根目录执行。

虚拟环境约定：

- 项目级脚本、pytest、数据库初始化等，使用项目虚拟环境：`.venv`。
- Jesse runtime bootstrap 完成后，涉及 `jesse` CLI 或 runtime workspace 依赖的命令，使用 `runtime/jesse_workspace/.venv`。

## 初始化

- 复制 `.env.example` 为 `.env`
- 启动 `docker compose up -d`

## 启动

- `bash scripts/start.sh`

## 停止

- `bash scripts/stop.sh`

## 状态

- `bash scripts/status.sh`

## Docker Dry-Run

该路径会在容器内启动与当前宿主机 dry-run 相同的 runtime model，包括 `executor` 与 `jesse-dryrun` 两个服务。

一键启动：

```bash
docker compose up -d
```

查看状态：

```bash
docker compose ps
```

查看日志：

```bash
docker compose logs -f executor jesse-dryrun
```

停止：

```bash
docker compose down
```

## Non-Container Dry-Run

前提：

- 已完成 Jesse runtime bootstrap。
- 项目虚拟环境 `.venv` 可用，供 `executor` 与 `scripts/check_heartbeat.py` 使用。
- `runtime/jesse_workspace/.venv` 可用，供 `jesse-dryrun` 使用。
- 以下命令默认在仓库根目录执行。
- `dryrun_start.sh` 默认按本机 PostgreSQL 连接启动：`127.0.0.1:5432`，数据库 `jesse_db`，用户 `jesse_user`，密码 `password`；若已设置对应环境变量，则以环境变量覆盖默认值。
- `jesse-dryrun` 默认执行项目内正式信号生产入口，而不是 `scripts/verify_jesse_imports.py` 这类占位检查命令。
- 正式入口会在执行前校验 `runtime/jesse_workspace`、策略同步产物与导入路径，然后通过现有 Jesse bridge 向 `signal_events` 写入真实信号。

启动：

```bash
bash scripts/dryrun_start.sh
```

查看状态：

```bash
bash scripts/dryrun_status.sh
```

状态含义：

- `running`：进程存在，且 heartbeat 在有效时间内。
- `stopped`：进程不存在，或 pid 文件对应进程已失效。
- `stale`：进程仍存在，但 heartbeat 已过期。

停止：

```bash
bash scripts/dryrun_stop.sh
```

运行产物：

- 日志路径：`runtime/dryrun/logs/*.log`
- heartbeat 路径：`runtime/dryrun/heartbeats/*.heartbeat`

排障建议：

- 先执行 `bash scripts/dryrun_status.sh`，确认 `executor` 与 `jesse-dryrun` 的进程状态与 heartbeat 状态。
- 若状态异常，再查看 `runtime/dryrun/logs/*.log` 定位启动失败、退出或连接问题。
- 若进程存活但没有业务流量，继续检查 `signal_events` 与 `execution_events` 是否有新增记录；这是 dry-run 是否真正有效的判定标准之一。

验证摘要：

```bash
source .venv/bin/activate
python3 scripts/summarize_dryrun_validation.py --minutes 60
```

- 该摘要属于 dry-run 验证证据的一部分，也是评估是否可以考虑进入 tiny live 的必备依据之一。

Smoke 验证：

- 当前一次宿主机 smoke 已执行 `bash scripts/dryrun_start.sh`、`bash scripts/dryrun_status.sh`、`bash scripts/dryrun_stop.sh`，结果为启动成功、状态可见、停止成功。

## Jesse Runtime Bootstrap

```bash
source .venv/bin/activate
bash scripts/bootstrap_jesse_runtime.sh
python3 scripts/check_jesse_runtime.py
python3 scripts/verify_jesse_imports.py
```

## Ott2butKAMA 真实信号桥

```bash
source .venv/bin/activate
python3 scripts/sync_jesse_strategy.py
source runtime/jesse_workspace/.venv/bin/activate
python3 scripts/verify_jesse_imports.py
```

说明：

- `Ott2butKAMA` 已通过项目内 bridge 发 `open_long / open_short / close_long / close_short`
- 信号写入目标是 `signal_events`

## Pytest Bridge 回归验收

```bash
.venv/bin/python -m pytest tests/test_ott2butkama_bridge_smoke.py -q
.venv/bin/python -m pytest tests/test_signal_executor_flow.py -q
```

说明：

- pytest 用例是 bridge 回归验收基线
- smoke 脚本 `scripts/smoke_test_ott2butkama_bridge.py` 仅作为开发联调用辅助，不作为验收标准

## 最小 DB 闭环

```bash
source .venv/bin/activate
python3 scripts/init_db.py
python3 -m apps.signal_service.cli --strategy Ott2butKAMA --symbol ETHUSDT --timeframe 5m --signal-time 2026-04-04T00:00:00Z --action open_long
python3 -m apps.executor_service.cli
```

## 切换只平不开

- `bash scripts/close_only.sh on`
- `bash scripts/close_only.sh off`
- 当前项目内可见行为是输出 `close_only=<value>`，用于切换运行时模式；本仓库上下文下未提供额外状态查询脚本。

## Backtest Compare

说明：

- 以下 `baseline==candidate` 命令用于框架 smoke 验收（验证对照流程、日志与报告产物），不用于评估策略优劣。
- 未显式传入 `--leverage` 时，当前默认杠杆基线为 `10`（`10x`）。

执行前检查：

- `jesse` 二进制可用（例如在已激活环境中执行 `jesse --help` 可返回帮助信息）。
- 已激活 runtime 虚拟环境：`source runtime/jesse_workspace/.venv/bin/activate`。

```bash
source runtime/jesse_workspace/.venv/bin/activate
python3 scripts/run_backtest_compare.py \
  --symbol ETHUSDT \
  --timeframe 5m \
  --start 2026-04-01 \
  --end 2026-04-04 \
  --baseline-strategy Ott2butKAMA \
  --candidate-strategy Ott2butKAMA
```

输出：

- 原始日志：`docs/backtests/raw/*.log`
- 对照报告：`docs/backtests/*-compare.md`

失败处理：

- 若运行失败，优先查看失败摘要：`docs/backtests/*-compare-failed.md`。
- 若存在原始日志，检查 `docs/backtests/raw/*.log`；若日志缺失，请直接查看命令终端输出定位失败原因。
