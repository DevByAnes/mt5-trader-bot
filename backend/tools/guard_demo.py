"""Demonstrate a deliberately bad src fails without modifying the real src tree."""

import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> None:
    with tempfile.TemporaryDirectory() as folder:
        source = Path(folder) / "src"
        source.mkdir()
        (source / "bad.py").write_text("terminal.order_send({})\n", encoding="utf-8")
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-m", "tools.no_orders", str(source)],
            capture_output=True,
            text=True,
            check=False,
        )
        print(result.stdout.strip())
        print("Deliberately bad sample exit code:", result.returncode, "(expected 1)")
        if result.returncode != 1:
            raise SystemExit("Safety guard demonstration failed")


if __name__ == "__main__":
    main()
