import argparse

from apps.signal_service.writer import insert_signal


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--timeframe", required=True)
    parser.add_argument("--signal-time", required=True)
    parser.add_argument("--action", required=True)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    insert_signal(
        strategy=args.strategy,
        symbol=args.symbol,
        timeframe=args.timeframe,
        signal_time=args.signal_time,
        action=args.action,
        payload={"source": "cli"},
    )


if __name__ == "__main__":
    main()
