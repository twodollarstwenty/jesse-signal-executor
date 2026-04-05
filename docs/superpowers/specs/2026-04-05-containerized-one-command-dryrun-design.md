# Containerized One-Command Dry-Run Design

## Background

The repository's current dry-run path is stable enough to run on the host with:

- `scripts/dryrun_start.sh`
- `scripts/dryrun_status.sh`
- `scripts/dryrun_stop.sh`

That path already uses the current intended execution model:

- `executor` loop
- `jesse-dryrun` loop
- Jesse signal generation through `run_jesse_live_loop.py`
- database-backed signal and execution events

However, the user now wants the deployment experience to become much simpler:

- one Docker-based command
- one containerized operational model
- no manual host-side process management

The goal is therefore not to revive the old abandoned Docker implementation, but to re-containerize the **current** dry-run architecture.

## Goal

Make `docker compose up -d` the one-command way to launch the full dry-run system.

## Scope

### In Scope

- Containerize the current dry-run runtime path.
- Add `executor` and `jesse-dryrun` services to `docker-compose.yml`.
- Reuse the current loop scripts and current signal-production path.
- Add healthchecks and the minimum operational documentation needed for containerized dry-run.

### Out of Scope

- Reverting to the earlier placeholder-based Docker dry-run design.
- Rewriting the dry-run runtime into a single container.
- Removing the host-side dry-run scripts.

## Proposed Approach

The Docker deployment should mirror the current host-level architecture as closely as possible.

### Services

#### `postgres`

- remains the database for `signal_events` and `execution_events`

#### `executor`

- uses the executor Docker image
- runs `scripts/run_executor_loop.py`
- connects to `postgres` service by container hostname

#### `jesse-dryrun`

- uses the signal Docker image
- runs `scripts/run_jesse_dryrun_loop.py`
- internally reaches the current signal-production path (`run_jesse_live_loop.py`)
- connects to `postgres` service by container hostname

#### `adminer`

- optional but still useful for inspection

## Runtime Model

The current dry-run logic remains the same:

1. `jesse-dryrun` produces strategy signals
2. signals are stored in `signal_events`
3. `executor` consumes and decides
4. execution records are stored in `execution_events`

The containerized version should not introduce a separate dry-run implementation. It should only change how the existing implementation is launched and supervised.

## Configuration

Containers should consume the same core environment configuration but with container-appropriate hostnames.

### Database

Within containers, database host should be:

- `postgres`

not `127.0.0.1`.

### Notifications

Existing notification settings should continue to work via environment variables, especially:

- `NOTIFY_ENABLED`
- `WECOM_BOT_WEBHOOK`

## Healthchecks

Both `executor` and `jesse-dryrun` should expose health through the existing heartbeat-based mechanism.

That means Docker healthchecks should reuse:

- `scripts/check_heartbeat.py`

with service-appropriate heartbeat paths and age thresholds.

## Operational Commands

The target user experience is:

### Start

```bash
docker compose up -d
```

### Status

```bash
docker compose ps
```

### Logs

```bash
docker compose logs -f executor jesse-dryrun
```

### Stop

```bash
docker compose down
```

## Validation Requirements

The containerized model is complete only if the following are true:

1. `docker compose up -d` starts `postgres`, `executor`, and `jesse-dryrun`
2. `docker compose ps` shows `executor` and `jesse-dryrun` as healthy
3. over an observation window, `signal_events` increases
4. over the same window, `execution_events` increases
5. existing WeCom notifications still function when enabled

## Documentation

`README.md` and/or `docs/runbook.md` should present Docker Compose as a valid one-command dry-run deployment path.

The host-level scripts can remain documented as an alternative path, but Docker should become the simplest entrypoint for deployment.

## Acceptance Criteria

This work is complete when:

1. `docker compose up -d` launches the full dry-run stack
2. dry-run event flow works in containers
3. healthchecks reflect actual container runtime health
4. notifications still function when configured
5. the new path is documented

## Risks and Mitigations

### Risk: Docker path drifts away from host path

Mitigation:

- reuse the same loop scripts and signal-production entrypoint
- avoid container-only execution logic

### Risk: container DB config conflicts with host defaults

Mitigation:

- explicitly set container-side database host to `postgres`
- do not rely on host-local defaults inside containers

### Risk: Docker healthchecks pass while event flow is broken

Mitigation:

- require event growth validation as part of acceptance, not just healthchecks

## Follow-Up

Future follow-up may include:

1. a dedicated Docker profile for dry-run-only deployment
2. optional compose overrides for local vs server deployment
3. automated notifier sidecar if stateless dry-run notifications need to run continuously in-container
