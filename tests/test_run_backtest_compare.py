from pathlib import Path
import subprocess

import pytest


def test_ensure_comparable_same_window_and_market_passes():
    from scripts.run_backtest_compare import ensure_comparable

    ensure_comparable(
        symbol="ETHUSDT",
        timeframe="5m",
        start="2024-01-01",
        end="2024-02-01",
        initial_balance=10000,
        fee=0.0004,
        leverage=2,
        mode="futures",
    )


def test_ensure_comparable_rejects_invalid_time_window():
    from scripts.run_backtest_compare import ensure_comparable

    with pytest.raises(ValueError, match="start must be earlier than end"):
        ensure_comparable(
            symbol="ETHUSDT",
            timeframe="5m",
            start="2024-02-01",
            end="2024-01-01",
            initial_balance=10000,
            fee=0.0004,
            leverage=2,
            mode="futures",
        )


def test_ensure_comparable_rejects_non_iso_start():
    from scripts.run_backtest_compare import ensure_comparable

    with pytest.raises(ValueError, match="start must be ISO date or datetime"):
        ensure_comparable(
            symbol="ETHUSDT",
            timeframe="5m",
            start="01-01-2024",
            end="2024-02-01",
            initial_balance=10000,
            fee=0.0004,
            leverage=2,
            mode="futures",
        )


def test_ensure_comparable_accepts_iso_datetimes():
    from scripts.run_backtest_compare import ensure_comparable

    ensure_comparable(
        symbol="ETHUSDT",
        timeframe="5m",
        start="2024-01-01T00:00:00+00:00",
        end="2024-02-01T00:00:00+00:00",
        initial_balance=10000,
        fee=0.0004,
        leverage=2,
        mode="futures",
    )


def test_parse_metrics_extracts_required_fields():
    from scripts.run_backtest_compare import parse_metrics

    raw = """
    Total Closed Trades: 120
    Win Rate: 52.5%
    Net Profit: 13.40%
    Max Drawdown: 6.20%
    """

    metrics = parse_metrics(raw)
    assert metrics["trades"] == "120"
    assert metrics["win_rate"] == "52.5%"
    assert metrics["net_profit"] == "13.40%"
    assert metrics["max_drawdown"] == "6.20%"


def test_build_backtest_command_uses_python_helper_script():
    from scripts.run_backtest_compare import build_backtest_command

    cmd = build_backtest_command(
        strategy="Ott2butKAMA",
        symbol="ETHUSDT",
        timeframe="5m",
        start="2026-04-01",
        end="2026-04-04",
        initial_balance=10000,
        fee=0.0004,
        leverage=2,
        mode="futures",
    )

    assert cmd[0] == "python3"
    assert cmd[1].endswith("scripts/run_single_backtest_case.py")
    assert "--strategy" in cmd
    assert "Ott2butKAMA" in cmd
    assert "--symbol" in cmd
    assert "ETHUSDT" in cmd


def test_write_compare_report_creates_markdown(tmp_path: Path):
    from scripts.run_backtest_compare import write_compare_report

    output = tmp_path / "report.md"

    write_compare_report(
        output_path=output,
        symbol="ETHUSDT",
        timeframe="5m",
        start="2024-01-01",
        end="2024-02-01",
        baseline_label="baseline",
        candidate_label="candidate",
        baseline_cmd=["cmd", "baseline"],
        candidate_cmd=["cmd", "candidate"],
        baseline_metrics={"trades": "100", "win_rate": "50%", "net_profit": "10%", "max_drawdown": "5%"},
        candidate_metrics={"trades": "110", "win_rate": "52%", "net_profit": "12%", "max_drawdown": "4.8%"},
        comparability_note="all fixed",
        conclusion="candidate better",
    )

    text = output.read_text()
    assert "## Summary" in text
    assert "## Commands" in text
    assert "## Comparability" in text
    assert "## Metrics" in text
    assert "## Conclusion" in text
    assert "| trades | 100 | 110 |" in text
    assert "candidate better" in text


