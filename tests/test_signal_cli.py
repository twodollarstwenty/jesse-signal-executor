from unittest.mock import patch

from apps.signal_service.cli import build_parser


def test_signal_cli_parser_accepts_required_args():
    parser = build_parser()
    args = parser.parse_args(
        [
            "--instance-id",
            "ott_eth_5m",
            "--strategy",
            "Ott2butKAMA",
            "--symbol",
            "ETHUSDT",
            "--timeframe",
            "5m",
            "--signal-time",
            "2026-04-04T00:00:00Z",
            "--action",
            "open_long",
        ]
    )
    assert args.instance_id == "ott_eth_5m"
    assert args.strategy == "Ott2butKAMA"
    assert args.action == "open_long"


@patch("apps.signal_service.cli.insert_signal")
def test_signal_cli_main_forwards_instance_id(mock_insert, monkeypatch):
    from apps.signal_service.cli import main

    monkeypatch.setattr(
        "sys.argv",
        [
            "signal-cli",
            "--instance-id",
            "ott_eth_5m",
            "--strategy",
            "Ott2butKAMA",
            "--symbol",
            "ETHUSDT",
            "--timeframe",
            "5m",
            "--signal-time",
            "2026-04-04T00:00:00Z",
            "--action",
            "open_long",
        ],
    )

    main()

    mock_insert.assert_called_once_with(
        instance_id="ott_eth_5m",
        strategy="Ott2butKAMA",
        symbol="ETHUSDT",
        timeframe="5m",
        signal_time="2026-04-04T00:00:00Z",
        action="open_long",
        payload={"source": "cli"},
    )
