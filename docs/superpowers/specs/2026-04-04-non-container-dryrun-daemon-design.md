# Non-Container Dry-Run Daemon Design

## Background

The repository already has the skeleton for non-container dry-run process management, but the current `jesse-dryrun` loop still uses `scripts/verify_jesse_imports.py` as its default command. That command is only an environment check. It can keep a process alive and refresh heartbeats, but it cannot produce trading signals.

As a result, the current host-level dry-run path can appear healthy at the process level while still failing the real business-level acceptance criteria: `signal_events` and `execution_events` do not grow during the observation window.

The goal of this design is to replace that placeholder behavior with the final intended behavior: a real Jesse execution chain that continuously produces signals through the existing bridge, while executor continues consuming them.

## Goal

Provide a non-Docker dry-run daemon workflow that starts two long-running host processes and uses a real Jesse execution chain as the default `jesse-dryrun` behavior, so that:

1. `jesse-dryrun` continuously produces signals into `signal_events`
2. `executor` continuously consumes signals into `execution_events`
3. operators can manage the workflow with `start`, `status`, `stop`, `logs`, and `heartbeat`
4. the repository's default non-container dry-run path is the final implementation, not a placeholder

## Scope

### In Scope

- Keep the host-level two-process daemon model.
- Keep `scripts/dryrun_start.sh`, `scripts/dryrun_status.sh`, and `scripts/dryrun_stop.sh` as the main operational interface.
- Replace the default `jesse-dryrun` command with a real Jesse execution entrypoint.
- Add a dedicated project-owned wrapper entrypoint for Jesse dry-run orchestration if needed.
- Keep runtime artifacts under `runtime/dryrun/`.
- Update tests and runbook to reflect final behavior.
- Verify both process health and business-level event growth.

### Out of Scope

- Docker-based dry-run orchestration.
- `launchd`, `supervisord`, `pm2`, or other external process supervisors.
- Reworking the executor state machine or changing event schema.
- Adding automatic restart strategies beyond the existing shell start/stop control.

## Final Approach

### Process Model

The final non-container dry-run workflow keeps two long-running processes:

1. `executor`
   - Entry: `scripts/run_executor_loop.py`
   - Responsibility: poll `signal_events`, apply the existing decision/state-machine logic, and write `execution_events`

2. `jesse-dryrun`
   - Entry: `scripts/run_jesse_dryrun_loop.py`
   - Responsibility: repeatedly invoke the final Jesse execution entrypoint so the strategy actually runs and produces signals through the existing bridge

### Jesse Entrypoint Shape

The repository should own a single formal Jesse dry-run entrypoint under `scripts/`. That entrypoint is the final business-level command used by `run_jesse_dryrun_loop.py` by default.

Its responsibilities are:

- verify that `runtime/jesse_workspace` exists and is bootstrapped
- verify that `runtime/jesse_workspace/.venv` exists and can run Jesse
- sync the strategy and custom indicators required by `Ott2butKAMA`
- switch execution into the Jesse workspace
- invoke the real Jesse execution path that drives the strategy and bridge
- fail loudly with actionable stderr if bootstrap, sync, or Jesse execution is broken

This wrapper exists to make the repository's default dry-run path deterministic and self-contained. Operators should not need to manually activate environments or manually sync strategy files before starting the daemon.

## Architecture

### Components

#### `scripts/dryrun_start.sh`

Responsibilities:

- ensure runtime directories exist
- clean or replace stale pid files
- start `executor` with the project `.venv`
- start `jesse-dryrun` with `runtime/jesse_workspace/.venv`
- wait for startup confirmation
- keep rollback behavior if the second process fails to start

Final behavior requirement:

- startup should be considered successful only after the process identity is confirmed, and ideally after the first heartbeat is observed or the process is within an explicit warmup window

#### `scripts/dryrun_status.sh`

Responsibilities:

- report whether pid files exist and match the expected commands
- report whether heartbeats are fresh
- print `running`, `stopped`, or `stale`
- support the final Jesse entrypoint without any special-case operator action

Final behavior requirement:

- avoid misleading immediate post-start `stale` output when a process is still in its expected warmup period

#### `scripts/dryrun_stop.sh`

Responsibilities:

- stop both daemon processes cleanly
- remove stale pid files
- avoid killing unrelated processes when pid files are stale or reused

#### `scripts/run_executor_loop.py`

Responsibilities remain unchanged:

- poll business events
- call `run_once()` repeatedly
- write heartbeat after successful loop iterations

#### `scripts/run_jesse_dryrun_loop.py`

This file remains the long-running scheduler, but its default command changes from an import-check placeholder to the final Jesse execution entrypoint.

Responsibilities:

- read configurable interval and command from environment
- default to the repository-owned Jesse dry-run entrypoint
- run the command repeatedly
- write heartbeat only after a successful cycle

#### Final Jesse Dry-Run Entrypoint

This is the new final business entrypoint used by the loop.

Responsibilities:

- perform preflight checks for workspace and venv
- sync strategy and indicators
- run the real Jesse chain that can emit signals through the existing bridge
- return non-zero on failure so the surrounding loop and status scripts reflect degraded state

