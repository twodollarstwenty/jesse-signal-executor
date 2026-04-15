# Multi-Strategy Multi-Symbol Supervisor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a config-driven dry-run supervisor that can run multiple strategy-symbol instances concurrently with per-instance capital allocation, sizing rules, state isolation, and status reporting.

**Architecture:** Parameterize the current single-instance live loop into a reusable worker that accepts one validated instance config. Introduce `instance_id` as the isolation key across runtime files and database-backed execution state, then layer a supervisor over the workers so the existing `dryrun_start/status/stop` commands can manage all enabled instances together.

**Tech Stack:** Python, pytest, pydantic, PyYAML, shell scripts, PostgreSQL, existing Jesse runtime bootstrap

---

## File Structure

- Create: `apps/runtime/instance_config.py`
  Purpose: load `configs/dryrun_instances.yaml`, validate instances, and expose typed config models.
- Create: `apps/runtime/sizing.py`
  Purpose: compute per-instance order sizing for `fixed_fraction`, `fixed_notional`, and `risk_per_trade`.
- Create: `apps/runtime/instance_runtime.py`
  Purpose: build per-instance runtime paths for logs, heartbeats, `last_action`, and `last_candle_ts`.
- Create: `scripts/run_strategy_instance.py`
  Purpose: execute one configured strategy-symbol instance using the parameterized live loop.
- Create: `scripts/run_dryrun_supervisor.py`
  Purpose: load config, sync strategies, start workers, stop workers, and report aggregate/per-instance status.
- Create: `configs/dryrun_instances.yaml`
  Purpose: declare enabled strategy-symbol instances and per-instance sizing/capital settings.
- Modify: `scripts/run_jesse_live_loop.py`
  Purpose: remove hard-coded single-instance assumptions and expose functions that accept instance config and runtime state paths.
- Modify: `scripts/run_jesse_dryrun_loop.py`
  Purpose: delegate to the new single-instance worker entrypoint for backward-compatible smoke coverage.
- Modify: `scripts/dryrun_start.sh`
  Purpose: delegate start orchestration to the supervisor.
- Modify: `scripts/dryrun_status.sh`
  Purpose: delegate aggregate and per-instance status reporting to the supervisor.
- Modify: `scripts/dryrun_stop.sh`
  Purpose: delegate stop behavior to the supervisor.
- Modify: `scripts/sync_jesse_strategy.py`
  Purpose: sync all unique strategy directories required by the instance config.
- Modify: `apps/signal_service/writer.py`
  Purpose: persist `instance_id` in emitted signals and include it in signal hashes.
- Modify: `apps/signal_service/jesse_bridge/emitter.py`
  Purpose: require `instance_id`, include sizing payload, and keep notifications compatible.
- Modify: `apps/executor_service/service.py`
  Purpose: consume `instance_id`, isolate position state by instance, and lock by instance instead of symbol.
- Modify: `apps/executor_service/cli.py`
  Purpose: preserve executor loop behavior while consuming instance-aware signals.
- Modify: `scripts/summarize_dryrun_validation.py`
  Purpose: add instance-aware summary output.
- Modify: `docs/runbook.md`
  Purpose: document the new config-driven supervisor workflow.
- Test: `tests/test_run_jesse_live_loop.py`
  Purpose: cover worker parameterization and per-instance runtime state handling.
- Test: `tests/test_dryrun_daemon_scripts.py`
  Purpose: cover shell entrypoints delegating to the supervisor.
- Test: `tests/test_sync_jesse_strategy.py`
  Purpose: cover syncing multiple unique strategies from config.
- Test: `tests/test_executor_service_unit.py`
  Purpose: cover instance-aware payloads and position updates.
- Create: `tests/test_instance_config.py`
  Purpose: validate config parsing, duplicate IDs, sizing validation, and enabled-instance loading.
- Create: `tests/test_sizing.py`
  Purpose: cover the three sizing modes and stop-price requirements.
- Create: `tests/test_dryrun_supervisor.py`
  Purpose: cover aggregate status, mixed worker health, and instance directory layout.

### Task 1: Add Instance Config Loading And Validation

**Files:**
- Create: `apps/runtime/instance_config.py`
- Create: `tests/test_instance_config.py`
- Create: `configs/dryrun_instances.yaml`

- [ ] **Step 1: Write the failing config tests**

Add `tests/test_instance_config.py` with these tests:

