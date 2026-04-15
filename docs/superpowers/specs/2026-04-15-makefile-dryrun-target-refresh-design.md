# Makefile Dryrun Target Refresh Design

## Background

The dry-run runtime moved from an older single-loop layout to a supervisor-managed multi-instance layout.

The `Makefile` still contains a small set of dry-run targets that assume the previous runtime shape:

- `dryrun-reset` still waits on old process names and removes old pid and state files.
- `dryrun-log` still tails the old single log file.

This creates operator confusion because `make dryrun-up` and `make dryrun-down` already work with the current supervisor flow, while `dryrun-reset` and `dryrun-log` still point at obsolete paths.

## Goal

Refresh the stale `Makefile` dry-run targets so they match the current supervisor and per-instance runtime layout without expanding scope into unrelated command changes.

## Scope

### In Scope

- Update `dryrun-reset` to clean the current supervisor and instance runtime layout.
- Update `dryrun-log` to read the current instance worker logs.
- Keep the existing database reset behavior.
- Verify the refreshed targets with direct `make` execution.

### Out of Scope

- Reworking `dryrun-up`, `dryrun-down`, `dryrun-watch`, or `dryrun-debug`.
- Adding new supervisor-only `make` targets.
- Reorganizing runtime directories.
- Changing supervisor lifecycle semantics.

## Design

### `dryrun-reset`

`dryrun-reset` should remain the operator's cleanup command, but it must act on the current runtime layout.

The command should:

1. call `scripts/dryrun_stop.sh` first
2. remove supervisor pid files under `runtime/dryrun/supervisor/pids/`
3. remove per-instance log files under `runtime/dryrun/instances/*/logs/`
4. remove per-instance heartbeat files under `runtime/dryrun/instances/*/heartbeats/`
5. remove per-instance state files under `runtime/dryrun/instances/*/state/`
6. clear `signal_events`, `execution_events`, and `position_state`
7. print the resulting status via `scripts/dryrun_status.sh`

The old polling loop for `scripts/run_executor_loop.py` and `scripts/run_jesse_dryrun_loop.py` should be removed because those process names are no longer the active runtime contract for the multi-instance supervisor flow.

### `dryrun-log`

`dryrun-log` should stop pointing to `runtime/dryrun/logs/jesse-dryrun.log`.

The minimal acceptable behavior is to tail the current worker logs under `runtime/dryrun/instances/*/logs/worker.log` so the operator sees live instance output from the new layout.

This keeps the target useful without introducing a larger log aggregation layer.

## Error Handling

- Missing runtime files should not cause reset to fail.
- Log target behavior may naturally fail if no worker logs exist yet; this is acceptable and reflects actual runtime state.
- Database reset behavior remains unchanged.

## Testing

Verification should cover:

1. `make dryrun-up && make dryrun-down` still behaves correctly after the `Makefile` edit
2. `make dryrun-reset` removes current runtime artifacts and exits successfully
3. `dryrun-log` references the new worker log path rather than the removed legacy file

## Rationale

This is intentionally a narrow refresh. The problem is not the overall dry-run workflow; it is that two `Makefile` targets still encode the old single-instance runtime assumptions. Updating only those targets fixes the operator-facing mismatch while keeping the change small and low risk.
