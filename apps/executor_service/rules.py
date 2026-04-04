def decide_action(signal_action: str, current_side: str | None) -> str:
    if signal_action == "open_long":
        if current_side == "long":
            return "ignored"
        if current_side == "short":
            return "rejected"
        return "execute"

    if signal_action == "open_short":
        if current_side == "short":
            return "ignored"
        if current_side == "long":
            return "rejected"
        return "execute"

    if signal_action in {"close_long", "close_short", "flat"}:
        return "execute"

    return "rejected"
