---
name: promote-to-live
description: Use when a testnet validated system is being reviewed for tiny-live promotion under strict safety gates.
---

# promote-to-live

## 何时使用

- testnet 已稳定
- 想进入 tiny live
- 已有停机和回滚预案

## 输入

- testnet 验证摘要
- tiny live 风险预算
- API 权限配置
- 停机方案

## 步骤

1. 检查是否满足 `rules/promotion-gates.md`。
2. 确认 API 权限最小化。
3. 确认 close-only / halt 可用。
4. 设定 tiny live 风险预算。
5. 启动并监控。

## 输出

- tiny live 上线决定
- 风险说明
- 监控要求

## 验证方式

- 上线前检查清单
- 启动命令
- 风险预算记录

## 常见错误

- testnet 还没稳定就想 live
- 无回滚预案
- 资金过大
