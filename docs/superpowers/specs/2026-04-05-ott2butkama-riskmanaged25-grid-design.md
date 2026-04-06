# Ott2butKAMA RiskManaged25 Grid Design

## Background

The repository already has `Ott2butKAMA_RiskManaged25`, which preserves the original strategy direction logic while using a fixed-risk position sizing model. The next requested step is not to replace that strategy with a traditional two-sided price grid, but to evolve it into a **staged-entry grid-style variant**.

The intent is to preserve the existing directional edge while turning one-shot entries into multiple planned entry layers.

## Goal

Create a staged-entry grid variant based on `Ott2butKAMA_RiskManaged25` that:

- keeps the same directional judgment
- keeps total risk budget anchored to the current `2.5%` model
- enters positions in multiple tranches rather than one shot

## Scope

### In Scope

- Multi-stage entries.
- Total fixed risk budget preserved.
- Long and short staged-entry behavior.
- Reuse the current direction logic from `Ott2butKAMA_RiskManaged25`.

### Out of Scope

- Traditional neutral grid trading.
- Multi-direction simultaneous grids.
- A new independent strategy model.
- Complex partial take-profit ladders in the first version.

## Proposed Approach

Introduce a new candidate strategy based on `Ott2butKAMA_RiskManaged25`, for example:

- `Ott2butKAMA_RiskManaged25_Grid`

This candidate should preserve the same directional filters and exits, but replace the current single-entry position sizing with planned staged entries.

## Position Entry Model

### Total Risk Budget

Keep the current total risk budget equivalent to the existing `2.5%` fixed-risk candidate.

### Entry Layers

The first version should use a small number of layers, such as:

- Layer 1: `40%`
- Layer 2: `30%`
- Layer 3: `30%`

These percentages refer to the total intended position/risk budget, not to independent unlimited adds.

## Entry Triggers

### Long Direction

When the strategy decides long bias is valid:

- first layer enters immediately
- second layer enters only if price retraces by a configured distance below the first layer reference
- third layer enters only if price retraces further

### Short Direction

Symmetric behavior for shorts:

- first layer enters immediately
- second and third layers add only if price moves against the short entry by configured upward distances

## Suggested First-Version Layer Distances

The first version should keep distances small and explicit, for example:

- layer 2 trigger: `0.4%`
- layer 3 trigger: `0.8%`

These are only for first-version design guidance and can be tuned later.

## Position State Requirements

The staged-entry variant needs more than a single `qty` and `entry_price`. It should at least track enough local or persistent state to know:

- which entry layers have already been filled
- current blended position quantity
- blended average entry price

This does not yet require a full portfolio engine, but it does require the strategy not to lose track of which layers have already been used.

## Exit Model

The first version should keep exits simple and close to the existing strategy behavior:

- keep the current direction-based close logic
- keep stop-loss / take-profit model simple

Do not add full laddered exits in the first version.

## Why This Is Not A Traditional Grid

This design is not a neutral market-making grid. It is:

- trend-directional
- signal-driven
- staged in its entries

So the correct mental model is:

- **directional strategy with staged entry grid**, not a standalone classical grid bot

## Acceptance Criteria

This work is complete when:

1. a new staged-entry grid candidate exists
2. it preserves the directional logic of `Ott2butKAMA_RiskManaged25`
3. it can enter in multiple planned layers
4. total risk remains bounded by the intended fixed-risk budget
5. it can be backtested against the original `RiskManaged25`

## Risks and Mitigations

### Risk: staged entry complexity makes state handling fragile

Mitigation:

- keep the first version to only 2-3 layers
- keep exits simple

### Risk: layered adds amplify drawdown too much

Mitigation:

- tie layer sizes to the same total risk budget rather than treating each add as full risk

### Risk: this becomes a disguised new strategy

Mitigation:

- preserve the original direction logic and only change position construction

## Follow-Up

If the staged-entry version works, the next step can be tuning layer distances or adding staged exits. If it becomes too stateful and brittle, the strategy may need a more formal position-management layer.
