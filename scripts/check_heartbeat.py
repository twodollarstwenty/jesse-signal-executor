import argparse
from datetime import datetime, timezone
from pathlib import Path


def _parse_timestamp(text: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


def is_healthy(path: Path, max_age_seconds: int) -> bool:
    try:
        if not path.exists():
            return False

        text = path.read_text().strip()
    except OSError:
        return False

    if not text:
        return False

    updated_at = _parse_timestamp(text)
    if updated_at is None:
        return False

    age = (datetime.now(timezone.utc) - updated_at).total_seconds()
    return age <= max_age_seconds


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True)
    parser.add_argument("--max-age-seconds", type=int, default=60)
    args = parser.parse_args()

    raise SystemExit(0 if is_healthy(Path(args.path), args.max_age_seconds) else 1)


if __name__ == "__main__":
    main()
