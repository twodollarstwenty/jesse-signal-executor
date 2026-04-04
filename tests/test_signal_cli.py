from apps.signal_service.cli import build_parser


def test_signal_cli_parser_accepts_required_args():
    parser = build_parser()
    args = parser.parse_args(
        [
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
    assert args.strategy == "Ott2butKAMA"
    assert args.action == "open_long"
