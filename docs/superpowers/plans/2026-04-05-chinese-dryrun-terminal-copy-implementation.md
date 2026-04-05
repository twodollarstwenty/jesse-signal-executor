# Chinese Dry-Run Terminal Copy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Localize dry-run terminal summary labels to Chinese and print summary timestamps in `+08:00`.

**Architecture:** Touch only the summary rendering helpers in `scripts/run_jesse_live_loop.py` and update the tests that assert those strings.

**Tech Stack:** Python 3.13, pytest

---

## File Structure

- Modify: `scripts/run_jesse_live_loop.py`
- Modify: `tests/test_run_jesse_live_loop.py`

### Task 1: Update terminal summary copy and tests

**Files:**
- Modify: `scripts/run_jesse_live_loop.py`
- Modify: `tests/test_run_jesse_live_loop.py`

- [ ] **Step 1: Change flat summary labels to Chinese**
- [ ] **Step 2: Change position summary labels to Chinese**
- [ ] **Step 3: Format timestamps in `+08:00` for terminal display**
- [ ] **Step 4: Keep action values unchanged**
- [ ] **Step 5: Update tests and run full suite**

Run:

```bash
PYTHONPATH=. ./.venv/bin/pytest
```

Expected: PASS.
