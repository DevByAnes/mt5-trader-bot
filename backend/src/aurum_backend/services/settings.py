"""Shared configuration validation and risk-direction comparison, not trading math."""

from typing import Any

from aurum_backend.api.errors import ApiFault
from aurum_backend.core.resources import SETTINGS
from aurum_backend.models.generated import ApplyRequest
from aurum_backend.models.generated_settings import SettingsMetadataValues


def review_settings(
    current: dict[str, Any], body: ApplyRequest, prerequisites: list[dict[str, Any]]
) -> dict[str, Any]:
    if current["version"] != body.base_version:
        raise ApiFault("VERSION_CONFLICT", "Reload settings and review again", 409)
    proposed = body.values.model_dump(mode="json")
    SettingsMetadataValues.model_validate(proposed)
    properties: Any = SETTINGS["properties"]
    values = current["values"]
    for key, meta in properties.items():
        if meta["mt5_only"] and proposed[key] != values[key]:
            raise ApiFault("MT5_ONLY", "Value is read-only outside MT5", 403, key)
    if proposed["executionMode"] == "LIVE" and (
        not values["allowRealAccount"]
        or not prerequisites
        or any(not p["ok"] for p in prerequisites)
    ):
        raise ApiFault("LIVE_LOCKED", "LIVE prerequisites unavailable", 403, "executionMode")
    diff = []
    for key, new in proposed.items():
        old, meta = values[key], properties[key]
        if old == new:
            continue
        direction = "NEUTRAL"
        if meta["risk_direction"] != "NONE" and isinstance(old, int | float):
            looser = new > old if meta["risk_direction"] == "HIGHER_IS_LOOSER" else new < old
            direction = "LOOSER" if looser else "TIGHTER"
        diff.append(
            {
                "key": key,
                "old_value": old,
                "new_value": new,
                "apply": meta["apply"],
                "risk_level": meta["risk_level"],
                "direction": direction,
            }
        )
    return {"base_version": current["version"], "values": proposed, "diff": diff}
