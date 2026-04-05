# Dry-Run Account Summary Design

## Background

The current dry-run terminal output can show:

- current price
- current action
- local floating PnL view while in position

The system also now has the beginnings of persistent position state. However, the operator still cannot see an account-style summary that answers the most practical questions:

- how much capital the dry-run started with
- how much has been realized
- how much is currently unrealized
- what the current equity is

The user wants a simple dry-run account view using an initial capital baseline of `1000 USDT`.

## Goal

Add a first-version dry-run account summary that shows:

- initial capital
- realized PnL
- unrealized PnL
- current equity

## Scope

### In Scope

- A lightweight account-summary view for dry-run.
- Initial capital assumed to be `1000 USDT`.
- Realized PnL from completed position cycles.
- Unrealized PnL from current open position.

### Out of Scope

- Full exchange-grade margin accounting.
- Funding fees.
- Multi-position portfolio accounting.
- Liquidation modeling.

## Proposed Approach

Create one small dry-run account-summary path that combines:

1. initial configured capital
2. realized PnL from completed close cycles
3. unrealized PnL from the current persisted position and current market price

The first version should aim for operator clarity, not accounting perfection.

## Core Metrics

### Initial Capital

Use a configurable initial dry-run capital with a default of:

- `1000 USDT`

### Realized PnL

Realized PnL should represent closed-position profit and loss accumulated so far.

### Unrealized PnL

Unrealized PnL should represent the floating PnL of the current open position, if one exists.

### Current Equity

Current equity should be shown as:

```text
current_equity = initial_capital + realized_pnl + unrealized_pnl
```

## Data Source Strategy

The first version should prefer existing repository state over introducing a new ledger schema immediately.

That means:

- use persistent current position state for open-position context
- use available execution/signal history to infer realized cycles where practical

If exact realized accounting is not yet available from current tables, the first version may explicitly implement a best-effort dry-run accounting model and document its boundaries.

## Display Shape

The first version can be a summary script or terminal block showing:

```text
初始资金: 1000.00
已实现盈亏: +35.20
未实现盈亏: -4.80
当前权益: 1030.40
当前持仓: long
持仓数量: 1.0
开仓价: 2058.05
当前价: 2057.99
```

## Acceptance Criteria

This work is complete when:

1. the dry-run account summary can display initial capital
2. it can display realized PnL
3. it can display unrealized PnL
4. it can display current equity
5. it can display the current persisted open position when one exists

## Risks and Mitigations

### Risk: current tables do not support perfect realized accounting

Mitigation:

- make the first version explicit about what is estimated vs. exact
- keep the implementation small and auditable

### Risk: account summary gets confused with real exchange margin accounting

Mitigation:

- label it clearly as dry-run account summary
- do not claim exchange-accurate margin calculations in the first version

## Follow-Up

If this proves useful, the next step would be a dedicated dry-run account state model with persistent realized/unrealized equity fields.
