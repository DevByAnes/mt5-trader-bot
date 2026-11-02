import subprocess
import sys
from pathlib import Path

import pytest

from tools.no_orders import scan, violations

ROOT = Path(__file__).resolve().parents[1]


def test_no_execution_code_in_entire_src() -> None:
    assert scan(ROOT / "src") == []


@pytest.mark.parametrize(
    "symbol",
    [
        "order_send",
        "order_check_send",
        "order_modify",
        "positions_close",
        "OrderSend",
        "send_order",
        "place_order",
        "submit_order",
        "execute_order",
    ],
)
def test_guard_rejects_intentionally_bad_examples(tmp_path: Path, symbol: str) -> None:
    bad = tmp_path / "bad.py"
    bad.write_text(f"terminal.{symbol}({{}})\n", encoding="utf-8")
    assert violations(bad)
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "tools.no_orders", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )  # noqa: S603
    assert result.returncode == 1 and "execution" in result.stdout


def test_guard_rejects_import_alias_and_dynamic_string(tmp_path: Path) -> None:
    bad = tmp_path / "bad.py"
    bad.write_text(
        'from MetaTrader5 import order_send as innocuous\ngetattr(terminal, "order_modify")()\n',
        encoding="utf-8",
    )
    assert len(violations(bad)) >= 3