```python
from pathlib import Path

import pytest


def test_load_instances_reads_enabled_instance_config(tmp_path: Path):
    from apps.runtime.instance_config import load_instances

    config_path = tmp_path / "dryrun_instances.yaml"
    config_path.write_text(
        """
instances:
  - id: ott_eth_5m
    enabled: true
    strategy: Ott2butKAMA
    symbol: ETHUSDT
    timeframe: 5m
    capital_usdt: 1000
    sizing:
      mode: fixed_fraction
      position_fraction: 0.2
      leverage: 10
  - id: disabled_case
    enabled: false
    strategy: Ott2butKAMA
    symbol: BTCUSDT
    timeframe: 5m
    capital_usdt: 1000
    sizing:
      mode: fixed_notional
      notional_usdt: 250
""".strip()
    )

    instances = load_instances(config_path)

    assert [instance.id for instance in instances] == ["ott_eth_5m"]
    assert instances[0].strategy == "Ott2butKAMA"
    assert instances[0].sizing.mode == "fixed_fraction"


def test_load_instances_rejects_duplicate_ids(tmp_path: Path):
    from apps.runtime.instance_config import load_instances

    config_path = tmp_path / "dryrun_instances.yaml"
    config_path.write_text(
        """
instances:
  - id: duplicate
    enabled: true
    strategy: Ott2butKAMA
    symbol: ETHUSDT
    timeframe: 5m
    capital_usdt: 1000
    sizing:
      mode: fixed_fraction
      position_fraction: 0.2
  - id: duplicate
    enabled: true
    strategy: Ott2butKAMA_RiskManaged25
    symbol: SOLUSDT
    timeframe: 5m
    capital_usdt: 1200
    sizing:
      mode: risk_per_trade
      risk_fraction: 0.025
""".strip()
    )

    with pytest.raises(ValueError, match="duplicate instance id"):
        load_instances(config_path)


def test_load_instances_rejects_invalid_sizing_block(tmp_path: Path):
    from apps.runtime.instance_config import load_instances

    config_path = tmp_path / "dryrun_instances.yaml"
    config_path.write_text(
        """
instances:
  - id: broken_risk
    enabled: true
    strategy: Ott2butKAMA_RiskManaged25
    symbol: SOLUSDT
    timeframe: 5m
    capital_usdt: 1200
    sizing:
      mode: risk_per_trade
""".strip()
    )

    with pytest.raises(ValueError, match="risk_per_trade"):
        load_instances(config_path)
```

- [ ] **Step 2: Run the config tests to verify they fail**

Run: `pytest tests/test_instance_config.py -v`

Expected: FAIL because `apps.runtime.instance_config` does not exist yet.

- [ ] **Step 3: Write the minimal config loader and sample config**

Create `apps/runtime/instance_config.py` with this implementation:

```python
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator


SizingMode = Literal["fixed_fraction", "fixed_notional", "risk_per_trade"]


class SizingConfig(BaseModel):
    mode: SizingMode
    position_fraction: float | None = None
    leverage: float | None = None
    notional_usdt: float | None = None
    risk_fraction: float | None = None
    risk_bps: int | None = None

    @model_validator(mode="after")
    def validate_mode_fields(self):
        if self.mode == "fixed_fraction" and self.position_fraction is None:
            raise ValueError("fixed_fraction sizing requires position_fraction")
        if self.mode == "fixed_notional" and self.notional_usdt is None:
            raise ValueError("fixed_notional sizing requires notional_usdt")
        if self.mode == "risk_per_trade" and self.risk_fraction is None and self.risk_bps is None:
            raise ValueError("risk_per_trade sizing requires risk_fraction or risk_bps")
        return self


class InstanceConfig(BaseModel):
    id: str
    enabled: bool = True
    strategy: str
    symbol: str
    timeframe: str = "5m"
    capital_usdt: float = Field(gt=0)
    sizing: SizingConfig


class InstanceConfigFile(BaseModel):
    instances: list[InstanceConfig]


def load_instances(config_path: Path) -> list[InstanceConfig]:
    raw = yaml.safe_load(config_path.read_text()) or {}
    parsed = InstanceConfigFile.model_validate(raw)
    enabled_instances = [instance for instance in parsed.instances if instance.enabled]
    seen_ids: set[str] = set()
    for instance in enabled_instances:
        if instance.id in seen_ids:
            raise ValueError(f"duplicate instance id: {instance.id}")
        seen_ids.add(instance.id)
    return enabled_instances
```

