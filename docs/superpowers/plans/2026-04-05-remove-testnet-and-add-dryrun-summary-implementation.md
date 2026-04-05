# Remove Testnet Stage And Add Dry-Run Summary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove `testnet` as a formal repository stage and add a first-class dry-run summary script that provides promotion evidence from PostgreSQL.

**Architecture:** Split the work into two coordinated parts. First, update the repository's active rules, guidance, and skills so the canonical path is `backtest -> dry-run -> tiny live`. Second, add one small script under `scripts/` that summarizes dry-run database activity in a terminal-friendly format, then wire that script into the runbook and validation guidance.

**Tech Stack:** Python 3.13, PostgreSQL, pytest, Markdown

---

## File Structure

- Create: `scripts/summarize_dryrun_validation.py`
  - Query `signal_events` and `execution_events` and print a compact dry-run validation summary.
- Create: `tests/test_summarize_dryrun_validation.py`
  - Cover the new summary script behavior.
- Modify: `rules/promotion-gates.md`
  - Remove `testnet` from the official stage ladder.
- Modify: `AGENT.md`
  - Update the stage ladder and required-skill references.
- Modify: `rules/trading-safety.md`
  - Remove testnet as a mandatory checkpoint before tiny live.
- Modify: `rules/verification-and-evidence.md`
  - Update evidence language from `dry-run/testnet` to the new stage model.
- Modify: `skills/run-dryrun-validation/SKILL.md`
  - Point dry-run validation guidance at the new summary evidence path.
- Modify or deprecate: `skills/promote-to-testnet/SKILL.md`
  - Remove it as an active promotion path, or clearly mark it deprecated.
- Modify: `skills/promote-to-live/SKILL.md`
  - Stop assuming `testnet` is a required prior stage.
- Modify: `README.md`
  - Align stage language with the active workflow.
- Modify: `docs/runbook.md`
  - Add the dry-run summary command to the validation flow.

### Task 1: Add failing tests for the dry-run summary script

**Files:**
- Create: `tests/test_summarize_dryrun_validation.py`

- [ ] **Step 1: Write the failing test file**

Create `tests/test_summarize_dryrun_validation.py` with the following content:

```python
from datetime import datetime, timedelta, timezone


def test_render_summary_includes_counts_and_latest_timestamps():
    from scripts.summarize_dryrun_validation import render_summary

    summary = {
        "window_minutes": 60,
        "signal_count": 12,
        "execution_count": 10,
        "signal_status_counts": {"execute": 8, "ignored": 3, "rejected": 1},
        "latest_signal_time": datetime(2026, 4, 5, 3, 0, tzinfo=timezone.utc),
        "latest_execution_time": datetime(2026, 4, 5, 3, 2, tzinfo=timezone.utc),
    }

    text = render_summary(summary)

    assert "window_minutes: 60" in text
    assert "signal_count: 12" in text
    assert "execution_count: 10" in text
    assert "execute: 8" in text
    assert "ignored: 3" in text
    assert "rejected: 1" in text
    assert "latest_signal_time: 2026-04-05T03:00:00+00:00" in text
    assert "latest_execution_time: 2026-04-05T03:02:00+00:00" in text


def test_window_start_uses_minutes_offset():
    from scripts.summarize_dryrun_validation import build_window_start

    now = datetime(2026, 4, 5, 4, 0, tzinfo=timezone.utc)

    assert build_window_start(now=now, minutes=90) == now - timedelta(minutes=90)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_summarize_dryrun_validation.py -q
```

Expected: FAIL with `ModuleNotFoundError` for `scripts.summarize_dryrun_validation`.

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/test_summarize_dryrun_validation.py
git commit -m "test: add failing coverage for dryrun summary"
```

### Task 2: Implement the dry-run summary script

**Files:**
- Create: `scripts/summarize_dryrun_validation.py`
- Test: `tests/test_summarize_dryrun_validation.py`

- [ ] **Step 1: Create the summary script**

Create `scripts/summarize_dryrun_validation.py` with the following content:

```python
import argparse
from datetime import datetime, timedelta, timezone

from apps.shared.db import connect


def build_window_start(*, now: datetime, minutes: int) -> datetime:
    return now - timedelta(minutes=minutes)


