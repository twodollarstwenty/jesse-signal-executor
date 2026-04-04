# Backtest Compare Framework 设计

## 背景

当前项目已完成信号与执行链路的基础验证，但尚未建立可复现、可比较的回测框架。按照项目阶段门槛，进入 dry-run 之前必须先具备可审计的回测证据。

目前缺口包括：

- Jesse workspace 的可运行回测配置仍不完整（`config.py` / `routes.py` 仍是占位）
- 没有统一的 baseline vs candidate 对照执行入口
- 没有标准化回测结果落盘与对照报告

## 目标

建立一个可重复执行的回测对照框架，在相同市场条件下对 baseline 与 candidate 进行公平比较，并产出结构化报告。

本轮基线市场固定：`ETHUSDT 5m`。

## 范围

### In Scope

- 补齐 Jesse runtime 最小回测配置。
- 新增统一对照回测执行入口（baseline/candidate 双跑）。
- 固化原始输出日志与对照报告输出格式。
- 增加最小自动化验证（脚本参数、结果文件、可比性检查）。

### Out of Scope

- 不做 Web 可视化报表。
- 不做数据库化结果存储。
- 不做多交易所或多市场并发调度。

## 方案选择

候选方案：

1. 最小单次回测脚本（仅跑一次）
2. baseline vs candidate 对照框架（采用）
3. 直接做全量实验平台

采用方案 2，原因：

- 满足“可比较、可复现、可审计”要求
- 范围仍可控，不引入平台级复杂度
- 与项目阶段门槛直接对齐（backtest -> dry-run）

## 架构设计

框架分三层：

1. **配置层**：`runtime/jesse_workspace/config.py` + `runtime/jesse_workspace/routes.py`
2. **执行层**：`scripts/run_backtest_compare.py`（统一入口）
3. **证据层**：`docs/backtests/raw/*.log` + `docs/backtests/*-compare.md`

### 1) 配置层

- 提供可运行的最小 Jesse 回测配置。
- 固定并显式声明核心参数（资金、费率、杠杆、交易模式等）。
- 路由指向 baseline/candidate 回测所需策略入口。

### 2) 执行层

统一脚本负责：

- 解析参数：
  - `--symbol`（默认 `ETHUSDT`）
  - `--timeframe`（默认 `5m`）
  - `--start` / `--end`
  - `--baseline-strategy` / `--candidate-strategy`
  - `--baseline-tag` / `--candidate-tag`（可选）
- 检查可比性前置条件：
  - 时间窗口一致
  - 资金、费率、杠杆、模式一致
- 顺序执行两次回测并收集输出。

### 3) 证据层

- 原始日志落盘：
  - `docs/backtests/raw/<timestamp>-baseline.log`
  - `docs/backtests/raw/<timestamp>-candidate.log`
- 对照报告落盘：
  - `docs/backtests/<timestamp>-compare.md`

报告至少包含：

- 回测命令（可复现）
- 参数一致性说明
- 指标对照表（交易数、胜率、收益、最大回撤）
- 结论与风险说明

## 失败处理策略

- 任一回测命令失败：立即返回非零退出码。
- 仍生成失败摘要报告（标明失败阶段、错误摘要、日志路径）。
- 输出中明确“不可比较”状态，禁止给出优劣结论。

## 测试与验证

## 自动化测试

- 验证参数解析与必填约束。
- 验证可比性检查逻辑（不一致参数触发失败）。
- 验证日志与报告文件生成路径。

## 手动验收

使用统一窗口执行一次完整对照：

- 市场：`ETHUSDT`
- 周期：`5m`
- 时间窗口：固定一个具体区间

验收通过条件：

- 产出 baseline 与 candidate 两份原始日志
- 产出一份对照报告
- 报告中的核心指标齐全且可追溯

## 风险与后续

### 风险

- Jesse CLI 版本差异导致命令输出格式变化，可能影响解析稳定性。
- 本轮使用文本日志解析，存在格式耦合风险。

### 后续迭代

1. 增加结构化结果输出（JSON）优先解析。
2. 扩展多窗口批量对照能力。
3. 接入 dry-run 阶段对照追踪（回测基线 -> 线上偏差）。
