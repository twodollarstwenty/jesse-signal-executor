# Chinese Dry-Run Terminal Copy Design

## Goal

Make dry-run terminal one-line summaries easier to read by switching field labels to Chinese and formatting timestamps in China Standard Time (`+08:00`).

## Scope

### In Scope

- Flat summary line labels.
- Position summary line labels.
- Timestamp formatting for terminal summary output.

### Out of Scope

- Database field names.
- Notification message copy.
- Internal action enum values.

## Approach

Translate only the surrounding display labels to Chinese while keeping action values such as `open_long`, `close_short`, `execute`, `ignored`, and `rejected` unchanged.

Terminal timestamps should be printed in `+08:00` rather than UTC.

## Acceptance Criteria

1. Flat summary output uses Chinese labels.
2. Position summary output uses Chinese labels.
3. Summary timestamps are rendered in `+08:00`.
