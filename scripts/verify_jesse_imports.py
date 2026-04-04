import os
import sys
from pathlib import Path


def _can_import(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:
        return False


def main() -> None:
    workspace = Path("runtime/jesse_workspace").resolve()
    os.chdir(workspace)

    project_root = Path("../..").resolve()
    runtime_strategies = workspace / "strategies"
    runtime_custom_indicators = workspace / "custom_indicators"
    runtime_custom_indicators_ottkama = workspace / "custom_indicators_ottkama"
    project_strategies = project_root / "strategies" / "jesse"

    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    if str(runtime_strategies) not in sys.path:
        sys.path.insert(0, str(runtime_strategies))
    if str(runtime_custom_indicators) not in sys.path:
        sys.path.insert(0, str(runtime_custom_indicators.parent))
    if str(runtime_custom_indicators_ottkama) not in sys.path:
        sys.path.insert(0, str(runtime_custom_indicators_ottkama.parent))
    if str(project_strategies) not in sys.path:
        sys.path.insert(0, str(project_strategies))

    print(f"import_jesse_ok={str(_can_import('jesse')).lower()}")
    print(f"import_talib_ok={str(_can_import('talib')).lower()}")
    print(f"import_ott2butkama_ok={str(_can_import('Ott2butKAMA')).lower()}")


if __name__ == "__main__":
    main()
