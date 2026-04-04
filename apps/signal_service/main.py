from apps.shared.settings import Settings


def main() -> None:
    settings = Settings()
    print(f"signal-service ready for {settings.default_symbol}")


if __name__ == "__main__":
    main()
