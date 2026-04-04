# AGENT

## 北极星目标

构建并运行稳定、可审计、可回滚的自动交易系统。

## 范围过滤

每项改动必须至少满足其一：
- 提升交易执行正确性
- 提升风控与安全性
- 提升策略验证质量
- 提升可观测性与恢复能力

## 红线

- 未达到阶段门槛不得进入 live
- 不允许将 secrets 提交到仓库
- 不允许绕过验证直接声明完成
- 不允许绕过 close-only / halt 安全机制

## 阶段门槛

- backtest -> dry-run -> testnet -> tiny live

## 必读规则

- `rules/objective-and-scope.md`
- `rules/architecture-boundaries.md`
- `rules/trading-safety.md`
- `rules/verification-and-evidence.md`
- `rules/promotion-gates.md`
- `rules/change-management.md`

## 必读技能

- `skills/add-new-strategy/`
- `skills/run-backtest-and-compare/`
- `skills/run-dryrun-validation/`
- `skills/promote-to-testnet/`
- `skills/promote-to-live/`
- `skills/incident-stop-and-recover/`
- `skills/add-risk-rule/`
