# AGENTS

## How To Start

在仓库根目录执行。

### 1. 初始化数据库表

```bash
PGPASSWORD=password psql -h 127.0.0.1 -p 5432 -U jesse_user -d jesse_db -f db/init.sql
```

### 2. 启动 dry-run

```bash
bash scripts/dryrun_start.sh
```

### 3. 查看状态

```bash
bash scripts/dryrun_status.sh
```

正常状态示例：

```python
{'supervisor': 'running', 'instances_total': 1, 'instances_running': 1, 'instances_failed': 0}
```

### 4. 查看 worker 日志

```bash
python3 - <<'PY'
from pathlib import Path
path = Path("runtime/dryrun/instances/ott_eth_5m/logs/worker.log")
print(path.read_text()[-4000:] if path.exists() else "missing")
PY
```

### 5. 验证 decision trace 是否写入数据库

```bash
PGPASSWORD=password psql -h 127.0.0.1 -p 5432 -U jesse_user -d jesse_db -c "select id, instance_id, strategy, symbol, timeframe, signal_time, candle_timestamp, intent, action, emitted, decision_status, reason_code from signal_decision_events order by id desc limit 20;"
```

只看总数：

```bash
PGPASSWORD=password psql -h 127.0.0.1 -p 5432 -U jesse_user -d jesse_db -c "select count(*) from signal_decision_events;"
```

### 6. 停止 dry-run

```bash
bash scripts/dryrun_stop.sh
```

## Notes

- 当前 dry-run 主线策略是 `StandardGrid_LightMartingale_v1`。
- 实例配置文件是 `configs/dryrun_instances.yaml`。
- decision trace 表是 `signal_decision_events`。
- 如需强制下一轮重新处理最新 K 线，可重置：

```bash
python3 -c "from pathlib import Path; Path('runtime/dryrun/instances/ott_eth_5m/state/last_candle_ts.txt').write_text('0')"
```
