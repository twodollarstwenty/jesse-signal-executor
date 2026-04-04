---
name: add-new-strategy
description: Use when introducing a new strategy into the project and it must be integrated, validated, and documented consistently.
---

# add-new-strategy

## 何时使用

- 新增策略文件
- 接入外部策略
- 替换当前主策略

## 输入

- 策略来源
- 目标市场
- 运行模式
- 预期验证窗口

## 步骤

1. 引入策略代码。
2. 补最小运行配置。
3. 跑基线回测。
4. 记录结果。
5. 如达标，再进入 dry-run 验证。

## 输出

- 可运行策略
- 回测记录
- 是否进入下一阶段的结论

## 验证方式

- 回测命令
- 指标结果
- 配置文件路径

## 常见错误

- 只接入不验证
- 不记录基线
- 不说明来源和适用条件
