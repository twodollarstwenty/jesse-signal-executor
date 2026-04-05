---
name: run-dryrun-validation
description: Use when validating a strategy or execution change in dry-run mode before any tiny live promotion decision.
---

# run-dryrun-validation

## 何时使用

- 新策略刚接入
- 执行逻辑刚修改
- 风控规则刚调整
- 准备评估是否进入 tiny live

## 输入

- 策略名
- 配置文件路径
- 观察窗口
- 验证目标

## 步骤

1. 启动 dry-run。
2. 检查服务状态是否正常。
3. 记录信号、执行、异常、仓位状态。
4. 运行 `python3 scripts/summarize_dryrun_validation.py --minutes 60` 汇总最近窗口内的 dry-run 证据。
5. 对照 `rules/promotion-gates.md` 判断是否达标。

## 输出

- 一份 dry-run 验证摘要
- 明确的 PASS / FAIL 结论

## 验证方式

必须给出：
- 启动命令
- 状态命令
- `scripts/summarize_dryrun_validation.py` 的摘要输出
- 关键日志或数据库结果
- 最终判断依据

## 常见错误

- 只看服务启动，不看仓位状态
- 只看收益，不看重复消费
- 没有附 dry-run 摘要脚本输出
- 没有给出可复查证据
