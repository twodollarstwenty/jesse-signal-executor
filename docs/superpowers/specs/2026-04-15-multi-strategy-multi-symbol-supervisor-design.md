# Multi-Strategy Multi-Symbol Supervisor Design

## Background

The current dry-run runtime is intentionally narrow. It assumes one active strategy, one active symbol, and one shared runtime state path.

Today that assumption appears in multiple layers:

- `scripts/run_jesse_live_loop.py` hard-codes one strategy, one symbol, and one timeframe.
- `scripts/run_jesse_dryrun_loop.py` only syncs and runs `Ott2butKAMA`.
- runtime state files such as `last_action` and `last_candle_ts` are stored as single global files.
- executor position tracking is effectively keyed by `symbol`, which is not sufficient if two strategies trade the same market independently.

The desired operating model is broader:

1. run multiple strategies at the same time
2. run multiple symbols per strategy
3. assign a distinct capital allocation and sizing rule to each strategy-symbol combination
4. manage the full set of active combinations through one supervisor entrypoint

This requires the runtime to move from a single-instance model to a configuration-driven multi-instance model.

## Goal

Design a dry-run architecture where one supervisor manages multiple independent trading instances, and each instance represents exactly one:

- strategy
- symbol
- timeframe
- capital allocation
- sizing rule

The resulting system must preserve clear isolation between instances while keeping operator workflows simple through unified `start`, `status`, `stop`, and summary commands.

## Scope

### In Scope

- Introduce a configuration-driven multi-instance runtime model.
- Support running multiple strategies concurrently.
- Support running multiple symbols per strategy.
- Support distinct capital allocation and sizing configuration per strategy-symbol instance.
- Isolate signal persistence, execution state, logs, heartbeats, and local runtime state per instance.
- Add a supervisor layer that manages all enabled instances together.
- Update validation and status reporting so operators can determine whether each instance is active, stale, or idle.

### Out of Scope

- Dynamic capital rebalancing between running instances.
- Portfolio-level risk aggregation across all instances.
- Live trading promotion changes.
- UI dashboards.
- Advanced capital accounting such as realized cross-instance transfers or shared margin optimization.

## Design Summary

The runtime should adopt a two-layer structure:

1. a single supervisor process that reads instance configuration and manages lifecycle
2. one worker process per enabled trading instance

Each trading instance is identified by a stable `instance_id`. This becomes the primary isolation key across runtime files, database records, executor state transitions, and operator tooling.

The supervisor is responsible for orchestration. Workers are responsible for signal generation for exactly one configured instance.

## Instance Model

### Definition

An instance is one independently managed trading unit with the following fields:

- `id`
- `enabled`
- `strategy`
- `symbol`
- `timeframe`
- `capital_usdt`
- `sizing.mode`
- `sizing` mode-specific parameters

Examples:

- `ott_eth_5m`
- `ott_btc_5m`
- `risk25_sol_5m`

### Invariants

Each instance must satisfy these rules:

1. `id` is unique across the full config file
2. `strategy` maps to a strategy directory that exists in `strategies/jesse/`
3. `symbol` is valid for the runtime's market data path
4. `capital_usdt` is positive
5. the `sizing` block is valid for the selected sizing mode

The system should reject invalid instance configurations during startup instead of allowing partially broken runtime behavior.

## Configuration Design

### Config File

Add one repository-owned config file for dry-run instances, for example:

- `configs/dryrun_instances.yaml`

Recommended structure:

```yaml
instances:
  - id: ott_eth_5m
    enabled: true
    strategy: Ott2butKAMA
    symbol: ETHUSDT
    timeframe: 5m
    capital_usdt: 1000
    sizing:
      mode: fixed_fraction
      position_fraction: 0.2
      leverage: 10

  - id: ott_btc_5m
    enabled: true
    strategy: Ott2butKAMA
    symbol: BTCUSDT
    timeframe: 5m
    capital_usdt: 800
    sizing:
      mode: fixed_fraction
      position_fraction: 0.15
      leverage: 10

  - id: risk25_sol_5m
    enabled: true
    strategy: Ott2butKAMA_RiskManaged25
    symbol: SOLUSDT
    timeframe: 5m
    capital_usdt: 1200
    sizing:
      mode: risk_per_trade
      risk_fraction: 0.025
```

### Why Config-Driven Instances

This is the narrowest design that cleanly supports:

- adding or removing symbols without code edits
- running the same strategy against multiple markets
- applying different capital rules per instance
- generating instance-specific logs and status output

Hard-coded constants are acceptable for a single instance but become a source of coupling and operator error once multiple combinations are required.

## Supervisor and Worker Architecture

### Supervisor Responsibilities

The supervisor should:

