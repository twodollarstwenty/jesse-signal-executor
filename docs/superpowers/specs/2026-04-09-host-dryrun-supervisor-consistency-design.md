# Host Dry-Run Supervisor Consistency Design

## Background

The host dry-run stack currently relies heavily on pid files. This creates inconsistency when:

- a process starts but heartbeat is delayed
- `dryrun_start.sh` removes the pid file before the process actually dies
- `dryrun_status.sh` and `dryrun_stop.sh` look only at pid files and conclude the process is stopped even when it is still running

This is the root cause behind multiple confusing operator experiences:

- `status` says stopped but the process is alive
- `stop` says already stopped but an old process still exists
- `start` can launch duplicate instances because the old instance is invisible once its pid file is removed

## Goal

Make `dryrun_start.sh`, `dryrun_status.sh`, and `dryrun_stop.sh` use the real process state as the source of truth, not pid files alone.

## Scope

### In Scope

- Host dry-run process detection
- Host dry-run pid-file consistency
- Duplicate-instance prevention
- Better startup timeout handling

### Out of Scope

- Docker supervisor behavior
- Changing strategy logic
- Notification logic

## Core Principle

Pid files are useful hints, but not authoritative truth.

The authoritative truth is:

- whether a matching process is actually running
- whether it belongs to the expected dry-run runtime instance

## Proposed Approach

### Process Identity

The scripts should identify processes using both:

- script path
- runtime-specific heartbeat path or equivalent runtime-specific marker

This allows them to recognize orphaned or still-running processes even when pid files are missing or stale.

### Start Behavior

When starting a process:

- if a matching process already exists for the same runtime instance, do not start a second one
- if startup times out before heartbeat appears, do not silently drop pid tracking unless the process is truly gone

### Status Behavior

If pid file is missing, status should still try to discover a matching live process for the same runtime instance.

Only if no matching process exists should it print `stopped`.

### Stop Behavior

If pid file is missing, stop should still attempt to discover and terminate matching processes for the same runtime instance.

## Acceptance Criteria

1. `status` no longer reports `stopped` while a matching dry-run process is still alive
2. `stop` can terminate matching dry-run processes even if pid files are missing
3. `start` does not launch duplicate instances when an orphaned matching process already exists
4. startup timeout handling does not leave the system in a misleading state

## Follow-Up

Once this consistency layer is stable, future work can add stronger lifecycle states such as explicit warmup or richer operator diagnostics.
