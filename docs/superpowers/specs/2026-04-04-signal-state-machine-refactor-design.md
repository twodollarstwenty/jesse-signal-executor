# Signal State Machine Refactor 设计

## 背景

当前 executor 规则由 `decide_action(signal_action, current_side)` 的条件分支驱动，已覆盖 `open_long/open_short` 的核心判定与 E2E 验证。但随着 `close_long/close_short/flat` 语义扩展，分支逻辑可维护性下降，且状态转移语义没有被显式建模。

本轮目标是将信号判定升级为完整状态机（state transition matrix），并补齐 close 路径的端到端覆盖。

## 目标

- 用显式状态机替代散落条件分支。
- 对 `(current_side, signal_action)` 的每个组合给出确定输出。
- 把“判定（decision）”与“状态更新（next_state）”分离。
- 补齐 close 路径 E2E，保证 open/close/flat 行为可回归。

## 范围

### In Scope

- 引入状态机模块（矩阵 + 纯函数）。
- executor `run_once()` 接入状态机结果。
- 在 `execute` 时更新 `position_state` 到 next_state。
- 单元测试覆盖全部组合（15 组）。
- E2E 新增 close 路径至少 6 条测试。

### Out of Scope

- 不新增动作类型（如 reverse_*）。
- 不改 backtest compare 执行框架。
- 不做数据库 schema 变更。

## 状态机定义

### 状态

- `flat`
- `long`
- `short`

### 事件

- `open_long`
- `open_short`
- `close_long`
- `close_short`
- `flat`

### 输出

- `decision`: `execute | ignored | rejected`
- `next_state`: `flat | long | short`（仅 `decision=execute` 时用于落库）

## 状态转移矩阵

### current_side = flat

- `open_long -> execute`, next=`long`
- `open_short -> execute`, next=`short`
- `close_long -> ignored`, next=`flat`
- `close_short -> ignored`, next=`flat`
- `flat -> ignored`, next=`flat`

### current_side = long

- `open_long -> ignored`, next=`long`
- `open_short -> rejected`, next=`long`
- `close_long -> execute`, next=`flat`
- `close_short -> rejected`, next=`long`
- `flat -> execute`, next=`flat`

### current_side = short

- `open_short -> ignored`, next=`short`
- `open_long -> rejected`, next=`short`
- `close_short -> execute`, next=`flat`
- `close_long -> rejected`, next=`short`
- `flat -> execute`, next=`flat`

## 架构与职责

### 状态机模块（纯逻辑）

- 新模块承载 transition matrix。
- 提供纯函数：输入 `current_side + signal_action`，输出 `decision + next_state`。
- 该层不依赖 DB，不做副作用，便于参数化全覆盖测试。

### executor service（应用层）

- `run_once()` 继续负责：取事件、调用状态机、写结果。
- `decision=execute` 且 next_state 变化时，更新 `position_state`。
- 非 execute 不更新仓位状态，仅记录事件。

## 测试策略

### 1. 单元测试（状态机）

- 新增参数化测试，覆盖 3 状态 x 5 事件 = 15 组合。
- 每组断言：`decision` 和 `next_state`。
- 这是语义唯一来源，防止后续分支漂移。

### 2. 端到端测试（executor + DB）

在现有 ignored/rejected E2E 文件中新增 close 用例，至少包括：

1. `close_long` on `long` -> `execute` 且状态落 `flat`
2. `close_long` on `flat` -> `ignored`
3. `close_long` on `short` -> `rejected`
4. `close_short` on `short` -> `execute` 且状态落 `flat`
5. `close_short` on `flat` -> `ignored`
6. `close_short` on `long` -> `rejected`

并继续校验：

- `signal_events.status`
- `execution_events.status`
- `execution_events.mode == dry_run`
- `execution_events.signal_id == signal.id`

## 验收标准

- 状态机单元测试全通过（15 组合）。
- close 路径新增 E2E 用例全部通过。
- 既有 open 路径与 bridge/backtest compare 流程不回归。
- 全量 `tests` 通过。

## 风险与缓解

### 风险

- 状态机映射一旦定义错误，会系统性影响判定结果。
- 兼容旧语义时可能出现预期不一致（尤其 close 行为）。

### 缓解

- 以参数化全矩阵测试作为唯一语义护栏。
- 优先保留 open 现有语义不变，close 变更通过新增 E2E 明确化。

## 后续

1. 在状态机基础上扩展 reverse_* 或 reduce_* 动作。
2. 将回测 compare 报告增加状态分布统计（execute/ignored/rejected 占比）。
3. 当状态机稳定后再考虑配置化规则。
