# Dry-Run Log Latest Execution Result Design

## Goal

Add the latest execution result to the existing one-line `jesse-dryrun` log output so the operator can distinguish between:

- strategy intent
- signal emission
- actual executor outcome

## Scope

### In Scope

- Query the latest relevant execution status for the symbol.
- Append a field like `最近执行结果=...` to the one-line dry-run log.

### Out of Scope

- Notification changes.
- Schema changes.
- Full event correlation UI.

## Proposed Output Shape

Current one-line log already shows:

- current action
- emitted flag

The enhanced version should also show:

- `最近执行结果=execute|ignored|rejected|none`

Example:

```text
[2026-04-07T07:10:00+08:00] 策略=Ott2butKAMA 交易对=ETHUSDT 持仓方向=多 ... 动作=close_long 已发送=是 最近执行结果=execute
```

## Acceptance Criteria

1. one-line dry-run output includes a latest execution result field
2. the field is safe when no execution exists yet
3. the rest of the log format remains unchanged
