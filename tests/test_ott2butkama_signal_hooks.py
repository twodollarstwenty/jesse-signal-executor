from pathlib import Path


def test_ott2butkama_contains_signal_actions():
    text = Path("strategies/jesse/Ott2butKAMA/__init__.py").read_text()
    assert "open_long" in text
    assert "open_short" in text
    assert "close_long" in text
    assert "close_short" in text
