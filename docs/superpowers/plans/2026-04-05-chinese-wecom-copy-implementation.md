# Chinese WeCom Notification Copy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Translate WeCom notification labels to Chinese without changing scripts, reports, or database semantics.

**Architecture:** Touch only the two formatting paths that generate WeCom messages and the related tests that assert those message strings.

**Tech Stack:** Python 3.13, pytest

---

## File Structure

- Modify: `apps/notifications/wecom.py`
- Modify: `scripts/notify_dryrun_events.py`
- Modify: `tests/test_wecom_notifications.py`
- Modify: `tests/test_notify_dryrun_events.py`

### Task 1: Update message copy and tests

**Files:**
- Modify: `apps/notifications/wecom.py`
- Modify: `scripts/notify_dryrun_events.py`
- Modify: `tests/test_wecom_notifications.py`
- Modify: `tests/test_notify_dryrun_events.py`

- [ ] **Step 1: Update backtest message labels to Chinese**

Change the labels in `format_backtest_summary_message()` to:

- `[回测结果]`
- `基线策略:`
- `候选策略:`
- `交易对:`
- `周期:`
- `区间:`
- `交易次数:`
- `胜率:`
- `净收益:`
- `最大回撤:`

- [ ] **Step 2: Update dry-run message labels to Chinese**

Change the labels in `format_execution_event_message()` to:

- `[Dry-Run]`
- `策略:`
- `交易对:`
- `动作:`
- `处理结果:`
- `信号时间:`
- `执行时间:`
- `价格:`
- `仓位方向:`
- `原因:`

- [ ] **Step 3: Update tests**

Adjust the WeCom-related tests so they assert the new Chinese labels but keep action/decision values unchanged.

- [ ] **Step 4: Run full tests**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest
```

Expected: PASS.
