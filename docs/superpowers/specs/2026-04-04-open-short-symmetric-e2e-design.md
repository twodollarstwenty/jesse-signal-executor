# Open Short 对称 E2E 覆盖设计

## 背景

当前项目已覆盖以下端到端状态路径：

- `open_long + current_side=long` -> `ignored`
- `open_long + current_side=short` -> `rejected`

但 `open_short` 的对称路径尚未进入 E2E 回归范围，导致状态机覆盖不完整。

## 目标

在不扩大范围、不改业务逻辑的前提下，补齐 `open_short` 的对称 E2E 覆盖，确保 `ignored/rejected` 在 long/short 两个开仓方向上都可回归验证。

## 范围

### In Scope

- 在现有 `tests/test_executor_ignored_rejected_e2e.py` 中新增 2 条测试。
- 覆盖 `open_short` 的 `ignored/rejected` 对称路径。
- 复用当前测试基建、断言口径和并行策略。

### Out of Scope

- 不新增 `close_long/close_short` 行为测试。
- 不调整 executor 判定规则。
- 不做测试隔离架构重构（schema/事务）。

## 方案选择

候选方案：

1. 在现有 E2E 文件上补两条对称用例（采用）
2. 拆新文件单独放 open_short 测试
3. 合并为参数化大矩阵（一次重构）

采用方案 1，原因：

- 变更最小，风险最低
- 与现有 open_long 用例对照清晰
- 能快速把覆盖面补齐

## 设计

### 测试用例

新增以下两条测试：

1. `test_open_short_ignored_when_current_side_is_short`
2. `test_open_short_rejected_when_current_side_is_long`

映射关系：

- `open_short + short` -> `ignored`
- `open_short + long` -> `rejected`

### 测试流程

每条测试流程保持与现有 open_long 用例同构：

1. 环境和 schema 初始化
2. 清理事件与仓位表
3. 写入 `position_state`
4. 写入 `signal_events`（`action=open_short`）
5. 执行 `run_once()`
6. 查询对应 signal/execution 并断言

### 断言口径

保持与现有用例一致：

- `signal.status == expected_status`
- `execution.status == expected_status`
- `execution.mode == "dry_run"`
- `execution.signal_id == signal.id`

### 并行策略

继续沿用当前策略：

- shared-table 清理
- xdist worker 下 skip

不在本轮引入新的隔离机制，避免范围膨胀。

## 验收标准

- 新增两条 `open_short` 对称用例通过。
- `tests/test_executor_ignored_rejected_e2e.py` 全量通过。
- 全项目 `tests` 全量通过，不影响既有 execute 回归。

## 风险与后续

### 风险

- shared-table 模式下并行执行仍有潜在干扰（当前由 skip 缓解）。

### 后续

1. 将 ignored/rejected 全矩阵参数化，减少重复代码。
2. 升级为独立 schema/事务隔离，移除 xdist skip。
3. 再扩展 close 路径覆盖。
