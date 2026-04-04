from apps.shared.settings import Settings


def main() -> None:
    settings = Settings()
    print(f"executor-service ready in {settings.execution_mode}")


if __name__ == "__main__":
    main()