def test_run_compare_writes_failure_report_when_runner_fails(tmp_path: Path):
    from scripts.run_backtest_compare import run_compare

    def fake_runner(_argv: list[str], _cwd: Path):
        raise RuntimeError("runner failed")

    with pytest.raises(RuntimeError, match="runner failed"):
        run_compare(
            symbol="ETHUSDT",
            timeframe="5m",
            start="2024-01-01",
            end="2024-02-01",
            baseline_strategy="Ott2butKAMA",
            candidate_strategy="Ott2butKAMA",
            baseline_tag="baseline",
            candidate_tag="candidate",
            initial_balance=10000,
            fee=0.0004,
            leverage=2,
            mode="futures",
            workspace=tmp_path,
            docs_dir=tmp_path / "docs_backtests",
            runner=fake_runner,
        )

    failure_reports = list((tmp_path / "docs_backtests").glob("*-compare-failed.md"))
    assert len(failure_reports) == 1
    report_text = failure_reports[0].read_text()
    assert "runner failed" in report_text
    assert "- stage: run_compare" in report_text
    assert "- baseline_log:" in report_text
    assert "- candidate_log:" in report_text
    assert "- stderr_excerpt:" in report_text
    assert "- likely_cause:" in report_text
    assert "- next_action:" in report_text


def test_run_compare_uses_same_exchange_for_baseline_and_candidate(tmp_path: Path):
    from scripts.run_backtest_compare import run_compare

    seen_argvs: list[list[str]] = []

    def fake_runner(argv: list[str], _cwd: Path):
        seen_argvs.append(argv)
        return "\n".join(
            [
                "Total Closed Trades: 1",
                "Win Rate: 50.0%",
                "Net Profit: 1.00%",
                "Max Drawdown: 0.50%",
            ]
        )

    run_compare(
        symbol="ETHUSDT",
        timeframe="5m",
        start="2024-01-01",
        end="2024-02-01",
        baseline_strategy="Ott2butKAMA",
        candidate_strategy="Ott2butKAMA",
        baseline_tag="baseline",
        candidate_tag="candidate",
        initial_balance=10000,
        fee=0.0004,
        leverage=2,
        mode="futures",
        exchange="Bybit USDT Perpetual",
        workspace=tmp_path,
        docs_dir=tmp_path / "docs_backtests",
        runner=fake_runner,
    )

    assert len(seen_argvs) == 2
    baseline_argv = seen_argvs[0]
    candidate_argv = seen_argvs[1]
    assert "--exchange" in baseline_argv
    assert "--exchange" in candidate_argv
    assert baseline_argv[baseline_argv.index("--exchange") + 1] == "Bybit USDT Perpetual"
    assert candidate_argv[candidate_argv.index("--exchange") + 1] == "Bybit USDT Perpetual"


def test_run_compare_sends_non_fatal_backtest_summary_notification(monkeypatch, tmp_path: Path):
    from scripts.run_backtest_compare import run_compare

    seen: dict[str, object] = {}

    def fake_runner(_argv: list[str], _cwd: Path):
        return "\n".join(
            [
                "Total Closed Trades: 7",
                "Win Rate: 57.0%",
                "Net Profit: 9.10%",
                "Max Drawdown: 3.40%",
            ]
        )

    def fake_format(**kwargs):
        seen["format_kwargs"] = kwargs
        return "formatted summary"

    def fake_send(message: str):
        seen["message"] = message
        raise RuntimeError("wecom unavailable")

    monkeypatch.setattr("scripts.run_backtest_compare.format_backtest_summary_message", fake_format)
    monkeypatch.setattr("scripts.run_backtest_compare.send_text_message", fake_send)

    report = run_compare(
        symbol="ETHUSDT",
        timeframe="5m",
        start="2024-01-01",
        end="2024-02-01",
        baseline_strategy="Ott2butKAMA",
        candidate_strategy="Ott2butKAMA_RiskManaged25",
        baseline_tag="baseline",
        candidate_tag="candidate",
        initial_balance=10000,
        fee=0.0004,
        leverage=2,
        mode="futures",
        workspace=tmp_path,
        docs_dir=tmp_path / "docs_backtests",
        runner=fake_runner,
    )

    assert report.exists()
    assert seen["message"] == "formatted summary"
    assert seen["format_kwargs"] == {
        "baseline": "baseline",
        "candidate": "candidate",
        "symbol": "ETHUSDT",
        "timeframe": "5m",
        "window": "2024-01-01 -> 2024-02-01",
        "trades": "7",
        "win_rate": "57.0%",
        "net_profit": "9.10%",
        "max_drawdown": "3.40%",
    }


