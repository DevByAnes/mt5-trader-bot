"""Load original root fixtures, validate them before serving, and return copies."""

from copy import deepcopy
from typing import Any

from aurum_backend.core.resources import FIXTURES, read_object, require_inputs
from aurum_backend.models.base import validate_schema


class FixtureLoader:
    def __init__(self) -> None:
        require_inputs()
        self.examples: dict[str, Any] = {}
        for path in sorted(FIXTURES.glob("*.json")):
            name = path.stem
            example = read_object(path)
            validate_schema(name + "Envelope", example)
            self.examples[name] = example

    def data(self, name: str) -> Any:
        return deepcopy(self.examples[name]["data"])
