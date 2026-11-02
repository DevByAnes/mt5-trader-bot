"""Read the frozen repository inputs; never silently substitute defaults."""

import json
from pathlib import Path
from typing import cast

from pydantic import JsonValue

ROOT = Path(__file__).resolve().parents[4]
SCHEMA = ROOT / "schema"
FIXTURES = ROOT / "fixtures"


def read_object(path: Path) -> dict[str, JsonValue]:
    value: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path.name}")
    return cast(dict[str, JsonValue], value)


OPENAPI = read_object(SCHEMA / "openapi.yaml")
SETTINGS = read_object(SCHEMA / "settings.schema.json")
SETTINGS_V2 = read_object(SCHEMA / "settings.v2.schema.json")
EVENTS = read_object(SCHEMA / "events.json")


def require_inputs() -> None:
    for path in [
        SCHEMA / "openapi.yaml",
        SCHEMA / "events.json",
        SCHEMA / "settings.schema.json",
        ROOT / "docs" / "CONTRACT.md",
    ]:
        if not path.is_file():
            raise RuntimeError(f"Required contract input missing: {path.name}")
    if not list(FIXTURES.glob("*.json")):
        raise RuntimeError("Required contract fixtures missing")