Create `configs/dryrun_instances.yaml` with this initial content:

```yaml
instances:
  - id: ott_eth_5m
    enabled: true
    strategy: Ott2butKAMA
    symbol: ETHUSDT
    timeframe: 5m
    capital_usdt: 1000
    sizing:
      mode: fixed_fraction
      position_fraction: 0.2
      leverage: 10
```

- [ ] **Step 4: Run the config tests to verify they pass**

Run: `pytest tests/test_instance_config.py -v`

Expected: PASS for enabled-instance loading, duplicate-ID rejection, and sizing validation.

- [ ] **Step 5: Commit the config foundation**

```bash
git add apps/runtime/instance_config.py configs/dryrun_instances.yaml tests/test_instance_config.py
git commit -m "feat: add dryrun instance config loader"
```

### Task 2: Add Runtime Paths And Sizing Engine

**Files:**
- Create: `apps/runtime/instance_runtime.py`
- Create: `apps/runtime/sizing.py`
- Create: `tests/test_sizing.py`

- [ ] **Step 1: Write the failing sizing tests**

Add `tests/test_sizing.py` with these tests:

```python
import pytest


def test_fixed_fraction_sizing_uses_capital_fraction_and_leverage():
    from apps.runtime.sizing import compute_order_qty

    qty = compute_order_qty(
        capital_usdt=1000,
        price=2500,
        sizing={"mode": "fixed_fraction", "position_fraction": 0.2, "leverage": 10},
        signal_payload={},
    )

    assert qty == 0.8


def test_fixed_notional_sizing_uses_configured_notional():
    from apps.runtime.sizing import compute_order_qty

    qty = compute_order_qty(
        capital_usdt=1000,
        price=2500,
        sizing={"mode": "fixed_notional", "notional_usdt": 300},
        signal_payload={},
    )

    assert qty == 0.12


def test_risk_per_trade_sizing_requires_stop_price():
    from apps.runtime.sizing import compute_order_qty

    with pytest.raises(ValueError, match="stop_price"):
        compute_order_qty(
            capital_usdt=1200,
            price=100,
            sizing={"mode": "risk_per_trade", "risk_fraction": 0.025},
            signal_payload={},
        )


def test_risk_per_trade_sizing_uses_stop_distance():
    from apps.runtime.sizing import compute_order_qty

    qty = compute_order_qty(
        capital_usdt=1200,
        price=100,
        sizing={"mode": "risk_per_trade", "risk_fraction": 0.025},
        signal_payload={"stop_price": 95},
    )

    assert qty == 6.0
```

- [ ] **Step 2: Run the sizing tests to verify they fail**

Run: `pytest tests/test_sizing.py -v`

Expected: FAIL because `apps.runtime.sizing` does not exist yet.

- [ ] **Step 3: Implement runtime path helpers and sizing functions**

Create `apps/runtime/instance_runtime.py`:

```python
from pathlib import Path


def build_instance_root(runtime_root: Path, instance_id: str) -> Path:
    return runtime_root / "instances" / instance_id


def build_instance_paths(runtime_root: Path, instance_id: str) -> dict[str, Path]:
    root = build_instance_root(runtime_root, instance_id)
    return {
        "root": root,
        "log": root / "logs" / "worker.log",
        "heartbeat": root / "heartbeats" / "worker.heartbeat",
        "last_action": root / "state" / "last_action.txt",
        "last_candle": root / "state" / "last_candle_ts.txt",
    }
```

Create `apps/runtime/sizing.py`:

```python
def _round_qty(value: float) -> float:
    return round(value, 8)


def compute_order_qty(*, capital_usdt: float, price: float, sizing: dict, signal_payload: dict) -> float:
    mode = sizing["mode"]
    if price <= 0:
        raise ValueError("price must be positive")

    if mode == "fixed_fraction":
        leverage = float(sizing.get("leverage", 1.0))
        position_fraction = float(sizing["position_fraction"])
        return _round_qty((capital_usdt * position_fraction * leverage) / price)

    if mode == "fixed_notional":
        return _round_qty(float(sizing["notional_usdt"]) / price)

    if mode == "risk_per_trade":
        stop_price = signal_payload.get("stop_price")
        if stop_price is None:
            raise ValueError("risk_per_trade sizing requires stop_price")
        stop_distance = abs(float(price) - float(stop_price))
        if stop_distance <= 0:
            raise ValueError("risk_per_trade sizing requires a positive stop distance")
        risk_fraction = sizing.get("risk_fraction")
        if risk_fraction is None:
            risk_fraction = float(sizing["risk_bps"]) / 10000
        allowed_loss = capital_usdt * float(risk_fraction)
        return _round_qty(allowed_loss / stop_distance)

    raise ValueError(f"unsupported sizing mode: {mode}")
```

