---
name: add-risk-rule
description: Use when introducing a new risk control rule and it must be validated without breaking the main execution path.
---

# add-risk-rule

## 何时使用

- 新增风控门禁
- 修改仓位限制
- 增加熔断条件

## 输入

- 风控规则目标
- 影响范围
- 验证方法

## 步骤

1. 明确规则目标。
2. 明确拦截条件。
3. 增加最小验证用例。
4. 验证不破坏主链路。
5. 记录规则目的和影响。

## 输出

- 新风控规则
- 验证结果
- 风险说明

## 验证方式

- 规则触发测试
- 主链路回归验证
- 行为记录

## 常见错误

- 只加限制，不做回归验证
- 风控语义不清晰
- 不说明为何需要这条规则
