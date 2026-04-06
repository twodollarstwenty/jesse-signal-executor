# Trade History Panel Design

## Goal

Define a trade-history panel/data view that matches the requested fields:

- 时间
- 合约
- 方向
- 价格
- 数量
- 手续费
- 角色
- 已实现盈亏

## Scope

### In Scope

- Field definitions
- First-version data-source mapping
- Which fields are real vs estimated vs currently unavailable

### Out of Scope

- Frontend implementation
- Exchange-grade fill reconciliation
- Full order book / maker-taker engine

## Intended Shape

The panel should read like a成交历史表, close to exchange UI language.

## Field Definitions

### 时间

成交时间，推荐使用北京时间展示。

### 合约

例如：

- `ETHUSDT 永续`

### 方向

建议使用：

- `开多`
- `开空`
- `平多`
- `平空`

### 价格

成交价或执行价。

### 数量

建议明确带单位，例如：

- `0.362 ETH`

### 手续费

第一版如果没有真实手续费模型，可明确区分：

- `--`
- 或 `估算值`

不要伪装成真实交易所精确手续费。

### 角色

第一版如果没有真实撮合数据，不要伪装成真实 `吃单方 / 挂单方`。

建议第一版显示：

- `dry-run`

或 `--`

### 已实现盈亏

平仓记录显示已实现盈亏。

开仓记录第一版可以显示：

- `0.00000000 USDT`

## First-Version Mapping

### Dry-Run

The first version can be built from:

- `signal_events`
- `execution_events`
- current/persistent position state if needed for pairing

This means the first version is an internal trade-history view, not an exchange-grade fill ledger.

### Tiny Live

If later integrated, the same panel shape can be filled with real exchange execution data.

## First-Version Example

| 时间 | 合约 | 方向 | 价格 | 数量 | 手续费 | 角色 | 已实现盈亏 |
|---|---|---|---:|---|---:|---|---:|
| 2026-04-06 09:23:25 | ETHUSDT 永续 | 平空 | 2114.84 | 0.362 ETH | -- | dry-run | +4.96060999 USDT |

## Acceptance Criteria

1. the trade-history panel fields are clearly defined
2. the first-version sources are explicit
3. unavailable exchange-only fields are not faked as exact values
4. the panel shape is compatible with both dry-run and future tiny-live usage

## Follow-Up

Later steps can upgrade the panel with real fee and role fields once exchange execution data is integrated.
