from pathlib import Path


def test_embedded_jesse_layout_exists():
    assert Path("runtime/jesse_workspace").exists()
    assert Path("strategies/jesse").exists()
    assert Path("apps/signal_service/jesse_bridge").exists()
