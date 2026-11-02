"""Produce a separate, versioned FILE wire contract without changing public API v1."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    string = {"type": "string"}
    uuid = {"type": "string", "format": "uuid"}
    integer = {"type": "integer", "minimum": 0, "maximum": 9007199254740991}

    def obj(properties: dict[str, object], required: list[str] | None = None) -> dict[str, object]:
        return {
            "type": "object",
            "additionalProperties": False,
            "properties": properties,
            "required": list(properties) if required is None else required,
        }

    def ref(name: str) -> dict[str, str]:
        return {"$ref": "openapi.yaml#/components/schemas/" + name}

    resources = obj(
        {
            name: {"anyOf": [ref(name), {"type": "null"}]}
            for name in [
                "Status",
                "EaState",
                "Positions",
                "DailyRisk",
                "SettingsData",
                "Signals",
                "Chart",
                "Telemetry",
                "Journal",
                "Validation",
                "Logs",
            ]
        }
    )
    state = obj({"account_id": string, "symbol": string, "magic": integer, "resources": resources})
    config = obj(
        {
            "request_id": uuid,
            "base_version": integer,
            "config_version": integer,
            "values": ref("SettingsDraft"),
            "apply_at": {"enum": ["NEXT_M15", "NEXT_DAY"]},
            "confirmed_loosen": {"type": "boolean"},
        }
    )
    command = obj(
        {
            "request_id": uuid,
            "command": {
                "enum": ["kill-switch", "risk-free-all", "risk-free-position", "close-position"]
            },
            "position_id": {"type": ["string", "null"]},
        }
    )
    ack = obj(
        {
            "request_id": uuid,
            "status": {"enum": ["APPLIED", "REJECTED"]},
            "reason": {"type": ["string", "null"]},
            "version": {"type": ["integer", "null"]},
            "ea_ack_utc": {"type": "string", "format": "date-time"},
        }
    )
    variants = []
    for kind, source, body in [
        ("STATE", "EA", state),
        ("ACK", "EA", ack),
        ("CONFIG", "PYTHON", config),
        ("COMMAND", "PYTHON", command),
        ("HEARTBEAT", "PYTHON", obj({"api_version": {"const": "1.0.0"}})),
    ]:
        variants.append(
            obj(
                {
                    "kind": {"const": kind},
                    "sender": {"const": source},
                    "message_id": uuid,
                    "ea_instance_id": uuid,
                    "seq": integer,
                    "issued_at_ms": integer,
                    "expires_at_ms": integer,
                    "body": body,
                }
            )
        )
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$defs": {
            "Payload": {"oneOf": variants},
            "Wire": obj(
                {
                    "protocol_version": {"const": "1.0.0"},
                    "key_id": {"type": "string", "pattern": "^[A-Za-z0-9_-]{1,64}$"},
                    "payload_b64": {"type": "string", "minLength": 4, "maxLength": 2097152},
                    "sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
                    "hmac_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
                }
            ),
        },
        "$ref": "#/$defs/Wire",
        "title": "Aurum FILE wire v1",
        "x-signature": (
            "HMAC-SHA256(key, UTF8('AURUM-FILE-V1\\n' + key_id + '\\n') + payload_bytes); "
            "SHA256 covers exact decoded payload bytes. Strict UTF-8 JSON; "
            "no BOM/duplicate keys/nonfinite values."
        ),
    }
    (ROOT / "schema/bridge.schema.json").write_text(
        json.dumps(schema, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
