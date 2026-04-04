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

## 最小 DB 闭环

```bash
source .venv/bin/activate
python3 scripts/init_db.py
python3 -m apps.signal_service.cli --strategy Ott2butKAMA --symbol ETHUSDT --timeframe 5m --signal-time 2026-04-04T00:00:00Z --action open_long
python3 -m apps.executor_service.cli
```

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
