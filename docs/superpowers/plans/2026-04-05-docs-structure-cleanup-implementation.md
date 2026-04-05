# Docs Structure Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize the runbook and clarify the status of superseded non-container dry-run planning docs without changing repository behavior.

**Architecture:** Keep this cleanup doc-only. Reorder `docs/runbook.md` into a clearer operational flow, add a short superseded note to the earlier non-container dry-run implementation plan, and leave the final plan as the clearly current reference. Verification is limited to reading the resulting markdown and checking the worktree diff.

**Tech Stack:** Markdown, git

---

## File Structure

- Modify: `docs/runbook.md`
  - Reorder sections into a clearer operator-facing sequence without changing meaning.
- Modify: `docs/superpowers/plans/2026-04-04-non-container-dryrun-daemon-implementation.md`
  - Add a short note marking it as superseded by the final plan.
- Keep: `docs/superpowers/plans/2026-04-05-final-jesse-dryrun-daemon-implementation.md`
  - No content change required unless a short wording tweak is needed for clarity.

### Task 1: Reorganize the runbook into an operator-friendly order

**Files:**
- Modify: `docs/runbook.md`

- [ ] **Step 1: Rewrite the runbook section order**

Update `docs/runbook.md` so the top-to-bottom order becomes:

```md
# Runbook

默认命令上下文：除非特别说明，以下命令都在仓库根目录执行。

虚拟环境约定：

- 项目级脚本、pytest、数据库初始化等，使用项目虚拟环境：`.venv`。
- Jesse runtime bootstrap 完成后，涉及 `jesse` CLI 或 runtime workspace 依赖的命令，使用 `runtime/jesse_workspace/.venv`。

## 初始化
...

## 启动
...

## 停止
...

## 状态
...

## Non-Container Dry-Run
...

## Jesse Runtime Bootstrap
...

## Ott2butKAMA 真实信号桥
...

## Pytest Bridge 回归验收
...

## 最小 DB 闭环
...

## 切换只平不开
...

## Backtest Compare
...
```

Keep all existing command content and explanations unless moving them improves the order.

- [ ] **Step 2: Verify the runbook edit visually**

Read the file and confirm:

- the non-container dry-run section is still intact
- the bootstrap/bridge sections sit below dry-run operations
- the file still reads naturally from setup to validation

- [ ] **Step 3: Commit the runbook cleanup**

```bash
git add docs/runbook.md
git commit -m "docs: reorganize runbook structure"
```

### Task 2: Mark the older non-container plan as superseded

**Files:**
- Modify: `docs/superpowers/plans/2026-04-04-non-container-dryrun-daemon-implementation.md`

- [ ] **Step 1: Add a superseded note at the top of the older plan**

Insert this note immediately below the title line:

```md
> Superseded by `docs/superpowers/plans/2026-04-05-final-jesse-dryrun-daemon-implementation.md`. Keep this file as historical implementation context only.
```

- [ ] **Step 2: Verify the note reads clearly in context**

Read the first 20 lines of the older plan and confirm:

- the superseded status is visible immediately
- the newer plan path is exact
- the older document still remains readable as history

- [ ] **Step 3: Commit the superseded-note update**

```bash
git add docs/superpowers/plans/2026-04-04-non-container-dryrun-daemon-implementation.md
git commit -m "docs: mark older dryrun plan as superseded"
```

### Task 3: Final verification and worktree inspection

**Files:**
- No new files required

- [ ] **Step 1: Read the edited documentation files**

Read:

```text
docs/runbook.md
docs/superpowers/plans/2026-04-04-non-container-dryrun-daemon-implementation.md
docs/superpowers/plans/2026-04-05-final-jesse-dryrun-daemon-implementation.md
```

Confirm the active/non-active relationship is obvious and the runbook structure is cleaner.

- [ ] **Step 2: Inspect git diff**

Run:

```bash
git diff -- docs/runbook.md docs/superpowers/plans/2026-04-04-non-container-dryrun-daemon-implementation.md docs/superpowers/plans/2026-04-05-final-jesse-dryrun-daemon-implementation.md
```

Expected: only markdown/documentation changes.

- [ ] **Step 3: Inspect worktree status**

Run:

```bash
git status --short
```

Expected: only the intended documentation files appear.

## Self-Review

- Spec coverage: The plan covers runbook reorganization and explicit superseded-plan labeling without touching code.
- Placeholder scan: All tasks specify exact files, exact inserted text, and concrete verification steps.
- Type consistency: File paths and document roles remain consistent across all tasks.