def fetch_summary(*, minutes: int) -> dict:
    now = datetime.now(timezone.utc)
    window_start = build_window_start(now=now, minutes=minutes)
    conn = connect()
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*), MAX(signal_time)
                FROM signal_events
                WHERE signal_time >= %s
                """,
                (window_start,),
            )
            signal_count, latest_signal_time = cur.fetchone()

            cur.execute(
                """
                SELECT COUNT(*), MAX(created_at)
                FROM execution_events
                WHERE created_at >= %s
                """,
                (window_start,),
            )
            execution_count, latest_execution_time = cur.fetchone()

            cur.execute(
                """
                SELECT status, COUNT(*)
                FROM signal_events
                WHERE signal_time >= %s
                GROUP BY status
                """,
                (window_start,),
            )
            signal_status_counts = {status: count for status, count in cur.fetchall()}

        return {
            "window_minutes": minutes,
            "signal_count": signal_count,
            "execution_count": execution_count,
            "signal_status_counts": signal_status_counts,
            "latest_signal_time": latest_signal_time,
            "latest_execution_time": latest_execution_time,
        }
    finally:
        conn.close()


def render_summary(summary: dict) -> str:
    lines = [
        f"window_minutes: {summary['window_minutes']}",
        f"signal_count: {summary['signal_count']}",
        f"execution_count: {summary['execution_count']}",
    ]

    for key in ("execute", "ignored", "rejected"):
        lines.append(f"{key}: {summary['signal_status_counts'].get(key, 0)}")

    lines.append(f"latest_signal_time: {summary['latest_signal_time']}")
    lines.append(f"latest_execution_time: {summary['latest_execution_time']}")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", type=int, default=60)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(render_summary(fetch_summary(minutes=args.minutes)))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the targeted tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_summarize_dryrun_validation.py -q
```

Expected: PASS.

- [ ] **Step 3: Commit the summary script**

```bash
git add scripts/summarize_dryrun_validation.py tests/test_summarize_dryrun_validation.py
git commit -m "feat: add dryrun validation summary script"
```

### Task 3: Remove testnet from the active stage model

**Files:**
- Modify: `rules/promotion-gates.md`
- Modify: `AGENT.md`
- Modify: `rules/trading-safety.md`
- Modify: `rules/verification-and-evidence.md`
- Modify: `README.md`

- [ ] **Step 1: Update `rules/promotion-gates.md`**

Rewrite the stage ladder and gates so the file becomes:

```md
# promotion-gates

## 必须

系统晋级顺序固定为：
- backtest
- dry-run
- tiny live

每一阶段都必须完成前一阶段验证后才能晋级。

## 最小门槛

### backtest -> dry-run
- 回测可重复
- 策略逻辑可解释
- 关键风险已知

### dry-run -> tiny live
- 连续运行窗口达标
- 无重复消费
- 无明显状态漂移
- 日志与验证摘要完整
- close-only / halt 已验证

## 禁止

- 跨级晋级。
- 用人工解释替代 gate。
```

- [ ] **Step 2: Update `AGENT.md` stage and skill guidance**

Change these lines in `AGENT.md`:

```md
- backtest -> dry-run -> tiny live
```

And remove `skills/promote-to-testnet/` from the required skill list.

- [ ] **Step 3: Update safety/evidence wording**

Update `rules/trading-safety.md` and `rules/verification-and-evidence.md` so they no longer describe `testnet` as a mandatory promotion step.

Use this wording pattern where appropriate:

```md
- 未完成 dry-run 验证直接推进 tiny live。
```

and:

```md
- dry-run/tiny-live 结论必须给出：
```

- [ ] **Step 4: Update `README.md` stage language**

Adjust README wording so it does not imply `testnet` is part of the active project path. Keep it aligned with the current focus on dry-run / paper execution.

- [ ] **Step 5: Inspect the stage-model diff**

Run:

```bash
git diff -- rules/promotion-gates.md AGENT.md rules/trading-safety.md rules/verification-and-evidence.md README.md
```

Expected: only wording and stage-model changes.

- [ ] **Step 6: Commit the stage-model cleanup**

```bash
git add rules/promotion-gates.md AGENT.md rules/trading-safety.md rules/verification-and-evidence.md README.md
git commit -m "docs: remove testnet from active stage model"
```

### Task 4: Update skill guidance and runbook to match the new path

**Files:**
- Modify: `skills/run-dryrun-validation/SKILL.md`
- Modify: `skills/promote-to-testnet/SKILL.md`
- Modify: `skills/promote-to-live/SKILL.md`
- Modify: `docs/runbook.md`

- [ ] **Step 1: Update `skills/run-dryrun-validation/SKILL.md`**

Change the guidance so it points to the dry-run summary script as part of standard evidence collection before any promotion decision.

- [ ] **Step 2: Deprecate `skills/promote-to-testnet/SKILL.md`**

Replace the current skill body with a short deprecation notice such as:

```md
---
name: promote-to-testnet
description: Deprecated. The repository no longer treats testnet as a formal promotion stage.
---

# promote-to-testnet

This skill is deprecated.

The active stage model is:
- backtest
- dry-run
- tiny live

Use the current dry-run validation guidance and tiny-live promotion guidance instead.
```

- [ ] **Step 3: Update `skills/promote-to-live/SKILL.md`**

Change its prerequisites so it assumes a validated dry-run system rather than a testnet-validated system.

- [ ] **Step 4: Update the runbook validation flow**

In `docs/runbook.md`, add the new summary command under `## Non-Container Dry-Run` or in the validation area using this exact command example:

```bash
source .venv/bin/activate
python3 scripts/summarize_dryrun_validation.py --minutes 60
```

Also add one short note that this summary is part of the evidence used before tiny live is considered.

- [ ] **Step 5: Review the affected docs and skills**

Read the edited files and confirm:

- `testnet` is no longer presented as an active required stage
- the dry-run summary command is visible in the runbook
- the deprecated testnet skill clearly redirects readers

- [ ] **Step 6: Commit the guidance updates**

```bash
git add skills/run-dryrun-validation/SKILL.md skills/promote-to-testnet/SKILL.md skills/promote-to-live/SKILL.md docs/runbook.md
git commit -m "docs: align dryrun guidance with tiny live path"
```

### Task 5: Final verification

**Files:**
- No new files required

- [ ] **Step 1: Run targeted tests for the new summary script**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/test_summarize_dryrun_validation.py -q
```

Expected: PASS.

- [ ] **Step 2: Run the full test suite**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest
```

Expected: PASS.

- [ ] **Step 3: Run the summary script manually**

Run:

```bash
source .venv/bin/activate
python3 scripts/summarize_dryrun_validation.py --minutes 60
```

Expected: a readable summary containing counts and latest timestamps.

- [ ] **Step 4: Inspect worktree status**

Run:

```bash
git status --short
```

Expected: only intended changes remain.

## Self-Review

- Spec coverage: The plan covers both stage-model cleanup and the dry-run summary capability.
- Placeholder scan: Each task includes exact files, commands, or inserted wording patterns.
- Type consistency: The plan consistently uses `scripts/summarize_dryrun_validation.py` as the summary entrypoint and `backtest -> dry-run -> tiny live` as the canonical stage model.
