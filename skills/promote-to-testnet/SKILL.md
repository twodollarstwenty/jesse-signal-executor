---
name: promote-to-testnet
description: Deprecated placeholder only. Do not use; the repository no longer treats testnet as a formal promotion stage.
---

# promote-to-testnet

## 状态

已弃用。当前仓库不再把 `testnet` 视为正式晋级阶段。

## 现在应做什么

- dry-run 验证请使用 `skills/run-dryrun-validation/`
- 准备进入 tiny live 请使用 `skills/promote-to-live/`

## 说明

- 正式路径为 `backtest -> dry-run -> tiny live`
- 不要把 testnet 结果当作当前仓库的必需 gate

## 常见错误

- 继续按过时 testnet 流程推进当前仓库变更
- 把 testnet 当作 tiny live 之前的必经步骤
