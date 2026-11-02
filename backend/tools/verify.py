"""Run the complete B1 acceptance commands and keep concise, reviewable evidence."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    commands = [
        ["-m", "ruff", "check"],
        ["-m", "mypy"],
        ["-m", "tools.gen_models", "--check"],
        ["-m", "pytest", "-q"],
        ["-m", "tools.no_orders"],
        ["-m", "tools.guard_demo"],
        ["-m", "tools.smoke"],
    ]
    lines = ["B1 local verification — Windows / Python 3.14.10 / 2026-11-02"]
    for command in commands:
        title = "$ uv run python " + " ".join(command)
        print(title, flush=True)
        result = subprocess.run(  # noqa: S603
            [sys.executable, *command],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        evidence = result.stdout.strip() + ("\n" + result.stderr.strip() if result.stderr else "")
        print(evidence, flush=True)
        lines.extend([title, evidence, f"exit={result.returncode}", ""])
        (ROOT / "docs/VERIFICATION.txt").write_text("\n".join(lines), encoding="utf-8")
        if result.returncode:
            raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