- [ ] **Step 4: Run the sizing tests to verify they pass**

Run: `pytest tests/test_sizing.py -v`

Expected: PASS for all three sizing modes and stop-price validation.

- [ ] **Step 5: Commit the runtime helpers and sizing layer**

```bash
git add apps/runtime/instance_runtime.py apps/runtime/sizing.py tests/test_sizing.py
git commit -m "feat: add instance runtime paths and sizing"
```

### Task 3: Parameterize The Live Loop For One Instance

**Files:**
- Modify: `scripts/run_jesse_live_loop.py`
- Create: `scripts/run_strategy_instance.py`
- Modify: `tests/test_run_jesse_live_loop.py`

- [ ] **Step 1: Write the failing worker-parameterization tests**

Append these tests to `tests/test_run_jesse_live_loop.py`:

```python
from pathlib import Path


def test_build_runtime_context_uses_instance_config_for_strategy_symbol_and_state_paths(tmp_path: Path):
    from scripts.run_jesse_live_loop import build_runtime_context

    context = build_runtime_context(
        instance={
            "id": "ott_btc_5m",
            "strategy": "Ott2butKAMA",
            "symbol": "BTCUSDT",
            "timeframe": "5m",
            "capital_usdt": 800,
            "sizing": {"mode": "fixed_fraction", "position_fraction": 0.15, "leverage": 10},
        },
        runtime_root=tmp_path,
    )

    assert context["strategy_name"] == "Ott2butKAMA"
    assert context["symbol"] == "BTC-USDT"
    assert context["paths"]["last_action"] == tmp_path / "instances" / "ott_btc_5m" / "state" / "last_action.txt"


def test_run_cycle_uses_instance_specific_last_candle_file(tmp_path: Path, monkeypatch):
    import scripts.run_jesse_live_loop as module

    workspace = tmp_path / "runtime" / "jesse_workspace"
    workspace.mkdir(parents=True)
    state_file = tmp_path / "instances" / "ott_eth_5m" / "state" / "last_candle_ts.txt"
    state_file.parent.mkdir(parents=True)
    state_file.write_text("1712189100000")

    context = {
        "instance_id": "ott_eth_5m",
        "strategy_name": "Ott2butKAMA",
        "symbol": "ETH-USDT",
        "timeframe": "5m",
        "capital_usdt": 1000,
        "sizing": {"mode": "fixed_fraction", "position_fraction": 0.2, "leverage": 10},
        "paths": {"last_candle": state_file, "last_action": tmp_path / "last_action.txt"},
    }

    monkeypatch.setattr(module, "ensure_runtime_ready", lambda: workspace)
    monkeypatch.setattr(module, "prepare_import_path", lambda current: None)
    monkeypatch.setattr(module, "fetch_recent_klines", lambda symbol, interval="5m", limit=50: {
        "symbol": "ETHUSDT",
        "close_prices": [2505.0, 2516.8, 2524.1],
        "latest_timestamp": 1712189100000,
        "timestamp": "2026-04-05T21:33:20+08:00",
    })
    monkeypatch.setattr(module, "emit_strategy_signals", lambda context, loop_state=None: (_ for _ in ()).throw(AssertionError("should not emit")))
    module.LAST_PROCESSED_CANDLE_TS = None

    module.run_cycle(context)

    assert module.LAST_PROCESSED_CANDLE_TS == 1712189100000
```

- [ ] **Step 2: Run the live-loop tests to verify they fail**

Run: `pytest tests/test_run_jesse_live_loop.py -v`

Expected: FAIL because `build_runtime_context()` does not exist and `run_cycle()` does not yet accept an instance context.

- [ ] **Step 3: Implement the minimal instance-aware live loop and worker entrypoint**

Update `scripts/run_jesse_live_loop.py` so these functions exist and are used by the main cycle:

