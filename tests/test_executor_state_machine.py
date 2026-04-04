import pytest

from apps.executor_service.state_machine import (
    ALL_ACTIONS,
    ALL_SIDES,
    TRANSITION_MATRIX,
    decide_transition,
)


@pytest.mark.parametrize(
    "current_side,signal_action,expected_decision,expected_next_state",
    [
        ("flat", "open_long", "execute", "long"),
        ("flat", "open_short", "execute", "short"),
        ("flat", "close_long", "ignored", "flat"),
        ("flat", "close_short", "ignored", "flat"),
        ("flat", "flat", "ignored", "flat"),
        ("long", "open_long", "ignored", "long"),
        ("long", "open_short", "rejected", "long"),
        ("long", "close_long", "execute", "flat"),
        ("long", "close_short", "rejected", "long"),
        ("long", "flat", "execute", "flat"),
        ("short", "open_short", "ignored", "short"),
        ("short", "open_long", "rejected", "short"),
        ("short", "close_short", "execute", "flat"),
        ("short", "close_long", "rejected", "short"),
        ("short", "flat", "execute", "flat"),
    ],
)
def test_decide_transition_matrix(current_side, signal_action, expected_decision, expected_next_state):
    decision, next_state = decide_transition(current_side=current_side, signal_action=signal_action)
    assert decision == expected_decision
    assert next_state == expected_next_state


def test_decide_transition_normalizes_none_side_to_flat():
    decision, next_state = decide_transition(current_side=None, signal_action="open_long")
    assert decision == "execute"
    assert next_state == "long"


def test_decide_transition_normalizes_unknown_side_to_flat():
    decision, next_state = decide_transition(current_side="mystery", signal_action="close_long")
    assert decision == "ignored"
    assert next_state == "flat"


def test_decide_transition_unknown_action_returns_rejected_and_normalized_side():
    decision, next_state = decide_transition(current_side="mystery", signal_action="unknown_action")
    assert decision == "rejected"
    assert next_state == "flat"


def test_transition_matrix_covers_all_side_action_pairs():
    expected_keys = {(side, action) for side in ALL_SIDES for action in ALL_ACTIONS}
    assert set(TRANSITION_MATRIX) == expected_keys
