# Containerized One-Command Dry-Run Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `docker compose up -d` launch the full dry-run stack using the current dry-run runtime path.

**Architecture:** Reuse the existing executor and signal Docker images and add two containerized dry-run services to Compose: `executor` and `jesse-dryrun`. Wire them to the existing loop scripts, use container-appropriate DB host values, reuse heartbeat healthchecks, and validate that `signal_events` and `execution_events` both grow in the containerized path.

**Tech Stack:** Docker Compose, Python 3.13, PostgreSQL, existing dry-run scripts

---

## File Structure

- Modify: `docker-compose.yml`
  - Add `executor` and `jesse-dryrun` services back using the current dry-run runtime path.
- Modify: `docs/runbook.md`
  - Document Docker Compose as the one-command dry-run deployment path.
- Create: `tests/test_docker_dryrun_compose.py`
  - Verify compose file contains the expected dry-run services and healthchecks.

### Task 1: Add failing tests for the Compose dry-run services

**Files:**
- Create: `tests/test_docker_dryrun_compose.py`

- [ ] **Step 1: Write the failing test file**

Create `tests/test_docker_dryrun_compose.py` with the following content:

```python
from pathlib import Path

import yaml


def test_compose_contains_executor_and_jesse_dryrun_services():
    compose = yaml.safe_load(Path("docker-compose.yml").read_text())

    services = compose["services"]

    assert "executor" in services
    assert "jesse-dryrun" in services


def test_executor_and_jesse_dryrun_use_postgres_hostname_and_healthchecks():
    compose = yaml.safe_load(Path("docker-compose.yml").read_text())
    services = compose["services"]

    executor = services["executor"]
    dryrun = services["jesse-dryrun"]

    assert executor["environment"]["POSTGRES_HOST"] == "postgres"
    assert dryrun["environment"]["POSTGRES_HOST"] == "postgres"
    assert "healthcheck" in executor
    assert "healthcheck" in dryrun
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_docker_dryrun_compose.py -q
```

Expected: FAIL because the dry-run services are not in the compose file yet.

### Task 2: Add the containerized dry-run services to Compose

**Files:**
- Modify: `docker-compose.yml`
- Test: `tests/test_docker_dryrun_compose.py`

- [ ] **Step 1: Add `executor` and `jesse-dryrun` services**

Update `docker-compose.yml` so it includes these service shapes in addition to the existing services:

```yaml
  executor:
    build:
      context: .
      dockerfile: infra/docker/executor.Dockerfile
    command: python3 scripts/run_executor_loop.py
    environment:
      POSTGRES_HOST: postgres
      POSTGRES_PORT: 5432
      POSTGRES_DB: ${POSTGRES_DB:-jesse_db}
      POSTGRES_USER: ${POSTGRES_USER:-jesse_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-password}
      NOTIFY_ENABLED: ${NOTIFY_ENABLED:-0}
      WECOM_BOT_WEBHOOK: ${WECOM_BOT_WEBHOOK:-}
    volumes:
      - .:/app
    depends_on:
      - postgres
    healthcheck:
      test: ["CMD", "python3", "scripts/check_heartbeat.py", "--path", "/tmp/executor.heartbeat", "--max-age-seconds", "30"]
      interval: 10s
      timeout: 5s
      retries: 3

  jesse-dryrun:
    build:
      context: .
      dockerfile: infra/docker/signal.Dockerfile
    command: python3 scripts/run_jesse_dryrun_loop.py
    environment:
      POSTGRES_HOST: postgres
      POSTGRES_PORT: 5432
      POSTGRES_DB: ${POSTGRES_DB:-jesse_db}
      POSTGRES_USER: ${POSTGRES_USER:-jesse_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-password}
      NOTIFY_ENABLED: ${NOTIFY_ENABLED:-0}
      WECOM_BOT_WEBHOOK: ${WECOM_BOT_WEBHOOK:-}
    volumes:
      - .:/app
    depends_on:
      - postgres
    healthcheck:
      test: ["CMD", "python3", "scripts/check_heartbeat.py", "--path", "/tmp/jesse-dryrun.heartbeat", "--max-age-seconds", "60"]
      interval: 10s
      timeout: 5s
      retries: 3
```

Do not reintroduce the old placeholder implementation.

- [ ] **Step 2: Run the compose tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_docker_dryrun_compose.py -q
```

Expected: PASS.

### Task 3: Document the one-command Docker dry-run path

**Files:**
- Modify: `docs/runbook.md`

- [ ] **Step 1: Add Docker Compose dry-run commands to the runbook**

Add a short section near `## Non-Container Dry-Run` explaining the containerized path:

```md
## Docker Dry-Run

一键启动：

```bash
docker compose up -d
```

查看状态：

```bash
docker compose ps
```

查看日志：

```bash
docker compose logs -f executor jesse-dryrun
```

停止：

```bash
docker compose down
```
```

Mention that this path launches the same current dry-run runtime model in containers.

### Task 4: Validate the containerized path manually

**Files:**
- No new files required

- [ ] **Step 1: Start the full stack**

Run:

```bash
docker compose up -d
```

Expected: `postgres`, `executor`, and `jesse-dryrun` start successfully.

- [ ] **Step 2: Check container status**

Run:

```bash
docker compose ps
```

Expected: `executor` and `jesse-dryrun` are healthy.

- [ ] **Step 3: Verify event flow**

Run:

```bash
set -a && source .env && set +a
source .venv/bin/activate
python3 scripts/summarize_dryrun_validation.py --minutes 60
```

Expected: `signal_count` and `execution_count` are non-zero or increasing during observation.

- [ ] **Step 4: Stop the stack**

Run:

```bash
docker compose down
```

Expected: containers stop cleanly.

### Task 5: Final verification

**Files:**
- No new files required

- [ ] **Step 1: Run full tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest
```

Expected: PASS.

- [ ] **Step 2: Inspect worktree status**

Run:

```bash
git status --short
```

Expected: only the intended Docker dry-run files and docs appear.

## Self-Review

- Spec coverage: The plan adds Compose dry-run services, documents the one-command path, and validates event flow.
- Placeholder scan: All tasks include exact files, concrete YAML shapes, and direct commands.
- Type consistency: The plan consistently uses `executor` and `jesse-dryrun` as the containerized dry-run services.
