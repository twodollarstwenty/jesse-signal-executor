# Backtest Compare Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立 baseline vs candidate 的可复现回测对照框架，并输出可审计的日志与对照报告。

**Architecture:** 通过 `scripts/run_backtest_compare.py` 统一执行两次回测，先做参数一致性校验，再分别调用回测命令，保存原始日志并解析核心指标，最后输出 Markdown 对照报告。Jesse runtime 的 `config.py`/`routes.py` 同步补齐最小回测配置，保证 `ETHUSDT 5m` 基线可运行。

**Tech Stack:** Python 3.11+, pytest, subprocess, pathlib, regex, Jesse runtime workspace

---

## File Structure

- Create: `scripts/run_backtest_compare.py`
  - 责任：参数解析、可比性校验、执行 baseline/candidate 回测、解析指标、写日志与报告。
- Create: `tests/test_run_backtest_compare.py`
  - 责任：覆盖参数校验、可比性检查、输出文件生成、指标解析、失败摘要行为。
- Modify: `runtime/jesse_workspace/config.py`
  - 责任：提供最小回测配置（资金、费率、杠杆、模式等）。
- Modify: `runtime/jesse_workspace/routes.py`
  - 责任：配置基线路由（`ETH-USDT` `5m` + `Ott2butKAMA`）。
- Modify: `docs/runbook.md`
  - 责任：新增回测对照执行与结果查看步骤。
- Create: `docs/backtests/.gitkeep`
  - 责任：提供结果目录占位。
- Create: `docs/backtests/raw/.gitkeep`
  - 责任：提供原始日志目录占位。

### Task 1: 先写回测对照脚本测试（红灯）

**Files:**
- Create: `tests/test_run_backtest_compare.py`

- [ ] **Step 1: 写失败测试文件（参数/可比性/输出）**

创建 `tests/test_run_backtest_compare.py`，写入以下完整内容：

```python
from pathlib import Path

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

    with pytest.raises(ValueError):
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
        baseline_cmd="cmd baseline",
        candidate_cmd="cmd candidate",
        baseline_metrics={"trades": "100", "win_rate": "50%", "net_profit": "10%", "max_drawdown": "5%"},
        candidate_metrics={"trades": "110", "win_rate": "52%", "net_profit": "12%", "max_drawdown": "4.8%"},
        comparability_note="all fixed",
        conclusion="candidate better",
    )

    text = output.read_text()
    assert "## Summary" in text
    assert "baseline" in text
    assert "candidate" in text
    assert "candidate better" in text


def test_run_compare_writes_failure_report_when_runner_fails(tmp_path: Path):
    from scripts.run_backtest_compare import run_compare

    def fake_runner(_cmd: str):
        raise RuntimeError("runner failed")

    with pytest.raises(RuntimeError):
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
```

- [ ] **Step 2: 运行目标测试确认红灯**

Run:

```bash
.venv/bin/python -m pytest tests/test_run_backtest_compare.py -q
```

Expected: FAIL（`scripts/run_backtest_compare.py` 尚不存在）。

- [ ] **Step 3: Commit 红灯测试**

```bash
git add tests/test_run_backtest_compare.py
git commit -m "test: add failing coverage for backtest compare framework"
```

### Task 2: 实现回测对照脚本并让测试转绿

**Files:**
- Create: `scripts/run_backtest_compare.py`
- Test: `tests/test_run_backtest_compare.py`

- [ ] **Step 1: 实现脚本完整代码**

创建 `scripts/run_backtest_compare.py`：

```python
import argparse
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable


MetricMap = dict[str, str]


def ensure_comparable(*, symbol: str, timeframe: str, start: str, end: str, initial_balance: float, fee: float, leverage: int, mode: str) -> None:
    if not symbol:
        raise ValueError("symbol is required")
    if not timeframe:
        raise ValueError("timeframe is required")
    if start >= end:
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


def build_backtest_command(*, strategy: str, symbol: str, timeframe: str, start: str, end: str, initial_balance: float, fee: float, leverage: int, mode: str) -> str:
    return (
        "jesse run "
        f"--strategy {strategy} "
        f"--symbol {symbol} "
        f"--timeframe {timeframe} "
        f"--start {start} "
        f"--finish {end} "
        f"--fee {fee} "
        f"--balance {initial_balance} "
        f"--leverage {leverage} "
        f"--mode {mode}"
    )


def default_runner(command: str) -> str:
    completed = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
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
    baseline_cmd: str,
    candidate_cmd: str,
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
- baseline: `{baseline_cmd}`
- candidate: `{candidate_cmd}`

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


def write_failure_report(*, output_path: Path, stage: str, error: str, baseline_log: Path, candidate_log: Path) -> None:
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
    workspace: Path,
    docs_dir: Path,
    runner: Callable[[str], str] = default_runner,
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
    )

    baseline_log = raw_dir / f"{timestamp}-{baseline_tag}.log"
    candidate_log = raw_dir / f"{timestamp}-{candidate_tag}.log"
    failed_report = docs_dir / f"{timestamp}-compare-failed.md"
    report_path = docs_dir / f"{timestamp}-compare.md"

    try:
        baseline_output = runner(f"cd {workspace} && {baseline_cmd}")
        baseline_log.write_text(baseline_output)

        candidate_output = runner(f"cd {workspace} && {candidate_cmd}")
        candidate_log.write_text(candidate_output)

        baseline_metrics = parse_metrics(baseline_output)
        candidate_metrics = parse_metrics(candidate_output)

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
        write_failure_report(
            output_path=failed_report,
            stage="run_compare",
            error=str(exc),
            baseline_log=baseline_log,
            candidate_log=candidate_log,
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
    parser.add_argument("--leverage", type=int, default=2)
    parser.add_argument("--mode", default="futures")
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
        workspace=Path(args.workspace),
        docs_dir=Path(args.docs_dir),
    )
    print(f"compare_report={report}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 运行目标测试确认转绿**

Run:

```bash
.venv/bin/python -m pytest tests/test_run_backtest_compare.py -q
```

Expected: PASS。

- [ ] **Step 3: Commit 脚本实现**

```bash
git add scripts/run_backtest_compare.py tests/test_run_backtest_compare.py
git commit -m "feat: add baseline candidate backtest compare runner"
```

### Task 3: 补齐 Jesse runtime 最小回测配置

**Files:**
- Modify: `runtime/jesse_workspace/config.py`
- Modify: `runtime/jesse_workspace/routes.py`

- [ ] **Step 1: 写失败测试，验证 config/routes 非空且含基线路由**

在 `tests/test_jesse_runtime_import_path.py` 追加测试：

```python
from pathlib import Path


