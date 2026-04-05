# Richer Dry-Run Log Line Design

## Goal

Enhance the existing one-line `jesse-dryrun` terminal/log output so the operator can directly observe account-style values in real time.

## Scope

### In Scope

- Add initial capital
- Add realized PnL
- Add unrealized PnL
- Add current equity
- Add notional position size in USDT
- Keep the output as one line

### Out of Scope

- New logging system
- New database tables
- Notification changes

## Proposed Output Shape

### Flat Example

```text
[2026-04-06T05:36:41+08:00] 策略=Ott2butKAMA 交易对=ETHUSDT 当前价=2057.99 初始资金=1000.00 已实现盈亏=+35.20 未实现盈亏=+0.00 当前权益=1035.20 持仓=空仓 判断=flat 动作=none 已发送=否
```

### In-Position Example

```text
[2026-04-06T05:36:41+08:00] 策略=Ott2butKAMA 交易对=ETHUSDT 持仓方向=多 持仓数量(ETH)=1.0 持仓名义金额(USDT)=2057.99 开仓价=2058.05 当前价=2057.99 已实现盈亏=+35.20 未实现盈亏=-0.06 当前权益=1035.14 动作=close_short 已发送=是
```

## Field Rules

- `初始资金`: default `1000.00`
- `已实现盈亏`: from the dry-run account-summary logic
- `未实现盈亏`: current floating PnL
- `当前权益`: initial capital + realized + unrealized
- `持仓数量(ETH)`: persistent position quantity in base asset units
- `持仓名义金额(USDT)`: `qty * current_price`

## Acceptance Criteria

1. Flat-state log lines include account summary values.
2. In-position log lines include account summary and notional USDT size.
3. Output remains one line per loop.
