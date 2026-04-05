# Chinese WeCom Notification Copy Design

## Goal

Change Enterprise WeCom notification copy to Chinese while keeping the underlying data fields, scripts, reports, and database semantics unchanged.

## Scope

### In Scope

- Dry-run WeCom notification labels.
- Backtest summary WeCom notification labels.

### Out of Scope

- CLI output.
- Database field names.
- Compare reports.
- Dry-run summary script output.

## Approach

Keep values such as `execute`, `ignored`, `rejected`, `open_long`, `close_long`, `long`, and `short` unchanged for debugging consistency, but translate the surrounding labels to Chinese.

## Acceptance Criteria

1. Dry-run WeCom notifications use Chinese labels.
2. Backtest summary WeCom notifications use Chinese labels.
3. Tests are updated to assert the new Chinese copy.