def test_run_compare_rejects_unsafe_tag(tmp_path: Path):
    from scripts.run_backtest_compare import run_compare

    with pytest.raises(ValueError, match="baseline_tag contains unsafe characters"):
        run_compare(
            symbol="ETHUSDT",
            timeframe="5m",
            start="2024-01-01",
            end="2024-02-01",
            baseline_strategy="Ott2butKAMA",
            candidate_strategy="Ott2butKAMA",
            baseline_tag="baseline;rm -rf /",
            candidate_tag="candidate",
            initial_balance=10000,
            fee=0.0004,
            leverage=2,
            mode="futures",
            workspace=tmp_path,
            docs_dir=tmp_path / "docs_backtests",
        )


def test_default_runner_uses_argv_and_workspace(monkeypatch, tmp_path: Path):
    from scripts.run_backtest_compare import default_runner

    seen: dict[str, object] = {}

    class Completed:
        stdout = "ok"
        stderr = ""

    def fake_run(argv, *, cwd, shell, check, capture_output, text):
        seen["argv"] = argv
        seen["cwd"] = cwd
        seen["shell"] = shell
        seen["check"] = check
        seen["capture_output"] = capture_output
        seen["text"] = text
        return Completed()

    monkeypatch.setattr("scripts.run_backtest_compare.subprocess.run", fake_run)

    output = default_runner(["jesse", "run", "--symbol", "ETHUSDT"], tmp_path)
    assert output == "ok\n"
    assert seen["argv"] == ["jesse", "run", "--symbol", "ETHUSDT"]
    assert seen["cwd"] == tmp_path
    assert seen["shell"] is False
    assert seen["check"] is True
    assert seen["capture_output"] is True
    assert seen["text"] is True


def test_default_runner_includes_stderr_excerpt_when_command_fails(monkeypatch, tmp_path: Path):
    from scripts.run_backtest_compare import default_runner

    def fake_run(argv, *, cwd, shell, check, capture_output, text):
        raise subprocess.CalledProcessError(
            returncode=2,
            cmd=argv,
            output="some stdout",
            stderr="fatal jesse error: invalid strategy",
        )

    monkeypatch.setattr("scripts.run_backtest_compare.subprocess.run", fake_run)

    with pytest.raises(RuntimeError, match="stderr_excerpt=fatal jesse error: invalid strategy"):
        default_runner(["jesse", "run"], tmp_path)


def test_run_compare_fails_when_metrics_missing(tmp_path: Path):
    from scripts.run_backtest_compare import run_compare

    def fake_runner(_argv: list[str], _cwd: Path):
        return "Total Closed Trades: 120\nWin Rate: 52.5%\n"

    with pytest.raises(ValueError, match="missing metrics"):
        run_compare(
            symbol="ETHUSDT",
            timeframe="5m",
            start="2024-01-01",
            end="2024-02-01",
            baseline_strategy="Ott2butKAMA",
            candidate_strategy="Ott2butKAMA",
            baseline_tag="baseline",
            candidate_tag="candidate",
            initial_balance=10000,
            fee=0.0004,
            leverage=2,
            mode="futures",
            workspace=tmp_path,
            docs_dir=tmp_path / "docs_backtests",
            runner=fake_runner,
        )


def test_parse_args_defaults_leverage_to_10(monkeypatch):
    from scripts.run_backtest_compare import parse_args

    monkeypatch.setattr(
        "sys.argv",
        [
            "run_backtest_compare.py",
            "--symbol",
            "ETHUSDT",
            "--timeframe",
            "5m",
            "--start",
            "2026-03-05",
            "--end",
            "2026-04-05",
            "--baseline-strategy",
            "Ott2butKAMA",
            "--candidate-strategy",
            "Ott2butKAMA_RiskManaged25",
        ],
    )

    args = parse_args()

    assert args.leverage == 10
