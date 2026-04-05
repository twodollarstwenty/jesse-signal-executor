# Ott2butKAMA Risk-Managed Variant Design

## Background

The current `Ott2butKAMA` strategy sizes positions using a simple half-balance model multiplied by leverage. That means position size is driven mainly by account size and leverage, not by the actual stop-loss distance of the trade.

As a result, two trades with very different stop distances can still take similarly large position sizes, which is not true fixed-risk behavior.

The user wants to improve the position sizing model rather than just changing leverage mode. The target is a fixed-risk model where a stopped-out trade risks roughly `1%` of account equity.

## Goal

Create a risk-managed `Ott2butKAMA` variant that preserves the existing signal logic but replaces the current half-balance sizing model with a stop-distance-based fixed-risk model.

## Scope

### In Scope

- Keep the same entry and exit signal logic.
- Keep the same indicator structure.
- Add a strategy variant with a fixed-risk position sizing model.
- Set the default per-trade risk to `1%` of equity.

### Out of Scope

- Rewriting the strategy logic.
- Changing executor or bridge behavior.
- Building a complete portfolio risk engine.

## Current Position Sizing

The current strategy uses:

```python
utils.size_to_qty((self.balance / 2), self.price, fee_rate=self.fee_rate) * self.leverage
```

This means:

- position size is based on half the account balance
- leverage amplifies the resulting quantity
- stop-loss distance does not directly cap the loss per trade

## Proposed Approach

Create a new variant, recommended name:

- `Ott2butKAMA_RiskManaged`

The variant should keep the same strategy logic and hyperparameters, but change the sizing model so that quantity is derived from:

1. current account balance
2. configured risk percentage per trade
3. estimated stop distance from entry to stop-loss

## Risk Model

### New Hyperparameter

Add a new hyperparameter:

- `risk_per_trade`

Default value:

- `10`

Interpretation:

- `10 / 1000 = 0.01 = 1%`

This keeps the parameter style consistent with the existing integer-based hyperparameter scheme used for stop-loss and risk-reward.

## Sizing Logic

### Risk Amount

Per-trade risk amount:

```text
risk_amount = balance * risk_fraction
```

With default `1%`, that means:

```text
risk_amount = balance * 0.01
```

### Stop Distance

The strategy already computes stop distance from OTT and price.

For longs:

```text
stop_price = ott - ott * stop
stop_distance = price - stop_price
```

For shorts:

```text
stop_price = ott + ott * stop
stop_distance = stop_price - price
```

### Quantity

The position size should be derived from:

```text
qty = risk_amount / stop_distance
```

Then adjusted into the format Jesse expects.

## Safety Rules

The risk-managed variant must defensively handle edge cases:

- if stop distance is zero or negative, do not produce an oversized position
- if stop distance is extremely small, the strategy should avoid nonsensical quantity growth

The implementation may clamp or fail safe, but it must not silently create unrealistic huge sizes.

## Strategy Structure

The variant should be a separate strategy directory, not a mutation of the original file.

Preferred structure:

- copy the current `Ott2butKAMA` strategy
- add the new `risk_per_trade` hyperparameter
- replace the current `pos_size` logic with fixed-risk sizing logic

This keeps the original strategy intact and makes A/B comparison straightforward.

## Validation

Validate the risk-managed variant against the original `Ott2butKAMA` using the same:

- symbol
- timeframe
- window
- leverage
- fee
- initial balance

The comparison should check at least:

- total trades
- win rate
- net profit
- max drawdown

And the evaluation should inspect whether risk exposure behaves more consistently per trade than the current half-balance model.

## Acceptance Criteria

This work is complete when:

1. a new `Ott2butKAMA_RiskManaged` variant exists
2. the original `Ott2butKAMA` remains unchanged
3. the new variant sizes positions using stop-distance-based fixed risk
4. default risk is approximately `1%` of account equity per trade
5. the variant can be backtested and compared directly to the original

## Risks and Mitigations

### Risk: risk model interacts unexpectedly with leverage

Mitigation:

- validate with the same leverage as the original strategy first
- compare not just return, but drawdown and practical trade sizing

### Risk: stop distance may be too small in some regimes

Mitigation:

- add safe guards against zero/near-zero stop distances

### Risk: strategy profitability drops even if risk control improves

Mitigation:

- treat this variant as a controlled risk experiment, not an assumption of better returns

## Follow-Up

If the risk-managed variant improves drawdown discipline but harms returns too much, the next step should be tuning `risk_per_trade` or combining risk-managed sizing with one of the moderate short-hold parameter profiles.
