"""AST + text safety lint for the complete src tree, including aliases/strings."""

import ast
import re
import sys
from pathlib import Path

# Kept outside src: the runtime tree must contain no trading-execution identifiers.
FORBIDDEN = {
    "ordersend",
    "orderchecksend",
    "ordermodify",
    "positionsclose",
    "ordercheck",
    "positionclose",
    "positionmodify",
    "buy",
    "sell",
    "buylimit",
    "selllimit",
    "buystop",
    "sellstop",
    "sendorder",
    "placeorder",
    "submitorder",
    "executeorder",
}
PATTERN = re.compile(
    r"(?i)(?:order[_\s]*(?:send|check[_\s]*send|modify|check)|"
    r"positions?[_\s]*(?:close|modify)|(?:send|place|submit|execute)[_\s]*order)"
)
READ_ONLY_SDK_NAMES = {"initialize", "shutdown", "copy_rates_range", "TIMEFRAME_M15"}


def violations(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    found = [
        f"{path.name}:{text[: m.start()].count(chr(10)) + 1}: execution symbol"
        for m in PATTERN.finditer(text)
    ]
    if path.suffix != ".py":
        return found
    tree = ast.parse(text, filename=str(path))
    for node in ast.walk(tree):
        name = (
            node.attr
            if isinstance(node, ast.Attribute)
            else (node.id if isinstance(node, ast.Name) else "")
        )
        if name.replace("_", "").casefold() in FORBIDDEN:
            found.append(f"{path.name}:{getattr(node, 'lineno', 0)}: execution identifier")
        if isinstance(node, ast.Import):
            if any(n.name.casefold() in {"metatrader5", "ccxt"} for n in node.names):
                found.append(f"{path.name}:{node.lineno}: trading integration import")
        if isinstance(node, ast.ImportFrom) and (node.module or "").casefold() in {
            "metatrader5",
            "ccxt",
        }:
            isolated_reader = path.name == "mt5_readonly.py" and path.parent.name == "data"
            explicit_reads = node.module == "MetaTrader5" and all(
                n.name in READ_ONLY_SDK_NAMES and n.asname is None for n in node.names
            )
            if not isolated_reader or not explicit_reads:
                found.append(f"{path.name}:{node.lineno}: trading integration import")
    return found


def scan(root: Path) -> list[str]:
    return [
        error
        for path in root.rglob("*")
        if path.is_file() and path.suffix in {".py", ".pyi", ".md", ".json", ".toml"}
        for error in violations(path)
    ]


def main() -> None:
    errors = scan(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("src"))
    if errors:
        print("\n".join(errors))
        raise SystemExit(1)
    print("No execution symbols in src")


if __name__ == "__main__":
    main()
