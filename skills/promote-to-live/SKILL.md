---
name: promote-to-live
description: Use when a dry-run validated system is being reviewed for tiny live promotion under strict safety gates.
---

# promote-to-live

## 何时使用

- dry-run 已完成验证
- 想进入 tiny live
- 已有停机和回滚预案

## 输入

- dry-run 验证摘要
- tiny live 风险预算
- API 权限配置
- 停机方案

## 步骤

1. 检查是否满足 `rules/promotion-gates.md`。
2. 确认 dry-run 摘要与相关日志/状态证据完整。
3. 确认 API 权限最小化。
4. 确认 close-only / halt 可用。
5. 设定 tiny live 风险预算。
6. 启动并监控。

## 输出

- tiny live 上线决定
- 风险说明
- 监控要求

## 验证方式

- 上线前检查清单
- 启动命令
- 风险预算记录
- dry-run 摘要与对应验证证据

## 常见错误

- dry-run 还没完成验证就想进入 tiny live
- 无回滚预案
- 资金过大