```python
from apps.runtime.instance_runtime import build_instance_paths


def normalize_symbol(symbol: str) -> str:
    return symbol if "-" in symbol else f"{symbol[:-4]}-{symbol[-4:]}"


def build_runtime_context(*, instance: dict, runtime_root: Path) -> dict:
    return {
        "instance_id": instance["id"],
        "strategy_name": instance["strategy"],
        "symbol": normalize_symbol(instance["symbol"]),
        "timeframe": instance["timeframe"],
        "capital_usdt": float(instance["capital_usdt"]),
        "sizing": dict(instance["sizing"]),
        "paths": build_instance_paths(runtime_root, instance["id"]),
    }


def run_cycle(context: dict | None = None) -> None:
    context = context or DEFAULT_CONTEXT
    # replace global STRATEGY_NAME / SYMBOL / TIMEFRAME reads with context[...] values
    # replace read/write last action and last candle helpers with context["paths"] entries
    # replace emit_strategy_signals(loop_state) with emit_strategy_signals(context, loop_state)
```

Create `scripts/run_strategy_instance.py`:

```python
import os
from pathlib import Path

from apps.runtime.instance_config import load_instances
from scripts.run_jesse_live_loop import build_runtime_context, run_cycle


def main() -> None:
    repo_root = Path(os.getenv("REPO_ROOT", Path(__file__).resolve().parents[1]))
    runtime_root = Path(os.getenv("DRYRUN_RUNTIME_DIR", repo_root / "runtime" / "dryrun"))
    config_path = Path(os.getenv("DRYRUN_INSTANCES_CONFIG", repo_root / "configs" / "dryrun_instances.yaml"))
    target_instance_id = os.environ["DRYRUN_INSTANCE_ID"]
    instances = load_instances(config_path)
    instance = next(item for item in instances if item.id == target_instance_id)
    context = build_runtime_context(instance=instance.model_dump(), runtime_root=runtime_root)
    run_cycle(context)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the live-loop tests to verify they pass**

Run: `pytest tests/test_run_jesse_live_loop.py -v`

Expected: PASS for the existing candle handling tests and the new instance-context tests.

- [ ] **Step 5: Commit the parameterized worker core**

```bash
git add scripts/run_jesse_live_loop.py scripts/run_strategy_instance.py tests/test_run_jesse_live_loop.py
git commit -m "feat: parameterize dryrun strategy worker"
```

### Task 4: Make Signal Persistence And Execution Instance-Aware

**Files:**
- Modify: `apps/signal_service/writer.py`
- Modify: `apps/signal_service/jesse_bridge/emitter.py`
- Modify: `apps/executor_service/service.py`
- Modify: `tests/test_executor_service_unit.py`

- [ ] **Step 1: Write the failing instance-aware executor tests**

Replace `tests/test_executor_service_unit.py` with this content:

```python
from apps.executor_service.service import build_execution_payload


def test_build_execution_payload_keeps_instance_id_and_dry_run_mode():
    payload = build_execution_payload(instance_id="ott_eth_5m", signal_id=1, symbol="ETHUSDT", status="execute")

    assert payload["instance_id"] == "ott_eth_5m"
    assert payload["signal_id"] == 1
    assert payload["mode"] == "dry_run"
    assert payload["status"] == "execute"


def test_build_position_payload_persists_instance_id_qty_and_entry_price_for_open_position():
    from apps.executor_service.service import build_position_payload

    payload = build_position_payload(
        instance_id="ott_eth_5m",
        symbol="ETHUSDT",
        side="long",
        signal_payload={"price": 2450.0, "qty": 2.5},
    )

    assert payload == {
        "instance_id": "ott_eth_5m",
        "symbol": "ETHUSDT",
        "side": "long",
        "qty": 2.5,
        "entry_price": 2450.0,
        "state_json": {},
    }
```

- [ ] **Step 2: Run the executor unit tests to verify they fail**

Run: `pytest tests/test_executor_service_unit.py -v`

Expected: FAIL because the service helpers do not yet accept `instance_id`.

- [ ] **Step 3: Implement minimal instance-aware signal and executor payload changes**

Update `apps/signal_service/writer.py` so `build_signal_hash()` and `insert_signal()` accept `instance_id` and include it in the hash payload.

Update `apps/signal_service/jesse_bridge/emitter.py` so `emit_signal()` requires `instance_id` and passes it to `insert_signal()`.

Update `apps/executor_service/service.py` with these signatures and payload structures:

```python
def build_execution_payload(*, instance_id: str, signal_id: int, symbol: str, status: str) -> dict:
    return {
        "instance_id": instance_id,
        "signal_id": signal_id,
        "symbol": symbol,
        "side": "unknown",
        "mode": "dry_run",
        "status": status,
        "detail_json": {"source": "executor_service"},
    }


