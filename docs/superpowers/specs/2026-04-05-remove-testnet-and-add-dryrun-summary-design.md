# Remove Testnet Stage And Add Dry-Run Summary Design

## Background

The repository has reached a stable host-level dry-run workflow. Backtest comparison, signal production, executor consumption, and non-container dry-run validation are already functioning. However, the project guidance still assumes a promotion path of:

- backtest
- dry-run
- testnet
- tiny live

That no longer matches the desired operating model. The user wants the repository to stop treating `testnet` as a formal stage entirely.

At the same time, the project still lacks one of the most important remaining capabilities for the current stage: a concise, repeatable dry-run summary that turns database activity into a human-readable validation result.

## Goal

Update the repository so that:

1. `testnet` is no longer treated as a formal stage in rules, guidance, or workflow entrypoints
2. the promotion path becomes `backtest -> dry-run -> tiny live`
3. the repository has a first-class dry-run summary capability that can be used as validation evidence

## Scope

### In Scope

- Update project rules and documentation to remove `testnet` as a formal stage.
- Update skill metadata and guidance that currently assume `testnet` is required.
- Add a dry-run summary script that reads database state and outputs a compact validation summary.
- Update runbook guidance to include the new summary step.

### Out of Scope

- Implementing tiny live trading.
- Adding exchange API integrations.
- Building a UI or dashboard.
- Redesigning all historical documents that mention `testnet` in narrative or legacy context unless they actively shape current behavior.

## Proposed Approach

The work should happen in two coordinated parts.

### Part 1: Stage Model Cleanup

Repository guidance should consistently describe only three stages:

1. backtest
2. dry-run
3. tiny live

This means:

- `rules/promotion-gates.md` should remove the `dry-run -> testnet` section and replace it with a direct `dry-run -> tiny live` gate
- `AGENT.md` should stop listing `testnet` as part of the official stage ladder
- safety and evidence rules should stop referring to `testnet` as a required promotion checkpoint
- the skills layer should no longer present `testnet` as a mandatory destination

The goal is not to erase every historical mention of the word `testnet`, but to ensure current repository rules and workflows no longer depend on it.

### Part 2: Dry-Run Summary Capability

Add one repository-owned script that queries PostgreSQL and summarizes the current dry-run state into a compact report suitable for operator use and promotion evidence.

The summary should answer these questions directly:

- how many `signal_events` exist in the inspected window
- how many `execution_events` exist in the inspected window
- how many signals reached `execute`, `ignored`, and `rejected`
- when the most recent signal and execution occurred
- whether the dry-run window shows active traffic

This should become the standard lightweight evidence layer between raw database inspection and any future promotion decision.

## Stage Model Design

### New Promotion Path

The canonical stage path becomes:

- backtest
- dry-run
- tiny live

### Gate Meaning

#### backtest -> dry-run

No functional change in principle:

- backtest results must be reproducible
- strategy behavior must be explainable
- major risks must be known before dry-run starts

#### dry-run -> tiny live

This gate replaces the previous two-step `dry-run -> testnet -> tiny live` model.

The repository should require dry-run evidence that covers at least:

- sustained event growth over the observation window
- no obvious duplicated consumption pattern
- no obvious state drift in the execution path
- enough logs and summaries to explain what happened
- close-only / halt safety expectations documented before tiny live is considered

## Dry-Run Summary Design

### New Script

Add a new script under `scripts/`, recommended name:

- `scripts/summarize_dryrun_validation.py`

### Responsibilities

The script should:

- connect using the existing project database environment variables
- query `signal_events`
- query `execution_events`
- aggregate counts for a selected time window
- print a compact text summary suitable for terminal use

### Minimum Output

The output should include at least:

- inspected window description
- total signal count in window
- total execution count in window
- signal status counts by `execute`, `ignored`, `rejected`
- latest signal timestamp
- latest execution timestamp

Optional fields are acceptable if they remain small and directly useful.

### Time Window

The script should support a simple operator-oriented window selection, such as:

- `--minutes 60`

This is preferred over making the operator provide raw timestamps for the common case.

### Output Format

Default output should be human-readable plain text.

If there is a later need for machine-readable output, that can be added separately. It is not required for this step.

## Documentation Updates

### `docs/runbook.md`

The runbook should:

- remove any current-stage implication that `testnet` is required
- add the dry-run summary command to the non-container dry-run validation flow
- explain that the summary script is part of the evidence used before tiny live is considered

### `README.md`

The README should stop implying Docker or other obsolete stage assumptions if they conflict with the active workflow language.

### Skills and Rules

The repository should update current guidance so that:

- `promote-to-testnet` is either removed or clearly deprecated
- `promote-to-live` no longer assumes `testnet` is a prerequisite
- `run-dryrun-validation` points to the new dry-run summary evidence path

## Acceptance Criteria

This work is complete when:

1. the repository's current stage model is `backtest -> dry-run -> tiny live`
2. no current rule or workflow still requires `testnet` as a formal step
3. a dry-run summary script exists and runs against PostgreSQL
4. the summary output includes the minimum signal/execution evidence fields
5. the runbook explains how to use the summary during dry-run validation

## Risks and Mitigations

### Risk: historical references to testnet remain in low-priority docs

Mitigation:

- clean the rules, agent guidance, README, and active skills first
- tolerate legacy references only where they do not shape current behavior

### Risk: summary output becomes too detailed to be useful

Mitigation:

- keep the first version small and terminal-friendly
- optimize for operator readability, not exhaustiveness

### Risk: stage cleanup drifts into live-trading implementation

Mitigation:

- limit this work to rules, docs, skill guidance, and dry-run evidence tooling

## Follow-Up

Possible future work after this step:

1. persist dry-run validation summaries to dated artifacts
2. define a stricter tiny live checklist with budget and rollback fields
3. add richer status grouping or time-series reporting if the summary script proves useful
