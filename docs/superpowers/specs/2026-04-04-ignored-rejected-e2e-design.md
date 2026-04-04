# Executor Ignored/Rejected E2E 设计

## 背景

当前项目已具备 `execute` 主路径的端到端回归测试（bridge -> signal_events -> executor -> execution_events），但尚未覆盖 `ignored/rejected` 判定路径。

`apps/executor_service/rules.py` 已定义规则：

- `open_long + current_side=long` -> `ignored`
- `open_long + current_side=short` -> `rejected`
- 对称规则适用于 `open_short`

缺口在于 executor 当前 `run_once()` 固定把 `current_side` 视为 `None`，无法在真实链路层触发上述分支。

## 目标

在不扩大系统复杂度的前提下，为 executor 增加最小“当前仓位读取”能力，并补齐 `ignored/rejected` 的端到端测试覆盖，确保状态机关键分支可回归验证。

## 范围

### In Scope

- 在 executor 侧读取 `position_state` 当前 side（`long/short/None`）。
- `run_once()` 将读取到的 `current_side` 传入 `decide_action()`。
- 新增端到端测试覆盖 `ignored/rejected` 两条路径。
- 复用现有测试基建（`tests/db_testkit.py`）与 dry-run 验收口径。

### Out of Scope

- 本轮不引入仓位自动更新逻辑。
- 本轮不扩展至 Jesse 周期驱动入口。
- 本轮不改动 `decide_action()` 规则本身。

## 方案选择

候选方案：

1. 最小侵入：从 `position_state` 读取 `current_side` 并做 E2E（采用）
2. 从历史 `execution_events` 反推持仓
3. 测试专用 `current_side_override` 注入

采用方案 1，原因：

- 最贴近当前数据模型（已有 `position_state`）
- 业务路径自然，不污染生产接口
- 变更面小，适合当前阶段快速固化回归能力

## 设计

### 1. Executor 最小改动

- 在 `apps/executor_service/service.py` 增加一个当前仓位读取函数：
  - 输入：`symbol`
  - 行为：查询 `position_state` 最新记录并返回 `side`
  - 返回值：`"long" | "short" | None`
- `run_once()` 在处理每条 `signal_events` 时，先取 `current_side`，再调用：

```python
decision = decide_action(action, current_side)
```

- 其余处理链路保持不变（更新 signal status + 插入 execution event）。

### 2. E2E 测试矩阵

新增 `tests/test_executor_ignored_rejected_e2e.py`，最小覆盖两条：

1. `open_long` + `position_state.side=long` -> `ignored`
2. `open_long` + `position_state.side=short` -> `rejected`

每条测试流程：

1. `apply_test_db_env()` / `init_db_schema()` / `clear_event_tables()`
2. 向 `position_state` 插入对应 side 的最新记录
3. 写入 `open_long` 信号
4. 执行 `run_once()`
5. 查询对应 signal 与 execution 记录，断言状态

### 3. 断言口径

核心断言：

- `signal_events.status == expected_status`
- `execution_events.status == expected_status`

辅助一致性断言：

- `execution_events.mode == "dry_run"`
- `execution_events.signal_id == signal_events.id`

### 4. 并行策略

与当前 smoke 用例保持一致：

- 使用 shared-table 清理策略
- 在 xdist worker 下 skip，避免并行互相污染

该策略与现有 `test_signal_executor_flow` / `test_ott2butkama_bridge_smoke` 保持一致，先稳定再迭代为更强隔离（独立 schema/事务回滚）。

## 验收标准

- 新增 E2E 测试文件可单独运行且通过。
- `ignored/rejected` 两条路径均有端到端断言。
- 全量 `tests` 保持通过，不影响既有 `execute` 路径测试。

## 风险与后续

### 风险

- 共享表清理导致并行环境下的互相影响（已通过 xdist skip 缓解）。
- 若 `position_state` 数据形态未来变化，当前读取函数需要同步调整。

### 后续自然升级

1. 扩展 `open_short` 对称路径测试。
2. 将测试隔离升级为独立 schema/事务，移除 xdist skip。
3. 接入真实 Jesse 执行周期入口后复用同样断言。