def build_position_payload(*, instance_id: str, symbol: str, side: str, signal_payload: dict) -> dict:
    if side == "flat":
        return {
            "instance_id": instance_id,
            "symbol": symbol,
            "side": "flat",
            "qty": 0.0,
            "entry_price": 0.0,
            "state_json": {},
        }

    return {
        "instance_id": instance_id,
        "symbol": symbol,
        "side": side,
        "qty": float(signal_payload.get("qty", 1.0)),
        "entry_price": float(signal_payload.get("price", 0.0)),
        "state_json": {},
    }
```

Also update the executor queries so current-side fetch and position insert operate by `instance_id` instead of symbol-only.

- [ ] **Step 4: Run the executor unit tests to verify they pass**

Run: `pytest tests/test_executor_service_unit.py -v`

Expected: PASS for instance-aware execution and position payload construction.

- [ ] **Step 5: Commit the instance-aware persistence changes**

```bash
git add apps/signal_service/writer.py apps/signal_service/jesse_bridge/emitter.py apps/executor_service/service.py tests/test_executor_service_unit.py
git commit -m "feat: isolate executor state by instance"
```

### Task 5: Sync Multiple Strategies From Config

**Files:**
- Modify: `scripts/sync_jesse_strategy.py`
- Modify: `tests/test_sync_jesse_strategy.py`

- [ ] **Step 1: Write the failing strategy-sync tests**

Append these tests to `tests/test_sync_jesse_strategy.py`:

```python
from pathlib import Path


def test_sync_strategies_copies_each_unique_strategy_once(tmp_path, monkeypatch):
    import scripts.sync_jesse_strategy as module

    monkeypatch.setattr(module, "ROOT", tmp_path)

    for name in ("Ott2butKAMA", "Ott2butKAMA_RiskManaged25"):
        strategy_source = tmp_path / "strategies" / "jesse" / name
        strategy_source.mkdir(parents=True)
        (strategy_source / "__init__.py").write_text(f"# {name}")

    shared_source = tmp_path / "strategies" / "shared"
    shared_source.mkdir(parents=True)
    (shared_source / "ott2butkama_core.py").write_text("CORE = True")
    (shared_source / "ott2butkama_features.py").write_text("FEATURES = True")

    for directory_name in ("custom_indicators_ottkama", "custom_indicators"):
        source = tmp_path / "strategies" / "jesse" / directory_name
        source.mkdir(parents=True)
        (source / "__init__.py").write_text("# indicator")

    module.sync_strategies(["Ott2butKAMA", "Ott2butKAMA", "Ott2butKAMA_RiskManaged25"])

    assert (tmp_path / "runtime" / "jesse_workspace" / "strategies" / "Ott2butKAMA" / "__init__.py").exists()
    assert (tmp_path / "runtime" / "jesse_workspace" / "strategies" / "Ott2butKAMA_RiskManaged25" / "__init__.py").exists()
```

- [ ] **Step 2: Run the strategy-sync tests to verify they fail**

Run: `pytest tests/test_sync_jesse_strategy.py -v`

Expected: FAIL because `sync_strategies()` does not exist yet.

- [ ] **Step 3: Implement multi-strategy sync support**

Update `scripts/sync_jesse_strategy.py` with this helper and keep `sync_strategy()` intact:

```python
def sync_strategies(strategy_names: list[str]) -> None:
    seen: set[str] = set()
    for strategy_name in strategy_names:
        if strategy_name in seen:
            continue
        seen.add(strategy_name)
        sync_strategy(strategy_name)
