# Docs Structure Cleanup Design

## Background

The repository now has a working non-container dry-run workflow and its final implementation has already been committed. The code path is stable, but the documentation layout still reflects the intermediate development process:

- `docs/runbook.md` contains accurate information, but the sections mix baseline service commands, dry-run operations, Jesse bootstrap details, and validation steps in a way that is harder to scan than necessary.
- `docs/superpowers/plans/` contains both an earlier non-container implementation plan and a later final implementation plan. Both are valuable historical artifacts, but the relationship between them is not obvious to a future reader.

The goal of this cleanup is documentation clarity, not feature work.

## Goal

Improve the repository's documentation structure so that:

1. the runbook reads as a clean operational entrypoint
2. the current non-container dry-run path is easy to locate and follow
3. historical planning documents remain available without being mistaken for the current plan

## Scope

### In Scope

- Reorganize `docs/runbook.md` for readability and operational flow.
- Clarify the relationship between superseded and current non-container dry-run plans.
- Keep the existing spec and plan files unless a lighter mechanism can make their status obvious.

### Out of Scope

- Any production code change.
- Any script or test behavior change.
- Rewriting past design history.
- Deleting useful historical records unless the replacement is clearly better and preserves traceability.

## Proposed Approach

### Runbook Structure

`docs/runbook.md` should be reorganized into a more intentional order:

1. environment and command context
2. baseline project lifecycle commands
3. non-container dry-run operations
4. Jesse runtime bootstrap and bridge validation
5. backtest compare workflow

This preserves the same content, but makes the document easier to use as an operator guide.

### Superpowers Plan Relationship

The repository should keep both of these files:

- `docs/superpowers/plans/2026-04-04-non-container-dryrun-daemon-implementation.md`
- `docs/superpowers/plans/2026-04-05-final-jesse-dryrun-daemon-implementation.md`

But the older plan should be explicitly marked as superseded by the later final plan. That can be done with a short note at the top of the older plan, rather than deleting or moving it.

Reasoning:

- keeping both files preserves the development trail
- a clear note prevents the older plan from being mistaken for the active one
- this is lower risk than introducing a new archive structure just for one document pair

## File-Level Design

### `docs/runbook.md`

Responsibilities after cleanup:

- act as the main human-facing operational guide
- present commands in a practical order
- make non-container dry-run the clearly documented active path

### `docs/superpowers/plans/2026-04-04-non-container-dryrun-daemon-implementation.md`

Responsibilities after cleanup:

- remain as historical implementation context
- contain a brief note that it was superseded by the final plan dated `2026-04-05`

### `docs/superpowers/plans/2026-04-05-final-jesse-dryrun-daemon-implementation.md`

Responsibilities after cleanup:

- remain the clearly current final implementation plan for the non-container dry-run workflow

## Acceptance Criteria

This cleanup is complete when:

1. `docs/runbook.md` is easier to scan and grouped by operational purpose
2. the current non-container dry-run path is clearly presented as the active operational workflow
3. the older non-container plan is visibly marked as superseded
4. no code behavior or tests need to change as part of the cleanup

## Risks and Mitigations

### Risk: over-cleaning removes useful history

Mitigation:

- prefer notes and structure over deletion
- keep historical plans in place unless they are clearly harmful

### Risk: documentation cleanup drifts into functional editing

Mitigation:

- restrict changes to markdown organization and status notes only

## Follow-Up

If the repository accumulates more superseded specs/plans later, a future pass may introduce a dedicated archive convention. That is unnecessary for this cleanup.