## Runtime Layout

Runtime files stay under `runtime/dryrun/`:

- `runtime/dryrun/pids/executor.pid`
- `runtime/dryrun/pids/jesse-dryrun.pid`
- `runtime/dryrun/logs/executor.log`
- `runtime/dryrun/logs/jesse-dryrun.log`
- `runtime/dryrun/heartbeats/executor.heartbeat`
- `runtime/dryrun/heartbeats/jesse-dryrun.heartbeat`

This directory is only for operational state, not source data.

## Data Flow

1. `bash scripts/dryrun_start.sh`
2. `executor` starts and begins polling for `signal_events`
3. `jesse-dryrun` starts and invokes the repository-owned final Jesse entrypoint
4. the final Jesse entrypoint syncs the strategy, enters the Jesse workspace, and runs the real Jesse execution path
5. the existing bridge writes trading signals into `signal_events`
6. `executor` consumes those records and writes `execution_events`
7. each loop updates its heartbeat after successful progress
8. `bash scripts/dryrun_status.sh` reports health from pid and heartbeat state

## Health Model

Two layers of health remain necessary:

### Process Health

- pid file exists
- process is alive
- pid still belongs to the expected script

### Logic Health

- heartbeat is fresh
- Jesse entrypoint successfully completes loop iterations

Suggested heartbeat thresholds remain:

- executor: 30 seconds
- jesse-dryrun: 60 seconds

Status values remain:

- `running`
- `stopped`
- `stale`

Meaning:

- `running`: process identity is correct and heartbeat is fresh
- `stopped`: pid missing or process no longer matches the expected command
- `stale`: process exists but is not making logical progress

## Error Handling

### Jesse Entrypoint Failure

If strategy sync, workspace setup, or Jesse execution fails:

- stderr must land in `runtime/dryrun/logs/jesse-dryrun.log`
- the loop iteration must fail
- no heartbeat should be written for that failed cycle
- `dryrun_status.sh` should eventually report `stale`

### Startup Failure

If `jesse-dryrun` fails during startup:

- `dryrun_start.sh` should continue to roll back `executor`
- the user should see a clear startup failure message with the relevant log path

### Warmup Window

The current immediate-post-start false `stale` result is an operator experience problem. Final behavior should explicitly account for startup warmup so that status does not mislead operators during the first heartbeat window.

The implementation may solve this either by:

- waiting for the first heartbeat before declaring startup success, or
- representing a short warmup period in status logic

The chosen implementation must still preserve the clear distinction between true steady-state `running` and true `stale`.

## Runbook Requirements

The runbook must describe the final non-container dry-run workflow as the default host-level operational path.

It must include:

- prerequisites for both virtual environments
- the fact that the daemon runs a real Jesse execution chain, not an import-check command
- `start`, `status`, and `stop` commands
- log and heartbeat paths
- troubleshooting order:
  1. `dryrun_status.sh`
  2. `runtime/dryrun/logs/*.log`
  3. `signal_events` growth
  4. `execution_events` growth

## Testing Requirements

### Automated Tests

- update loop tests so the default Jesse command reflects the final entrypoint, not `verify_jesse_imports.py`
- add tests for the new Jesse wrapper entrypoint behavior where practical
- keep daemon script tests for start/stop/status behavior
- keep status-script tests around pid matching and status output

### Host-Level Validation

A complete acceptance run must verify:

1. `bash scripts/dryrun_start.sh` starts both processes
2. after warmup, `bash scripts/dryrun_status.sh` reports both as `running`
3. during the observation window, `signal_events` count increases
4. during the observation window, `execution_events` count increases
5. `bash scripts/dryrun_stop.sh` stops both processes cleanly

## Acceptance Criteria

The final design is complete only when all of the following are true:

1. the default non-container dry-run path uses a real Jesse execution chain
2. `jesse-dryrun` no longer defaults to `scripts/verify_jesse_imports.py`
3. the daemon can be started and observed entirely from host-level scripts
4. `signal_events` grows during the validation window
5. `execution_events` grows during the validation window
6. logs and status outputs are sufficient to diagnose failure
7. the working tree can distinguish source changes from generated runtime artifacts

## Risks and Mitigations

### Risk: Jesse CLI invocation details are brittle

Mitigation:

- encapsulate Jesse invocation in a single repository-owned wrapper
- test the wrapper directly where practical

### Risk: Strategy sync drift causes silent no-op behavior

Mitigation:

- make strategy sync part of the final entrypoint, not a manual prerequisite
- fail fast if expected strategy files are missing

### Risk: startup status is misleading during warmup

Mitigation:

- explicitly model warmup in startup or status logic

### Risk: process-level health passes while business flow is broken

Mitigation:

- treat event growth checks as part of final acceptance, not optional observation

## Follow-Up Work

Out of scope for this step, but natural future enhancements are:

1. summary tooling for `execute` / `ignored` / `rejected` counts
2. automatic restart policies
3. optional `launchd` integration once the host-level workflow is stable
