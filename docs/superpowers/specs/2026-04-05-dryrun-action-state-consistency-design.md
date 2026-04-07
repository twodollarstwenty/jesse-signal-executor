# Dry-Run Action and Position-State Consistency Design

## Background

The current dry-run has become much more realistic than earlier versions, but one important inconsistency remains: the strategy-side decision can produce an action that conflicts with the currently displayed position state.

For example, the operator can observe:

- current position: `short`
- emitted action: `open_long`

This is logically inconsistent. A short position should first be closed before any long position is opened.

The user correctly pointed out that the problem is not only the action label itself. Once a `close_short` or `close_long` is executed, the displayed position state must also progress correctly.

## Goal

Make dry-run action generation and position-state display consistent with one another.

## Core Principle

The dry-run should distinguish between:

1. **strategy intent** — what direction the current candle-driven logic prefers
2. **legal executable action** — what action is allowed given the current position state
3. **position progression** — how the displayed state changes after execution

## Proposed Model

### Step 1: Strategy Intent

The candle-driven logic should produce a directional intent such as:

- `long`
- `short`
- `flat`

This is not yet an executable action.

### Step 2: Normalize Intent Into Legal Action

Given the current persisted position state:

#### Current position = `flat`

- `long` intent -> `open_long`
- `short` intent -> `open_short`
- `flat` intent -> `none`

#### Current position = `long`

- `long` intent -> `none`
- `short` intent -> `close_long`
- `flat` intent -> `close_long`

#### Current position = `short`

- `short` intent -> `none`
- `long` intent -> `close_short`
- `flat` intent -> `close_short`

This guarantees that the system never jumps directly from `short` to `open_long` or from `long` to `open_short` in one step.

## Position-State Progression

The displayed position state should follow the persisted `position_state` table as the authoritative state.

That means:

- after `close_short` executes, the next displayed state should become `flat`
- after `close_long` executes, the next displayed state should become `flat`
- only after a flat state exists should a new opposite-direction open action become legal

## Why This Matters

Without this normalization layer, dry-run output may still be useful for raw activity observation, but it is hard to trust as a trading simulation. The operator should not have to mentally reconcile contradictory lines such as:

- current position = short
- action = open_long

## Acceptance Criteria

This work is complete when:

1. dry-run first computes directional intent, then normalizes it into a legal action
2. the system never emits `open_long` while a short position is still open
3. the system never emits `open_short` while a long position is still open
4. displayed position state progresses consistently after executed close actions

## Follow-Up

After this consistency layer is in place, the next stage can further tighten how closely the candle-driven intent matches the real strategy logic.