def test_runtime_backtest_config_and_routes_are_not_empty():
    config_text = Path("runtime/jesse_workspace/config.py").read_text()
    routes_text = Path("runtime/jesse_workspace/routes.py").read_text()

    assert "config =" in config_text
    assert "routes =" in routes_text
    assert "ETH-USDT" in routes_text
    assert "5m" in routes_text
```

- [ ] **Step 2: 运行测试确认红灯**

Run:

```bash
.venv/bin/python -m pytest tests/test_jesse_runtime_import_path.py -q
```

Expected: FAIL（当前 `config.py`/`routes.py` 仍为占位空对象）。

- [ ] **Step 3: 实现最小可运行配置**

将 `runtime/jesse_workspace/routes.py` 更新为：

```python
routes = [
    {
        "exchange": "Binance Perpetual Futures",
        "strategy": "Ott2butKAMA",
        "symbol": "ETH-USDT",
        "timeframe": "5m",
    }
]
```

将 `runtime/jesse_workspace/config.py` 更新为：

```python
config = {
    "app": {
        "considering_timeframes": ["5m"],
        "trading_mode": "backtest",
        "debug_mode": False,
    },
    "env": {
        "exchanges": {
            "Binance Perpetual Futures": {
                "fee": 0.0004,
                "balance": 10000,
                "type": "futures",
                "futures_leverage": 2,
            }
        }
    },
}
```

- [ ] **Step 4: 运行测试确认通过**

Run:

```bash
.venv/bin/python -m pytest tests/test_jesse_runtime_import_path.py -q
```

Expected: PASS。

- [ ] **Step 5: Commit 配置补齐**

```bash
git add runtime/jesse_workspace/config.py runtime/jesse_workspace/routes.py tests/test_jesse_runtime_import_path.py
git commit -m "chore: add minimal jesse runtime backtest config and route"
```

### Task 4: 补 runbook 与结果目录约定，执行一次对照回测

**Files:**
- Create: `docs/backtests/.gitkeep`
- Create: `docs/backtests/raw/.gitkeep`
- Modify: `docs/runbook.md`

- [ ] **Step 1: 创建结果目录占位文件**

创建空文件：

- `docs/backtests/.gitkeep`
- `docs/backtests/raw/.gitkeep`

- [ ] **Step 2: 在 runbook 中增加对照回测步骤**

在 `docs/runbook.md` 追加：

```markdown
## Backtest Compare

```bash
source runtime/jesse_workspace/.venv/bin/activate
python3 scripts/run_backtest_compare.py \
  --symbol ETHUSDT \
  --timeframe 5m \
  --start 2024-01-01 \
  --end 2024-02-01 \
  --baseline-strategy Ott2butKAMA \
  --candidate-strategy Ott2butKAMA
```

输出：

- 原始日志：`docs/backtests/raw/*.log`
- 对照报告：`docs/backtests/*-compare.md`
```

- [ ] **Step 3: 执行一次基线对照回测（baseline==candidate 作为框架验收）**

Run:

```bash
source runtime/jesse_workspace/.venv/bin/activate && python3 scripts/run_backtest_compare.py --symbol ETHUSDT --timeframe 5m --start 2024-01-01 --end 2024-02-01 --baseline-strategy Ott2butKAMA --candidate-strategy Ott2butKAMA
```

Expected:

- 生成 `docs/backtests/raw/*-baseline.log`
- 生成 `docs/backtests/raw/*-candidate.log`
- 生成 `docs/backtests/*-compare.md`

- [ ] **Step 4: Commit 文档与目录约定**

```bash
git add docs/runbook.md docs/backtests/.gitkeep docs/backtests/raw/.gitkeep docs/backtests
git commit -m "docs: document backtest compare workflow and outputs"
```

### Task 5: 全量验证与改动确认

**Files:**
- No additional code files required

- [ ] **Step 1: 跑全量测试**

Run:

```bash
.venv/bin/python -m pytest tests -q
```

Expected: PASS。

- [ ] **Step 2: 查看最终改动范围**

Run:

```bash
git status --short
```

Expected: 仅出现本计划涉及文件。

## Self-Review

- Spec coverage: 覆盖了配置层、执行层、证据层，包含失败摘要与可比性校验。
- Placeholder scan: 无 TBD/TODO/后补描述。
- Type consistency: `ensure_comparable` / `run_compare` / `parse_metrics` 等函数签名在测试和实现中一致。
