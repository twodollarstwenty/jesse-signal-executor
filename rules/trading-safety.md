# trading-safety

## 必须

- 单实例单策略运行。
- 单时刻单有效仓位。
- 支持 `close-only` 模式。
- 支持 `halt` 模式。
- 所有 live/testnet API key 必须最小权限。
- 所有执行前必须校验当前仓位状态。

## 禁止

- 带提币权限的 API key。
- 未完成 dry-run/testnet 验证直接推进 live。
- 在仓位状态不一致时继续执行。
- 在不明确风险边界时自动加仓。

## 例外

- 无。
