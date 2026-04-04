# 最小 DB 闭环设计文档

## 目标

在当前仓库骨架基础上，把系统从“只有结构”推进到“能跑通一条信号生命周期”的最小闭环。

本阶段只关注数据库内的信号流转，不接入真实交易所，也不做真实仓位同步。

## 范围

本阶段范围内：

- `signal-service` 增加 CLI 写信号入口
- `executor-service` 增加 CLI 消费一条信号入口
- `signals.status` 更新为决策结果
- 写入一条模拟 `executions` 记录
- 通过集成测试验证 DB 内闭环

本阶段范围外：

- Binance API
- ccxt
- 真实撮合
- 持续轮询守护进程
- 多信号批量处理
- `positions` 的真实状态管理

## 推荐实现方式

推荐采用：

- `signal-service CLI + executor-service CLI + PostgreSQL`

原因：

- 复杂度最低
- 最容易调试
- 可以最快验证信号生命周期设计是否正确
- 不依赖 Docker 也能先跑通主逻辑

## 设计边界

### `signal-service`

新增一个 CLI 入口，用于手工或脚本写入一条标准化信号。

建议参数：

- `--strategy`
- `--symbol`
- `--timeframe`
- `--signal-time`
- `--action`

CLI 内部调用 `insert_signal(...)`。

### `executor-service`

新增一个 CLI 入口，用于单次消费一条 `status='new'` 的信号。

CLI 内部调用 `run_once()`。

### `service.py` 行为变化

当前 `run_once()` 只更新 `signals.status`。

本阶段升级为：

1. 查询一条 `signals.status='new'`
2. 根据规则计算决策
3. 更新 `signals.status`
4. 写入一条 `executions`

## `executions` 最小写入规范

最小字段：

- `signal_id`
- `symbol`
- `side`
- `mode`
- `status`
- `detail_json`

约定：

- `mode = "dry_run"`
- `status` 直接使用规则决策结果：
  - `execute`
  - `ignored`
  - `rejected`

## 验收口径

本阶段验收口径为：

- 只要求 `signals` 与 `executions` 正确落库
- `positions` 暂不参与本阶段验收

## 验收标准

系统达标需要满足：

- 可以通过 `signal-service` CLI 写入一条新信号
- `executor-service` CLI 可以消费一条 `new` 信号
- 消费后：
  - `signals.status` 被正确更新
  - `executions` 新增一条记录
- `executions.status` 与规则决策一致

## 建议测试覆盖

建议覆盖三种路径：

1. `execute`
   - 当前无仓位，允许执行

2. `ignored`
   - 当前已有同向仓位的模拟场景

3. `rejected`
   - 当前有冲突状态或不允许执行的模拟场景

第一轮最小实现至少保证：

- `execute` 路径完整跑通
- `ignored/rejected` 保留规则分支与测试入口
