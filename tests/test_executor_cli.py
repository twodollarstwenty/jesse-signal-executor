from apps.executor_service.cli import main


def test_executor_cli_exposes_main():
    assert callable(main)
