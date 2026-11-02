import subprocess
import sys


def main() -> None:
    for command in (
        [sys.executable, "-m", "ruff", "check", "."],
        [sys.executable, "-m", "tools.no_orders"],
    ):
        result = subprocess.run(command, check=False)  # noqa: S603
        if result.returncode:
            raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
