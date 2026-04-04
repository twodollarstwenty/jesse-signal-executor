from typing import Final, Literal, TypeGuard


Side = Literal["flat", "long", "short"]
Action = Literal["open_long", "open_short", "close_long", "close_short", "flat"]
Decision = Literal["execute", "ignored", "rejected"]

Transition = tuple[Decision, Side]

ALL_SIDES: Final[tuple[Side, ...]] = ("flat", "long", "short")
ALL_ACTIONS: Final[tuple[Action, ...]] = (
    "open_long",
    "open_short",
    "close_long",
    "close_short",
    "flat",
)


TRANSITION_MATRIX: dict[tuple[Side, Action], Transition] = {
    ("flat", "open_long"): ("execute", "long"),
    ("flat", "open_short"): ("execute", "short"),
    ("flat", "close_long"): ("ignored", "flat"),
    ("flat", "close_short"): ("ignored", "flat"),
    ("flat", "flat"): ("ignored", "flat"),
    ("long", "open_long"): ("ignored", "long"),
    ("long", "open_short"): ("rejected", "long"),
    ("long", "close_long"): ("execute", "flat"),
    ("long", "close_short"): ("rejected", "long"),
    ("long", "flat"): ("execute", "flat"),
    ("short", "open_short"): ("ignored", "short"),
    ("short", "open_long"): ("rejected", "short"),
    ("short", "close_short"): ("execute", "flat"),
    ("short", "close_long"): ("rejected", "short"),
    ("short", "flat"): ("execute", "flat"),
}


def _is_side(value: str | None) -> TypeGuard[Side]:
    return value in ALL_SIDES


def _is_action(value: str) -> TypeGuard[Action]:
    return value in ALL_ACTIONS


def _decide_transition_typed(*, current_side: Side, signal_action: Action) -> Transition:
    return TRANSITION_MATRIX[(current_side, signal_action)]


def normalize_side(current_side: str | None) -> Side:
    if _is_side(current_side):
        return current_side
    return "flat"


def decide_transition(*, current_side: str | None, signal_action: str) -> Transition:
    side = normalize_side(current_side)
    if not _is_action(signal_action):
        return "rejected", side
    return _decide_transition_typed(current_side=side, signal_action=signal_action)
