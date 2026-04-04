from apps.executor_service.rules import decide_action


def test_same_side_signal_is_ignored():
    assert decide_action("open_long", "long") == "ignored"


def test_reverse_side_signal_is_rejected():
    assert decide_action("open_long", "short") == "rejected"
