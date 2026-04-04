# Bridge Smoke Test 固化设计

## 背景与目标

当前项目已经打通 `Ott2butKAMA -> Jesse bridge -> signal_events -> executor -> execution_events` 的最小执行链路，但主要依赖 smoke 脚本手工验证。该方式难以防回归，且问题定位不稳定。

本次目标是把已打通链路固化为可重复、可定位的 pytest 测试，优先覆盖 `execute` 主路径，不在本轮扩展 `ignored/rejected` 业务判定。

## 范围

### In Scope

- 将现有 smoke 核心逻辑迁移为 pytest 集成测试。
- 统一测试前置：测试库环境、DB 初始化、表清理。
- 统一测试执行入口，避免依赖系统 `python3`。
- 验证 bridge 发信号后 executor 能消费并生成 execute 结果。

### Out of Scope

- 接入真实 Jesse 回测/运行周期入口。
- 扩展 `ignored/rejected` 完整路径断言。
- 调整生产运行流程或上线门槛。

## 方案选择

候选方案：

1. 最小固化（仅 execute）
2. 一次补全 execute/ignored/rejected
3. 先接 Jesse 周期入口再回填测试

采用方案 1（最小固化），原因：变更面最小、最快形成回归保护、与当前阶段目标一致。

## 设计

### 测试文件与职责

- 新增 `tests/test_ott2butkama_bridge_smoke.py`。
- 保留 `tests/test_signal_executor_flow.py` 的现有职责（最小 DB 闭环）。
- 新文件专注“bridge 路径不回归”验证，避免职责重叠。

### 测试夹具设计

- `db_env`：注入 `POSTGRES_HOST/PORT/DB/USER/PASSWORD` 测试配置。
- `initialized_db`：执行 `db/init.sql`，确保表结构存在。
- `clean_tables`：每次测试前清理 `execution_events` 与 `signal_events`，保证用例独立性。

关键约束：初始化和清理都在测试进程内完成，不通过 `subprocess + python3` 调脚本。

### execute 主路径用例

主测试：`test_bridge_execute_path_end_to_end`

步骤：

1. 调用 bridge 发射入口发出 `open_long` 信号（`strategy/symbol/timeframe/signal_time/payload`）。
2. 调用 `run_once()` 执行 executor 一次处理。
3. 读取两张事件表最新记录并断言：
   - `signal_events.status == "execute"`
   - `execution_events.status == "execute"`
4. 校验关键业务字段（如 `strategy/symbol/action`）正确落库。

### 失败可定位性

- 断言前先查询最新事件行并保存关键字段。
- 断言失败时输出关键字段，区分：
  - bridge 写入失败
  - executor 判定失败

## 与现有脚本关系

- 保留 `scripts/smoke_test_ott2butkama_bridge.py` 作为开发辅助脚本。
- 该脚本不再作为回归验收标准，回归口径转为 pytest。

## 运行与验收

推荐命令：

```bash
.venv/bin/python -m pytest tests/test_ott2butkama_bridge_smoke.py -q
.venv/bin/python -m pytest tests -q
```

验收标准：

- 新增 smoke 测试单独可跑。
- 全量测试可跑。
- 失败时可明确归因到 bridge 或 executor。

## 风险与后续

### 主要风险

- 测试依赖本地 PostgreSQL 可用。
- 历史数据污染可能影响断言稳定性（通过清表夹具缓解）。

### 后续自然升级

1. 在同一测试框架补 `ignored/rejected` 路径。
2. 接入真实 Jesse 执行周期入口并复用现有断言结构。
