# promotion-gates

## 必须

系统晋级顺序固定为：
- backtest
- dry-run
- tiny live

每一阶段都必须完成前一阶段验证后才能晋级。

## 最小门槛

### backtest -> dry-run
- 回测可重复
- 策略逻辑可解释
- 关键风险已知

### dry-run -> tiny live
- 连续运行窗口达标
- 无重复消费
- 无明显状态漂移
- 日志与验证摘要完整
- close-only / halt 已验证

## 禁止

- 跨级晋级。
- 用人工解释替代 gate。
