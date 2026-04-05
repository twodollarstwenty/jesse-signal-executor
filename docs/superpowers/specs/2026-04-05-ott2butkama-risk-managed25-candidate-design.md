# Ott2butKAMA RiskManaged25 Candidate Design

## Background

The repository already has a general fixed-risk strategy variant, `Ott2butKAMA_RiskManaged`, with default per-trade risk of `1.0%`. Recent backtests showed that higher fixed-risk settings preserve the original signal quality while improving returns relative to the `1.0%` version.

Among the tested values, `2.5%` emerged as a strong candidate because it:

- outperformed the original strategy on net profit in the tested window
- kept drawdown below the original strategy
- avoided the margin failures seen at much higher risk levels

The user wants to formalize this `2.5%` setting as a distinct candidate, rather than merely keeping it as a temporary runtime experiment.

## Goal

Create a formal `Ott2butKAMA_RiskManaged25` strategy candidate and export its trade details alongside the original strategy for direct inspection.

## Scope

### In Scope

- Add a dedicated runtime-compatible `Ott2butKAMA_RiskManaged25` strategy directory.
- Keep the same fixed-risk sizing logic as `Ott2butKAMA_RiskManaged`.
- Set the default risk level to `2.5%`.
- Export trade details for `Ott2butKAMA` and `Ott2butKAMA_RiskManaged25`.

### Out of Scope

- Further risk sweeps.
- Replacing the existing `Ott2butKAMA_RiskManaged` variant.
- Changing signal logic.

## Proposed Approach

Add one new strategy directory:

- `strategies/jesse/Ott2butKAMA_RiskManaged25`

It should be a full Jesse-runtime-compatible strategy copy, just like the current risk-managed variant, but with:

- `risk_per_trade = 25`

Interpretation:

- `25 / 1000 = 0.025 = 2.5%`

This preserves explicit naming and avoids overloading the meaning of `Ott2butKAMA_RiskManaged`.

## Why A Dedicated Strategy Name

Using a dedicated strategy directory is preferred over mutating the existing `Ott2butKAMA_RiskManaged` default because:

- it preserves the already-established `1.0%` candidate as a separate reference point
- it makes compare runs easier to understand
- it avoids silently changing the semantics of an existing committed strategy

## Validation

The candidate should be validated with two outputs:

1. a direct compare run against the original `Ott2butKAMA`
2. exported trade-detail tables for both:
   - `Ott2butKAMA`
   - `Ott2butKAMA_RiskManaged25`

The main purpose of the trade-detail export is not just performance comparison, but visual inspection of:

- whether the candidate still follows the same broad trade timing
- how the per-trade sizing differs from the original
- whether the candidate remains operationally understandable

## Acceptance Criteria

This work is complete when:

1. a new `Ott2butKAMA_RiskManaged25` strategy exists
2. its sizing logic matches the fixed-risk model already established in `Ott2butKAMA_RiskManaged`
3. its default risk is `2.5%`
4. the original strategy and the `RiskManaged25` candidate can both export trade details

## Risks and Mitigations

### Risk: strategy duplication grows too much

Mitigation:

- accept the duplication for now because explicit named candidates are useful during evaluation

### Risk: candidate naming becomes noisy

Mitigation:

- keep names explicit and aligned with the fixed-risk percentage

## Follow-Up

If `RiskManaged25` is accepted, a future cleanup could simplify the candidate set and archive weaker variants.
