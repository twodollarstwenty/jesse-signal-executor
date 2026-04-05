import argparse
import re
import subprocess
from datetime import date
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


MetricMap = dict[str, str]
TAG_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
REQUIRED_METRICS = ("trades", "win_rate", "net_profit", "max_drawdown")
STDERR_EXCERPT_LIMIT = 240
DEFAULT_EXCHANGE = "Binance Perpetual Futures"


def build_stderr_excerpt(stderr: str | None) -> str:
    cleaned = (stderr or "").strip()
    if not cleaned:
        return "N/A"
    if len(cleaned) <= STDERR_EXCERPT_LIMIT:
        return cleaned
    return cleaned[:STDERR_EXCERPT_LIMIT] + "..."


def infer_failure_guidance(*, error: str) -> tuple[str, str]:
    lower = error.lower()
    if "missing metrics" in lower:
        return (
            "backtest output format changed or run ended before summary metrics",
            "inspect raw logs, then verify Jesse completed and summary lines exist",
        )
    if "stderr_excerpt" in lower or "calledprocesserror" in lower or "command failed" in lower:
        return (
            "backtest subprocess failed",
            "review stderr excerpt and raw logs, then fix command/strategy/workspace issues",
        )
    return (
        "unexpected runtime error while running compare",
        "check traceback and raw logs, then rerun compare after fixing root cause",
    )


def parse_iso_datetime(value: str, *, field_name: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        parsed_dt = datetime.fromisoformat(normalized)
    except ValueError:
        try:
            parsed_date = date.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be ISO date or datetime") from exc
        return datetime.combine(parsed_date, datetime.min.time(), tzinfo=timezone.utc)

    if parsed_dt.tzinfo is None:
        return parsed_dt.replace(tzinfo=timezone.utc)
    return parsed_dt.astimezone(timezone.utc)


def validate_tag(tag: str, *, field_name: str) -> None:
    if not tag:
        raise ValueError(f"{field_name} is required")
    if TAG_PATTERN.fullmatch(tag) is None:
        raise ValueError(f"{field_name} contains unsafe characters")


def ensure_comparable(*, symbol: str, timeframe: str, start: str, end: str, initial_balance: float, fee: float, leverage: int, mode: str) -> None:
    if not symbol:
        raise ValueError("symbol is required")
    if not timeframe:
        raise ValueError("timeframe is required")
    start_dt = parse_iso_datetime(start, field_name="start")
    end_dt = parse_iso_datetime(end, field_name="end")
    if start_dt >= end_dt:
        raise ValueError("start must be earlier than end")
    if initial_balance <= 0:
        raise ValueError("initial_balance must be positive")
    if fee < 0:
        raise ValueError("fee must be non-negative")
    if leverage <= 0:
        raise ValueError("leverage must be positive")
    if mode not in {"futures", "spot"}:
        raise ValueError("mode must be futures or spot")


def parse_metrics(raw: str) -> MetricMap:
    patterns = {
        "trades": r"Total Closed Trades:\s*([^\n]+)",
        "win_rate": r"Win Rate:\s*([^\n]+)",
        "net_profit": r"Net Profit:\s*([^\n]+)",
        "max_drawdown": r"Max Drawdown:\s*([^\n]+)",
    }
    result: MetricMap = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, raw)
        result[key] = "N/A" if match is None else match.group(1).strip()
    return result


def ensure_required_metrics(metrics: MetricMap, *, source: str) -> None:
    missing = [key for key in REQUIRED_METRICS if metrics.get(key) in {None, "N/A"}]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"missing metrics for {source}: {joined}")


def build_backtest_command(
    *,
    strategy: str,
    symbol: str,
    timeframe: str,
    start: str,
    end: str,
    initial_balance: float,
    fee: float,
    leverage: int,
    mode: str,
    exchange: str = DEFAULT_EXCHANGE,
) -> list[str]:
    helper_script = Path(__file__).resolve().parent / "run_single_backtest_case.py"
    return [
        "python3",
        str(helper_script),
        "--strategy",
        strategy,
        "--symbol",
        symbol,
        "--timeframe",
        timeframe,
        "--start",
        start,
        "--end",
        end,
        "--fee",
        str(fee),
        "--initial-balance",
        str(initial_balance),
        "--leverage",
        str(leverage),
        "--mode",
        mode,
        "--exchange",
        exchange,
    ]