```

- [ ] **Step 4: Run the strategy-sync tests to verify they pass**

Run: `pytest tests/test_sync_jesse_strategy.py -v`

Expected: PASS for the existing single-strategy path tests and the new unique-strategy sync test.

- [ ] **Step 5: Commit the strategy-sync upgrade**

```bash
git add scripts/sync_jesse_strategy.py tests/test_sync_jesse_strategy.py
git commit -m "feat: sync unique strategies for dryrun config"
```

### Task 6: Add Supervisor Python Entry Point And Shell Delegation

**Files:**
- Create: `scripts/run_dryrun_supervisor.py`
- Create: `tests/test_dryrun_supervisor.py`
- Modify: `scripts/dryrun_start.sh`
- Modify: `scripts/dryrun_status.sh`
- Modify: `scripts/dryrun_stop.sh`
- Modify: `tests/test_dryrun_daemon_scripts.py`

- [ ] **Step 1: Write the failing supervisor tests**

Create `tests/test_dryrun_supervisor.py` with these tests:

```python
from pathlib import Path


def test_build_supervisor_status_reports_mixed_instance_health(tmp_path: Path):
    from scripts.run_dryrun_supervisor import build_supervisor_status

    runtime_root = tmp_path / "runtime"
    health = {
        "ott_eth_5m": {"state": "running"},
        "risk25_sol_5m": {"state": "failed"},
    }

    status = build_supervisor_status(runtime_root=runtime_root, instance_health=health)

    assert status["supervisor"] == "degraded"
    assert status["instances_total"] == 2
    assert status["instances_running"] == 1
    assert status["instances_failed"] == 1
```

Append this shell-level smoke to `tests/test_dryrun_daemon_scripts.py`:

```python
def test_dryrun_start_script_delegates_to_supervisor_command(tmp_path):
    runtime_root = tmp_path / "runtime-root"
    env = os.environ.copy()
    env["DRYRUN_RUNTIME_DIR"] = str(runtime_root)
    env["DRYRUN_SKIP_PROCESS_START"] = "1"

    completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/dryrun_start.sh")],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert (runtime_root / "supervisor").exists()
```

- [ ] **Step 2: Run the supervisor and daemon tests to verify they fail**

Run: `pytest tests/test_dryrun_supervisor.py tests/test_dryrun_daemon_scripts.py -v`

Expected: FAIL because the supervisor script and supervisor status helpers do not exist yet.

- [ ] **Step 3: Implement the minimal supervisor and shell delegation**

Create `scripts/run_dryrun_supervisor.py`:

```python
import os
from pathlib import Path

from apps.runtime.instance_config import load_instances
from apps.runtime.instance_runtime import build_instance_paths
from scripts.sync_jesse_strategy import sync_strategies


def build_supervisor_status(*, runtime_root: Path, instance_health: dict[str, dict]) -> dict:
    running = sum(1 for item in instance_health.values() if item["state"] == "running")
    failed = sum(1 for item in instance_health.values() if item["state"] == "failed")
    if not instance_health:
        supervisor = "stopped"
    elif failed and running:
        supervisor = "degraded"
    elif failed:
        supervisor = "degraded"
    else:
        supervisor = "running"
    return {
        "supervisor": supervisor,
        "instances_total": len(instance_health),
        "instances_running": running,
        "instances_failed": failed,
    }


def ensure_supervisor_layout(runtime_root: Path) -> None:
    (runtime_root / "supervisor" / "logs").mkdir(parents=True, exist_ok=True)
    (runtime_root / "supervisor" / "pids").mkdir(parents=True, exist_ok=True)


def main() -> None:
    repo_root = Path(os.getenv("REPO_ROOT", Path(__file__).resolve().parents[1]))
    runtime_root = Path(os.getenv("DRYRUN_RUNTIME_DIR", repo_root / "runtime" / "dryrun"))
    config_path = Path(os.getenv("DRYRUN_INSTANCES_CONFIG", repo_root / "configs" / "dryrun_instances.yaml"))
    ensure_supervisor_layout(runtime_root)
    instances = load_instances(config_path)
    sync_strategies([instance.strategy for instance in instances])
