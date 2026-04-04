---
name: run-backtest-and-compare
description: Use when comparing strategy changes or parameter changes and a fair, reproducible backtest is required.
---

# run-backtest-and-compare

## 何时使用

- 新策略对比旧策略
- 参数改动前后对比
- 不同模式收益对比

## 输入

- 策略名
- 交易对
- 时间窗口
- 杠杆或模式
- 对照对象

## 步骤

1. 固定时间窗口和市场条件。
2. 固定资金、费率、模式和杠杆。
3. 分别运行基线和候选版本。
4. 记录交易数、胜率、收益、回撤。
5. 明确说明是否可比较。

## 输出

- 对照表
- 结论
- 风险说明

## 验证方式

- 回测命令
- 原始结果
- 比较说明

## 常见错误

- 时间窗口不一致
- 费率或杠杆不一致
- 把不可比结果直接下结论
