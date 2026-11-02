"""Validated profile and native .set export; never exports permissions or credentials."""

import json
from typing import Any

from aurum_backend.bridge.codec import strict_json
from aurum_backend.core.resources import SETTINGS_V2
from aurum_backend.models.generated_settings_v2 import EASettings


def defaults() -> dict[str, Any]:
    properties: Any = SETTINGS_V2["properties"]
    result = {key: meta["default"] for key, meta in properties.items()}
    EASettings.model_validate(result)
    return result


def export_profile(values: dict[str, Any]) -> str:
    model = EASettings.model_validate(values)
    properties: Any = SETTINGS_V2["properties"]
    safe = {
        key: value
        for key, value in model.model_dump(mode="json").items()
        if not properties[key]["mt5_only"]
    }
    return json.dumps({"schema_version": "2.0.0", "values": safe}, sort_keys=True, indent=2)


def import_profile(raw: str, current: dict[str, Any]) -> dict[str, Any]:
    if len(raw.encode()) > 65536:
        raise ValueError("Profile too large")
    value = strict_json(raw.encode("utf-8"))
    if (
        not isinstance(value, dict)
        or set(value) != {"schema_version", "values"}
        or (value["schema_version"] != "2.0.0" or not isinstance(value["values"], dict))
    ):
        raise ValueError("Invalid profile envelope")
    properties: Any = SETTINGS_V2["properties"]
    for key in value["values"]:
        if key not in properties or properties[key]["mt5_only"]:
            raise ValueError("Profile cannot change a local permission or unknown field")
    result = {**current, **value["values"]}
    EASettings.model_validate(result)
    return result


def export_set(values: dict[str, Any]) -> str:
    model = EASettings.model_validate(values)
    properties: Any = SETTINGS_V2["properties"]
    lines = ["; Aurum schema 2.0.0 / experimental SIGNAL_ONLY tester inputs"]
    for key, value in model.model_dump(mode="json").items():
        meta = properties[key]
        if meta["mt5_only"]:
            value = meta["default"]
        if key == "InpExecutionMode":
            value = "SIGNAL_ONLY"
        if key == "InpBrokerOffsetMode":
            value = "MANUAL"
        if "enum" in meta:
            value = meta["enum"].index(value)
        elif isinstance(value, bool):
            value = "true" if value else "false"
        if any(c in str(value) for c in ["\n", "\r", "\x00"]):
            raise ValueError("Invalid native input characters")
        lines.append(f"{key}={value}")
    return "\r\n".join(lines) + "\r\n"