```

Update `scripts/dryrun_start.sh`, `scripts/dryrun_status.sh`, and `scripts/dryrun_stop.sh` so each shell script invokes `python3 scripts/run_dryrun_supervisor.py` with a mode argument (`start`, `status`, `stop`) instead of embedding single-instance process assumptions directly.

- [ ] **Step 4: Run the supervisor and daemon tests to verify they pass**

Run: `pytest tests/test_dryrun_supervisor.py tests/test_dryrun_daemon_scripts.py -v`

Expected: PASS for supervisor status aggregation and shell delegation smoke coverage.

- [ ] **Step 5: Commit the supervisor orchestration layer**

```bash
git add scripts/run_dryrun_supervisor.py scripts/dryrun_start.sh scripts/dryrun_status.sh scripts/dryrun_stop.sh tests/test_dryrun_supervisor.py tests/test_dryrun_daemon_scripts.py
git commit -m "feat: add dryrun supervisor orchestration"
```

### Task 7: Add Instance-Aware Validation Summary And Runbook Updates

**Files:**
- Modify: `scripts/summarize_dryrun_validation.py`
- Modify: `docs/runbook.md`

- [ ] **Step 1: Write the failing instance-summary test**

Add this test to `tests/test_status_script.py` if that file already covers command output, otherwise create `tests/test_dryrun_summary_instances.py`:

```python
def test_render_summary_includes_instance_rollups():
    from scripts.summarize_dryrun_validation import render_summary

    summary = {
        "window_minutes": 60,
        "signal_count": 3,
        "execution_count": 2,
        "signal_status_counts": {"execute": 2, "ignored": 1},
        "latest_signal_time": None,
        "latest_execution_time": None,
        "instances": {
            "ott_eth_5m": {"signal_count": 2, "execution_count": 1},
            "risk25_sol_5m": {"signal_count": 1, "execution_count": 1},
        },
    }

    text = render_summary(summary)

    assert "instance: ott_eth_5m signal_count=2 execution_count=1" in text
    assert "instance: risk25_sol_5m signal_count=1 execution_count=1" in text
```

- [ ] **Step 2: Run the summary test to verify it fails**

Run: `pytest tests/test_dryrun_summary_instances.py -v`

Expected: FAIL because the summary renderer does not yet include per-instance lines.

- [ ] **Step 3: Implement the minimal summary and runbook update**

Update `scripts/summarize_dryrun_validation.py` so `fetch_summary()` returns an `instances` mapping and `render_summary()` appends one line per instance in sorted order:

```python
for instance_id, instance_summary in sorted(summary["instances"].items()):
    lines.append(
        f"instance: {instance_id} signal_count={instance_summary['signal_count']} execution_count={instance_summary['execution_count']}"
    )
```

Update `docs/runbook.md` to document:

- `configs/dryrun_instances.yaml` as the source of enabled workers
- the supervisor-managed `dryrun_start/status/stop` workflow
- the instance-aware validation summary output

- [ ] **Step 4: Run the summary test to verify it passes**

Run: `pytest tests/test_dryrun_summary_instances.py -v`

Expected: PASS with per-instance summary lines included.

- [ ] **Step 5: Commit the observability updates**

```bash
git add scripts/summarize_dryrun_validation.py docs/runbook.md tests/test_dryrun_summary_instances.py
git commit -m "feat: add instance-aware dryrun summaries"
```

### Task 8: Final Verification

**Files:**
- Modify: none
- Test: `tests/test_instance_config.py`
- Test: `tests/test_sizing.py`
- Test: `tests/test_run_jesse_live_loop.py`
- Test: `tests/test_executor_service_unit.py`
- Test: `tests/test_sync_jesse_strategy.py`
- Test: `tests/test_dryrun_supervisor.py`
- Test: `tests/test_dryrun_daemon_scripts.py`
- Test: `tests/test_dryrun_summary_instances.py`

- [ ] **Step 1: Run the focused implementation test suite**

Run:

```bash
pytest \
  tests/test_instance_config.py \
  tests/test_sizing.py \
  tests/test_run_jesse_live_loop.py \
  tests/test_executor_service_unit.py \
  tests/test_sync_jesse_strategy.py \
  tests/test_dryrun_supervisor.py \
  tests/test_dryrun_daemon_scripts.py \
  tests/test_dryrun_summary_instances.py -v
```

Expected: PASS for all targeted multi-instance runtime coverage.

- [ ] **Step 2: Run one shell-level status smoke against the configured supervisor**

Run:

```bash
bash scripts/dryrun_start.sh
bash scripts/dryrun_status.sh
bash scripts/dryrun_stop.sh
```

Expected: start succeeds, status prints supervisor and per-instance lines, stop succeeds without leaving stale supervisor layout.

- [ ] **Step 3: Commit the final verification checkpoint**

```bash
git add docs/runbook.md scripts tests apps tests
git commit -m "test: verify multi-instance dryrun supervisor flow"
```
