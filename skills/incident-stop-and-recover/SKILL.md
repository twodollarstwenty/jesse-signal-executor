---
name: incident-stop-and-recover
description: Use when there is an execution anomaly, position mismatch, repeated signals, or any condition requiring emergency stop or controlled recovery.
---

# incident-stop-and-recover

## 何时使用

- 仓位不一致
- 重复执行
- 执行异常堆积
- 需要紧急停机

## 输入

- 当前服务状态
- 当前仓位状态
- 最近异常日志

## 步骤

1. 切换 `halt` 或 `close-only`。
2. 冻结新信号消费。
3. 检查数据库与外部状态差异。
4. 记录事故。
5. 明确恢复步骤后再恢复运行。

## 输出

- 停机状态
- 事故记录
- 恢复方案

## 验证方式

- 停机命令输出
- 状态查询结果
- 恢复前后对照

## 常见错误

- 先修再记录
- 未停机就继续处理
- 不核对外部状态
