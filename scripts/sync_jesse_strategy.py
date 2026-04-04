from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]


def build_target_path(strategy_name: str) -> Path:
    return ROOT / "runtime" / "jesse_workspace" / "strategies" / strategy_name


def build_source_path(strategy_name: str) -> Path:
    return ROOT / "strategies" / "jesse" / strategy_name


def sync_strategy(strategy_name: str) -> None:
    source = build_source_path(strategy_name)
    target = build_target_path(strategy_name)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)

    for directory_name in ("custom_indicators_ottkama", "custom_indicators"):
        indicator_source = ROOT / "strategies" / "jesse" / directory_name
        indicator_target = ROOT / "runtime" / "jesse_workspace" / directory_name
        if indicator_target.exists():
            shutil.rmtree(indicator_target)
        shutil.copytree(indicator_source, indicator_target)


if __name__ == "__main__":
    sync_strategy("Ott2butKAMA")