- load and validate the instance config
- filter to enabled instances
- sync required strategy code into the runtime workspace
- start one worker per enabled instance
- stop workers
- report aggregate and per-instance status
- mark the runtime `degraded` when some workers fail but others continue running

The supervisor should remain an orchestration layer and should not embed trading logic.

### Worker Responsibilities

Each worker should:

- operate on exactly one configured instance
- fetch market data for its own symbol/timeframe
- track its own latest processed candle
- run its own strategy logic
- emit signals tagged with its own `instance_id`
- write its own heartbeat and logs

This isolates failures and makes it possible to reason about one strategy-symbol unit without reading unrelated runtime state.

### Recommended Execution Model

Externally, operators continue to use unified scripts such as:

- `bash scripts/dryrun_start.sh`
- `bash scripts/dryrun_status.sh`
- `bash scripts/dryrun_stop.sh`

Internally, those scripts should delegate to the new supervisor instead of assuming exactly one executor process and one Jesse loop.

## Runtime State Isolation

The current runtime stores single global state files, which is incompatible with multi-instance operation.

The runtime should instead store per-instance state under an instance directory, for example:

```text
runtime/dryrun/instances/ott_eth_5m/
  logs/worker.log
  heartbeats/worker.heartbeat
  state/last_action.txt
  state/last_candle_ts.txt

runtime/dryrun/instances/risk25_sol_5m/
  logs/worker.log
  heartbeats/worker.heartbeat
  state/last_action.txt
  state/last_candle_ts.txt
```

Benefits:

- one instance cannot overwrite another instance's last action or last candle marker
- heartbeat health checks become instance-specific
- operators can inspect failures without mixing unrelated streams

## Database Isolation Model

### Core Requirement

The current runtime behavior is too dependent on `symbol` as the state key. That is not safe when multiple strategies can trade the same symbol independently.

The database model should therefore elevate `instance_id` to a first-class key.

### Signal Events

`signal_events` should store at least:

- `instance_id`
- `strategy`
- `symbol`
- `timeframe`
- existing signal metadata

This allows two strategies to emit separate `ETHUSDT` signals without ambiguity.

### Execution Events

`execution_events` should also store `instance_id` directly, even if the associated signal can be joined later.

Direct storage improves:

- operator queries
- per-instance summaries
- execution debugging

### Position State

`position_state` must no longer be treated as symbol-global state.

The effective ownership of a position record should be the instance. The implementation can still store `symbol` and `strategy` for readability, but the state transition logic and retrieval logic should use `instance_id` as the primary isolation key.

### Executor Locking

Executor locking should shift from a symbol-based advisory lock to an instance-based advisory lock.

Without this change, two independent strategies trading the same symbol would serialize against the same lock and risk state contamination.

## Signal and Execution Flow

The signal flow should become:

1. worker loads instance config
2. worker detects a new candle for its own symbol/timeframe
3. worker computes strategy intent
4. worker normalizes intent into an action
5. worker computes sizing for that instance when the action opens a position
6. worker emits a signal with `instance_id`, strategy metadata, and sizing payload
7. executor consumes the signal and updates only that instance's position state

The signal payload should carry the sizing result so the executor can remain focused on state transitions instead of recomputing trading rules.

## Capital Allocation and Sizing Design

### Capital Allocation Model

Each instance has its own independent `capital_usdt` allocation. This is a configuration value, not a dynamic shared account.

The first version should treat this as a static per-instance capital pool. That is sufficient for the stated goal and avoids prematurely introducing portfolio accounting.

### Sizing Boundary

Sizing should be a runtime capability, not ad hoc logic spread across strategy classes.

The strategy should answer:

- what action should happen

The sizing layer should answer:

- how large the new position should be for this instance

### Supported Sizing Modes

The first version should support three sizing modes:

1. `fixed_fraction`
2. `fixed_notional`
3. `risk_per_trade`

#### `fixed_fraction`

Use a fixed fraction of the instance capital allocation for each new position.

Recommended parameters:

- `position_fraction`
- optional `leverage`

This is the natural fit for the current baseline strategy behavior.

#### `fixed_notional`

Open each position with a fixed configured notional amount.

Recommended parameter:

- `notional_usdt`

This is useful when you want strict exposure caps per market regardless of instance capital size.

#### `risk_per_trade`

Compute quantity from allowed loss divided by stop distance.

Recommended parameters:

- `risk_fraction` or `risk_bps`

This is the natural fit for risk-managed strategies.

### Stop Price Requirement

`risk_per_trade` must require a reliable stop price.

The recommended design is for the strategy to include `stop_price` in the signal payload for opening actions. The sizing layer then uses:

- entry price
- stop price
- capital allocation
- allowed risk fraction

to compute quantity.

