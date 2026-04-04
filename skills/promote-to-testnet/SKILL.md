---
name: promote-to-testnet
description: Use when a dry-run validated strategy or execution path is being considered for testnet promotion.
---

# promote-to-testnet

## 何时使用

- dry-run 已稳定
- 想验证真实下单链路
- 想验证订单状态同步

## 输入

- dry-run 验证记录
- testnet 配置
- 风险边界

## 步骤

1. 确认 dry-run 达标。
2. 确认 testnet API 配置正确。
3. 启动 testnet。
4. 检查订单生命周期。
5. 检查仓位一致性。

## 输出

- testnet 验证摘要
- 是否可进入 tiny live

## 验证方式

- 启动命令
- 订单与仓位状态
- 错误日志

## 常见错误

- dry-run 未达标就上 testnet
- 用主网 key 冒充 testnet
- 只看下单成功，不看状态同步
