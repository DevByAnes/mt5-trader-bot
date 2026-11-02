"""Validate schema details a generator can otherwise relax (optional ≠ nullable)."""

import math
from collections.abc import Iterator
from decimal import Decimal, InvalidOperation
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker, ValidationError, validators
from pydantic import BaseModel, model_validator

from aurum_backend.core.resources import EVENTS, OPENAPI, SETTINGS


def multiple_of(
    validator: Any, divisor: float, instance: Any, schema: Any
) -> Iterator[ValidationError]:
    if isinstance(instance, bool) or not isinstance(instance, int | float):
        return
    try:
        if Decimal(str(instance)) % Decimal(str(divisor)):
            yield ValidationError("Number is not a multiple of the schema step")
    except InvalidOperation:
        yield ValidationError("Number must be finite")


Validator = validators.extend(Draft202012Validator, {"multipleOf": multiple_of})  # type: ignore[no-untyped-call]


def finite(value: Any) -> bool:
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, dict):
        return all(finite(v) for v in value.values())
    if isinstance(value, list):
        return all(finite(v) for v in value)
    return True


def validate_schema(name: str, value: Any) -> None:
    if not finite(value):
        raise ValueError("Nonfinite JSON value")
    if name == "SettingsMetadataValues":
        schema: Any = SETTINGS
    elif name == "Event":
        # Resolve local event references without any network fetch or changed frozen file.
        def resolve(node: Any) -> Any:
            if isinstance(node, dict):
                if "$ref" in node:
                    ref = node["$ref"].split("/")[-1]
                    components: Any = OPENAPI["components"]
                    return resolve(components["schemas"][ref])
                return {key: resolve(val) for key, val in node.items() if key != "$id"}
            if isinstance(node, list):
                return [resolve(v) for v in node]
            return node

        schema = resolve(EVENTS)
    else:
        schema = {"$ref": "#/components/schemas/" + name, "components": OPENAPI["components"]}
    Validator(schema, format_checker=FormatChecker()).validate(value)


class SchemaModel(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def enforce_source(cls, value: Any) -> Any:
        components: Any = OPENAPI["components"]
        if cls.__name__ in components["schemas"] or cls.__name__ == "SettingsMetadataValues":
            if isinstance(value, BaseModel):
                value = value.model_dump(mode="json", exclude_unset=True)
            try:
                validate_schema(cls.__name__, value)
            except ValidationError as exc:
                raise ValueError("Value violates frozen schema") from exc
        return value
