# Shared Core Dependency Consolidation Design

## Background

The project has started moving toward a shared `Ott2butKAMA` strategy core, but the current dependency structure is still fragile. In particular, the shared feature builder imports `custom_indicators_ottkama` from a runtime-visible module location rather than from a stable shared package boundary.

This causes exactly the kind of drift and import instability the user wants to avoid:

- backtest can work while dry-run fails
- runtime workspace layout leaks into shared-core design
- new entrypoints can break due to import-order assumptions

## Goal

Consolidate shared strategy-core dependencies into a stable package structure so the shared core no longer depends on ad hoc runtime import paths.

## Core Principle

The shared strategy core must form a self-contained dependency boundary.

That means:

- shared core modules should depend on shared package modules
- not on runtime-workspace-local directories that happen to be importable only in some execution modes

## Proposed Package Shape

Introduce or consolidate shared dependencies under:

- `strategies/shared/`

Recommended structure:

- `strategies/shared/ott2butkama_core.py`
- `strategies/shared/ott2butkama_features.py`
- `strategies/shared/custom_indicators_ottkama/`

This allows shared strategy logic to depend only on modules inside the same shared package boundary.

## What Changes

### Shared Feature Builder

`ott2butkama_features.py` should stop importing:

- `custom_indicators_ottkama`

from a runtime-external loose namespace.

Instead it should import the shared indicator package through a stable path inside `strategies/shared`.

### Sync / Runtime Layout

The runtime sync path should ensure the shared package subtree is copied into the runtime workspace together with strategy packages.

### Strategy Wrapper

The Jesse strategy wrapper should continue to use the shared package, but after consolidation it should do so through stable imports that work consistently in:

- backtest
- dry-run
- runtime workspace

## Why This Matters

Without this consolidation, every new integration step risks breaking because import success depends on execution context instead of architecture.

The user explicitly asked to avoid temporary fixes. This is the structural answer.

## Acceptance Criteria

This work is complete when:

1. shared strategy-core modules depend only on stable shared-package imports
2. runtime workspace sync includes the shared package dependencies needed by the shared core
3. both backtest and dry-run can import the shared core without special-case import hacks
4. the project is less dependent on runtime path accidents

## Risks and Mitigations

### Risk: moving shared indicator code changes import paths across multiple files

Mitigation:

- move the package structure first
- update imports second
- verify both backtest and dry-run after the move

### Risk: the shared package grows into a second strategy tree

Mitigation:

- keep `strategies/shared` focused on reusable logic only, not strategy wrappers

## Follow-Up

Once the dependency boundary is stable, the project can continue the bigger strategy-consistency goal with much lower integration risk.
