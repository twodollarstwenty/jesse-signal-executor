# Current Position Panel Design

## Goal

Define a clear current-position panel for dry-run and future tiny-live views using these fields:

- 符号
- 大小
- 保证金
- 保证金比率
- 开仓价格
- 标记价格
- 强平价格
- 收益额（收益率）
- 止盈/止损

## Scope

### In Scope

- Field definitions
- First-version calculation rules
- Which fields are exact vs estimated vs unavailable

### Out of Scope

- Frontend implementation
- Exact exchange-grade liquidation engine
- Full portfolio margin engine

## Field Definitions

### 符号

Display as contract-style symbol, for example:

- `ETHUSDT 永续`

### 大小

The panel should not show an ambiguous single number. It should make the unit explicit.

Recommended split:

- `大小(ETH)` or base-asset quantity
- `名义金额(USDT)`

Where:

```text
名义金额(USDT) = qty * 标记价格
```

### 保证金

For the first version, this should be an estimated value:

```text
保证金 ≈ 名义金额 / 杠杆
```

This is acceptable for dry-run display even though it is not exchange-grade margin accounting.

### 保证金比率

For the first version, use an estimated operator-friendly value:

```text
保证金比率 ≈ 保证金 / 当前权益
```

This should be labeled as a first-version estimate if needed.

### 开仓价格

Use the current persisted `entry_price` from position state.

### 标记价格

Use the current market-derived price (Binance Futures REST in the current dry-run implementation).

### 强平价格

Do not fake this field.

For the first version:

- show `--`
- or `未计算`

until a real liquidation model exists.

### 收益额（收益率）

Use the current floating values:

- `未实现盈亏`
- `未实现收益率`

Rendered together, for example:

```text
+17.50 USDT (+0.85%)
```

### 止盈/止损

The first version can display the strategy's active TP / SL prices when available.

Suggested display:

- `止盈: 2120.50`
- `止损: 2041.20`

If unavailable, show `--`.

## First-Version Example

| 符号 | 大小(ETH) | 名义金额(USDT) | 保证金 | 保证金比率 | 开仓价格 | 标记价格 | 强平价格 | 收益额（收益率） | 止盈/止损 |
|---|---:|---:|---:|---:|---:|---:|---|---|---|
| ETHUSDT 永续 | 1.0 | 2075.55 | 207.56 | 20.76% | 2058.05 | 2075.55 | -- | +17.50 (+0.85%) | TP 2120 / SL 2041 |

## Display Guidance

- 盈亏正数使用绿色
- 盈亏负数使用红色
- 多空方向明显区分
- `大小` 字段必须带单位，避免把标的数量和 USDT 名义金额混淆

## Acceptance Criteria

1. the current-position panel fields are clearly defined
2. first-version estimated fields are explicitly identified
3. the panel avoids ambiguous quantity presentation
4. `强平价格` is not fabricated in the first version

## Follow-Up

Later steps can replace the estimated margin fields with exchange-accurate calculations and add a real liquidation model.