def default_runner(argv: list[str], cwd: Path) -> str:
    try:
        completed = subprocess.run(argv, cwd=cwd, shell=False, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        stderr_excerpt = build_stderr_excerpt(exc.stderr)
        raise RuntimeError(
            f"command failed with returncode={exc.returncode}; stderr_excerpt={stderr_excerpt}"
        ) from exc
    return completed.stdout + "\n" + completed.stderr


def write_compare_report(
    *,
    output_path: Path,
    symbol: str,
    timeframe: str,
    start: str,
    end: str,
    baseline_label: str,
    candidate_label: str,
    baseline_cmd: list[str],
    candidate_cmd: list[str],
    baseline_metrics: MetricMap,
    candidate_metrics: MetricMap,
    comparability_note: str,
    conclusion: str,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = f"""# Backtest Compare Report

## Summary
- symbol: {symbol}
- timeframe: {timeframe}
- window: {start} -> {end}

## Commands
- baseline: `{' '.join(baseline_cmd)}`
- candidate: `{' '.join(candidate_cmd)}`

## Comparability
{comparability_note}

## Metrics
| metric | {baseline_label} | {candidate_label} |
|---|---:|---:|
| trades | {baseline_metrics['trades']} | {candidate_metrics['trades']} |
| win_rate | {baseline_metrics['win_rate']} | {candidate_metrics['win_rate']} |
| net_profit | {baseline_metrics['net_profit']} | {candidate_metrics['net_profit']} |
| max_drawdown | {baseline_metrics['max_drawdown']} | {candidate_metrics['max_drawdown']} |

## Conclusion
{conclusion}
"""
    output_path.write_text(text)


def write_failure_report(
    *,
    output_path: Path,
    stage: str,
    error: str,
    baseline_log: Path,
    candidate_log: Path,
    stderr_excerpt: str,
    likely_cause: str,
    next_action: str,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "\n".join(
            [
                "# Backtest Compare Failed",
                "",
                f"- stage: {stage}",
                f"- error: {error}",
                f"- baseline_log: {baseline_log}",
                f"- candidate_log: {candidate_log}",
                f"- stderr_excerpt: {stderr_excerpt}",
                f"- likely_cause: {likely_cause}",
                f"- next_action: {next_action}",
            ]
        )
    )


def run_compare(
    *,
    symbol: str,
    timeframe: str,
    start: str,
    end: str,
    baseline_strategy: str,
    candidate_strategy: str,
    baseline_tag: str,
    candidate_tag: str,
    initial_balance: float,
    fee: float,
    leverage: int,
    mode: str,
    exchange: str = DEFAULT_EXCHANGE,
    workspace: Path,
    docs_dir: Path,
    runner: Callable[[list[str], Path], str] = default_runner,
) -> Path:
    ensure_comparable(
        symbol=symbol,
        timeframe=timeframe,
        start=start,
        end=end,
        initial_balance=initial_balance,
        fee=fee,
        leverage=leverage,
        mode=mode,
    )

    validate_tag(baseline_tag, field_name="baseline_tag")
    validate_tag(candidate_tag, field_name="candidate_tag")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    raw_dir = docs_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    baseline_cmd = build_backtest_command(
        strategy=baseline_strategy,
        symbol=symbol,
        timeframe=timeframe,
        start=start,
        end=end,
        initial_balance=initial_balance,
        fee=fee,
        leverage=leverage,
        mode=mode,
        exchange=exchange,
    )
    candidate_cmd = build_backtest_command(
        strategy=candidate_strategy,
        symbol=symbol,
        timeframe=timeframe,
        start=start,
        end=end,
        initial_balance=initial_balance,
        fee=fee,
        leverage=leverage,
        mode=mode,
        exchange=exchange,
    )

    baseline_log = raw_dir / f"{timestamp}-{baseline_tag}.log"
    candidate_log = raw_dir / f"{timestamp}-{candidate_tag}.log"
    failed_report = docs_dir / f"{timestamp}-compare-failed.md"
    report_path = docs_dir / f"{timestamp}-compare.md"

    try:
        baseline_output = runner(baseline_cmd, workspace)
        baseline_log.write_text(baseline_output)

        candidate_output = runner(candidate_cmd, workspace)
        candidate_log.write_text(candidate_output)

        baseline_metrics = parse_metrics(baseline_output)
        candidate_metrics = parse_metrics(candidate_output)
        ensure_required_metrics(baseline_metrics, source=baseline_tag)
        ensure_required_metrics(candidate_metrics, source=candidate_tag)

        write_compare_report(
            output_path=report_path,
            symbol=symbol,
            timeframe=timeframe,
            start=start,
            end=end,
            baseline_label=baseline_tag,
            candidate_label=candidate_tag,
            baseline_cmd=baseline_cmd,
            candidate_cmd=candidate_cmd,
            baseline_metrics=baseline_metrics,
            candidate_metrics=candidate_metrics,
            comparability_note="symbol/timeframe/window/fee/leverage/balance/mode are fixed",
            conclusion="compare using table above",
        )
        return report_path
    except Exception as exc:
        error_text = str(exc)
        stderr_excerpt = "N/A"
        marker = "stderr_excerpt="
        if marker in error_text:
            stderr_excerpt = error_text.split(marker, maxsplit=1)[1].strip()
        likely_cause, next_action = infer_failure_guidance(error=error_text)
        write_failure_report(
            output_path=failed_report,
            stage="run_compare",
            error=error_text,
            baseline_log=baseline_log,
            candidate_log=candidate_log,
            stderr_excerpt=stderr_excerpt,
            likely_cause=likely_cause,
            next_action=next_action,
        )
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run baseline vs candidate backtest compare")
    parser.add_argument("--symbol", default="ETHUSDT")
    parser.add_argument("--timeframe", default="5m")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--baseline-strategy", required=True)
    parser.add_argument("--candidate-strategy", required=True)
    parser.add_argument("--baseline-tag", default="baseline")
    parser.add_argument("--candidate-tag", default="candidate")
    parser.add_argument("--initial-balance", type=float, default=10000)
    parser.add_argument("--fee", type=float, default=0.0004)
    parser.add_argument("--leverage", type=int, default=10)
    parser.add_argument("--mode", default="futures")
    parser.add_argument("--exchange", default=DEFAULT_EXCHANGE)
    parser.add_argument("--workspace", default="runtime/jesse_workspace")
    parser.add_argument("--docs-dir", default="docs/backtests")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = run_compare(
        symbol=args.symbol,
        timeframe=args.timeframe,
        start=args.start,
        end=args.end,
        baseline_strategy=args.baseline_strategy,
        candidate_strategy=args.candidate_strategy,
        baseline_tag=args.baseline_tag,
        candidate_tag=args.candidate_tag,
        initial_balance=args.initial_balance,
        fee=args.fee,
        leverage=args.leverage,
        mode=args.mode,
        exchange=args.exchange,
        workspace=Path(args.workspace),
        docs_dir=Path(args.docs_dir),
    )
    print(f"compare_report={report}")


if __name__ == "__main__":
    main()