If an instance is configured for `risk_per_trade` but a required stop price is unavailable, the runtime should reject the open signal for that instance instead of silently falling back to a different sizing rule.

### Executor Boundary

The executor should consume already-sized signals and remain focused on:

- transition decisions
- persistence
- position state updates

It should not be responsible for inferring how large a position should have been.

## Error Handling

### Startup Validation

Invalid instance definitions should fail before workers are started.

Examples:

- duplicate `id`
- missing strategy path
- invalid symbol or timeframe
- non-positive capital
- incomplete sizing config
- `risk_per_trade` without the ability to supply stop prices

### Runtime Failures

One worker failure should not require all workers to stop.

The supervisor should surface an aggregate status such as:

- `running`
- `degraded`
- `stopped`

### Log Context

Every important runtime error should include:

- `instance_id`
- `strategy`
- `symbol`

This is mandatory in a multi-instance system because the operator must be able to identify which instance failed without reconstructing context manually.

### No-Signal vs Broken-State Clarity

The runtime must clearly distinguish these conditions:

- waiting for a new candle
- new candle processed but no trade action
- market fetch failure
- signal persistence failure
- executor consumption failure

This directly addresses the current operator ambiguity between “no signal” and “system failure”.

## Observability and Status Reporting

### Aggregate Status

`dryrun_status` should report supervisor health and an overview such as:

```text
supervisor: degraded
instances_total: 3
instances_running: 2
instances_failed: 1
```

### Per-Instance Status

The operator should also see a line per instance, including enough data to know whether the worker is:

- running
- stale
- stopped
- failed
- idle with no recent signals

### Per-Instance Validation Summary

The dry-run summary tooling should evolve from one global rollup into an instance-aware summary, including:

- signal count per instance
- execution count per instance
- latest signal time per instance
- latest execution time per instance

This is the minimum observability needed for operating more than one strategy-symbol combination safely.

## Testing Strategy

### Config Validation Tests

Add tests that reject invalid instance definitions, including duplicate IDs and incomplete sizing blocks.

### Worker Unit Tests

Add tests for a single configured worker verifying:

- new candles are detected per instance
- repeated candles do not re-emit signals
- `flat` intent does not emit open signals
- instance state files remain isolated

### Executor Isolation Tests

Add tests proving that two instances on the same symbol do not share:

- current side resolution
- advisory locks
- position state transitions

### Supervisor Integration Tests

Add integration coverage showing that the supervisor can:

- start multiple instances
- report mixed health correctly
- keep logs and heartbeats separate
- avoid blocking healthy instances when one instance fails

## Implementation Phasing

This work should be implemented in three phases.

### Phase 1: Parameterize the Single-Instance Runtime

Remove hard-coded strategy, symbol, and timeframe assumptions from the current live loop so one worker can be driven by explicit instance input.

This creates a reusable worker core without yet introducing full multi-instance orchestration.

### Phase 2: Introduce Instance Isolation Across Persistence and Runtime State

Add `instance_id` to the relevant persistence paths and runtime file layout.

This phase is the true safety boundary. Multi-instance operation should not proceed until this isolation is complete.

### Phase 3: Add Supervisor-Orchestrated Multi-Instance Execution

Load the instance config, start one worker per enabled instance, and upgrade operator commands and summaries to work across the full set.

## Acceptance Criteria

This design is satisfied when:

1. the runtime can configure multiple enabled strategy-symbol instances from one repository-owned config file
2. each instance has independent capital allocation and sizing settings
3. worker logs, heartbeats, and local runtime state are isolated per instance
4. signal, execution, and position handling are isolated by `instance_id`
5. two different strategies can operate on the same symbol without sharing position state
6. unified supervisor commands can start, stop, and report status across all enabled instances
7. operator summaries can distinguish “no signal” from runtime failure on a per-instance basis

## Risks and Mitigations

### Risk: symbol-level state leaks remain after partial migration

Mitigation:

- treat `instance_id` migration as a hard gate
- add executor isolation tests before enabling multi-instance execution

### Risk: sizing rules remain split across strategy code and runtime code

Mitigation:

- define a clear sizing boundary early
- require runtime-owned sizing selection by `sizing.mode`

### Risk: one bad instance causes confusing operator output

Mitigation:

- add explicit supervisor aggregate states
- keep per-instance logs and per-instance health reporting

### Risk: scope drifts into a full portfolio management system

Mitigation:

- keep the first version to static per-instance capital allocations
- defer dynamic rebalancing and shared-margin optimization

## Follow-Up

Likely future work after this step:

1. add instance-scoped pause or disable commands without editing config manually
2. add portfolio-level reporting on top of isolated instance execution
3. add richer sizing modes for grid or layered entries once the instance model is stable
