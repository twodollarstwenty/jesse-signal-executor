# Realistic Dry-Run Position Sizing Design

## Background

The current dry-run observability layer is now much richer, but position size still appears as a placeholder-like `1.0` in many places. That makes the display misleading when the operator expects the shown quantity to be consistent with:

- initial capital
- leverage
- current price
- chosen risk model

The user explicitly pointed out the mismatch: if the dry-run account starts from `1000 USDT`, the displayed quantity should not feel arbitrary.

## Goal

Introduce a realistic position sizing model for dry-run so that displayed quantity and margin are consistent with capital, leverage, and the chosen sizing rule.

## Scope

### In Scope

- Realistic dry-run quantity calculation.
- Margin estimate derived from notional and leverage.
- Position panel values that are consistent with the chosen sizing model.

### Out of Scope

- Full exchange-grade liquidation engine.
- Portfolio-level capital allocation across many simultaneous symbols.
- Real exchange balance synchronization.

## Proposed Sizing Model

The dry-run system should stop using placeholder quantity values and instead derive quantity from a simple capital-aware formula.

## Recommended First Version

Use this formula:

```text
max_notional = initial_capital * leverage
qty = position_fraction * max_notional / current_price
```

Where:

- `initial_capital` default: `1000 USDT`
- `leverage` default: current configured leverage (now `10x`)
- `position_fraction` first-version default: `0.2` (20% of max notional)

This creates a dry-run quantity that is:

- easy to explain
- capital-aware
- leverage-aware
- stable enough for operator understanding

## Why This First-Version Model

The repository already has a deeper risk-managed strategy family, but the dry-run display layer does not yet behave like a clean portfolio engine.

So the first version should prioritize:

- consistency
- explainability
- operator trust

before attempting a more sophisticated exchange-grade margin model.

## Example

If:

- initial capital = `1000 USDT`
- leverage = `10x`
- position fraction = `20%`
- current price = `2100 USDT`

Then:

```text
max_notional = 1000 * 10 = 10000 USDT
effective_notional = 10000 * 0.2 = 2000 USDT
qty = 2000 / 2100 = 0.95238 ETH
```

That is much closer to operator intuition than a hardcoded `1.0` placeholder.

## Display Impact

Once quantity is derived this way, the current-position panel becomes much more believable:

- size in base asset becomes meaningful
- notional USDT becomes meaningful
- estimated margin becomes meaningful

## Acceptance Criteria

This work is complete when:

1. dry-run quantity is no longer a placeholder value
2. displayed size is consistent with initial capital, leverage, and current price
3. position panel notional and margin are derived from the same sizing model
4. the resulting values are explainable by a simple formula

## Risks and Mitigations

### Risk: this is still not exchange-grade margin math

Mitigation:

- document it clearly as a first-version dry-run sizing model
- prefer a transparent approximation over misleading fake precision

### Risk: position fraction is too arbitrary

Mitigation:

- choose a default that is small and explainable
- make it configurable later if needed

## Follow-Up

If this improves operator trust, the next step can be unifying this sizing model with the strategy's fixed-risk candidate logic or introducing symbol-level position fractions.
