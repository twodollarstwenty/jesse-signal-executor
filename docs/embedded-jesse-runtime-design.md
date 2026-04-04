# 新项目内嵌 Jesse Runtime 设计文档

## 目标

让 `jesse-signal-executor` 不再依赖外部旧项目 `jesse-sandbox`，而是在新项目内部自带一个独立 Jesse workspace，使 Jesse 成为新项目自己的策略回测与信号来源。

## 核心原则

- 新项目必须完全独立
- 不依赖旧的 `jesse-sandbox`
- Jesse 只是新项目内部的运行时组件之一
- Jesse 只负责策略计算和信号发出，不负责执行

## 目录设计

建议新增如下目录：

- `runtime/jesse_workspace/`
- `strategies/jesse/`
- `apps/signal_service/jesse_bridge/`

含义如下：

- `runtime/jesse_workspace/`：Jesse 运行时环境
- `strategies/jesse/`：项目自己的 Jesse 策略源码
- `apps/signal_service/jesse_bridge/`：Jesse 到 signal writer 的桥接辅助代码

## 嵌入方式

### 1. Jesse 作为内部运行时

Jesse 不放在主项目根逻辑层，而是作为内部 runtime 子系统存在。

这样主项目主结构仍保持清晰：

- `apps/`
- `db/`
- `rules/`
- `skills/`
- `scripts/`

而 Jesse 被隔离在：

- `runtime/jesse_workspace/`

### 2. 策略源码与 Jesse runtime 分离

策略源码不直接长期散落在 Jesse runtime 目录中。

主项目保留：

- `strategies/jesse/`

再通过同步脚本或复制步骤，把策略放入：

- `runtime/jesse_workspace/strategies/`

这样可以保证策略源码仍然属于主项目，而 Jesse workspace 只是运行副本。

### 3. Jesse 的职责边界

Jesse 在新项目内只负责两件事：

- 回测
- 产出标准化信号

它不负责：

- 执行
- 风控总控
- 订单状态管理

这些职责仍归主项目的 executor 层。

## Jesse 到主项目的桥接

由于 Jesse 和 signal writer 都已在同一新项目里，因此不再存在“跨旧项目 import”问题。

Jesse 策略将直接调用新项目中的：

- `apps.signal_service.writer`

推荐在 Jesse 策略内以最薄方式接入：

- 在开仓动作点发 `open_long / open_short`
- 在平仓动作点发 `close_long / close_short`
- 使用 K 线时间作为 `signal_time`

## 第一阶段范围

第一阶段只做到以下程度：

- 新项目内有独立 Jesse workspace
- 能放入一个策略（先 `Ott2butKAMA`）
- Jesse 能把标准信号写入主项目数据库
- 主项目 executor 可以继续消费这些信号

## 第一阶段不做

- Jesse live
- 多策略并发
- 真实交易所接入
- 完整 Docker 化 Jesse runtime
- 历史全部策略迁移

## 第一阶段验收标准

以下全部满足才算达标：

- `runtime/jesse_workspace/` 建立完成
- `strategies/jesse/` 中存在 `Ott2butKAMA` 的项目版本
- Jesse 可以调用主项目的 signal writer
- Jesse 发出的真实信号能进入 `signal_events`
- executor 能消费该信号并写入 `execution_events`
- 整个链路不依赖旧的 `jesse-sandbox`
