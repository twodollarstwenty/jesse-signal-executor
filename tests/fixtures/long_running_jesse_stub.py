import sys
import time
from pathlib import Path


def main() -> None:
    heartbeat = Path(sys.argv[1])
    heartbeat.parent.mkdir(parents=True, exist_ok=True)
    heartbeat.write_text("ok")
    time.sleep(30)


if __name__ == "__main__":
    main()
