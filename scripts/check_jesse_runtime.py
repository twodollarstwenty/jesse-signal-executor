from pathlib import Path


def _can_import(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:
        return False


def main() -> None:
    venv_ok = Path("runtime/jesse_workspace/.venv").exists()
    print(f"jesse_ok={str(_can_import('jesse')).lower()}")
    print(f"talib_ok={str(_can_import('talib')).lower()}")
    print(f"venv_ok={str(venv_ok).lower()}")


if __name__ == "__main__":
    main()
