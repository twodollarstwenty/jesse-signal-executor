# promotion-gates

## 必须

系统晋级顺序固定为：
- backtest
- dry-run
- testnet
- tiny live

每一阶段都必须完成前一阶段验证后才能晋级。

## 最小门槛

### backtest -> dry-run
- 回测可重复
- 策略逻辑可解释
- 关键风险已知

### dry-run -> testnet
- 连续运行窗口达标
- 无重复消费
- 无仓位漂移
- 日志完整

### testnet -> tiny live
- 真实下单链路稳定
- 无状态错乱
- 有停机和回滚预案
- close-only / halt 已验证

## 禁止

- 跨级晋级。
- 用人工解释替代 gate。
