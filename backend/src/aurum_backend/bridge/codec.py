"""Authenticate exact bytes before accepting telemetry or control messages."""

import base64
import binascii
import hashlib
import hmac
import json
import re
import time
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from aurum_backend.core.resources import OPENAPI, SCHEMA, read_object
from aurum_backend.models.base import finite

MAX_WIRE_BYTES = 2_200_000
MAX_PAYLOAD_BYTES = 1_500_000


class BridgeFault(ValueError):
    """Messages intentionally contain no input payload or secret material."""


def json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("ascii")


def strict_json(raw: bytes) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise BridgeFault("DUPLICATE_KEY")
            result[key] = value
        return result

    def invalid(value: str) -> None:
        raise BridgeFault("NONFINITE_JSON")

    try:
        text = raw.decode("utf-8", errors="strict")
        if text.startswith("\ufeff"):
            raise BridgeFault("BOM_NOT_ALLOWED")
        parsed = json.loads(text, object_pairs_hook=pairs, parse_constant=invalid)
        if not finite(parsed):
            raise BridgeFault("NONFINITE_JSON")
        return parsed
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise BridgeFault("INVALID_JSON") from exc


def _schemas() -> tuple[dict[str, Any], dict[str, Any]]:
    source: Any = read_object(SCHEMA / "bridge.schema.json")
    components: Any = OPENAPI["components"]

    def resolve(value: Any) -> Any:
        if isinstance(value, dict):
            if "$ref" in value and not value["$ref"].startswith("#/$defs/"):
                return resolve(components["schemas"][value["$ref"].split("/")[-1]])
            return {k: resolve(v) for k, v in value.items()}
        if isinstance(value, list):
            return [resolve(v) for v in value]
        return value

    resolved = resolve(source)
    return resolved["$defs"]["Wire"], resolved["$defs"]["Payload"]


class SignedCodec:
    def __init__(self, key: bytes, key_id: str = "local-v1") -> None:
        if len(key) < 32 or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", key_id):
            raise BridgeFault("INVALID_KEY_CONFIGURATION")
        self._key = key
        self.key_id = key_id
        wire, payload = _schemas()
        self._wire = Draft202012Validator(wire, format_checker=FormatChecker())
        self._payload = Draft202012Validator(payload, format_checker=FormatChecker())

    def __repr__(self) -> str:
        return f"SignedCodec(key_id={self.key_id!r}, key=<redacted>)"

    def _signed_bytes(self, payload: bytes) -> bytes:
        return b"AURUM-FILE-V1\n" + self.key_id.encode("ascii") + b"\n" + payload

    def encode(self, payload: dict[str, Any]) -> bytes:
        if not self._payload.is_valid(payload):
            raise BridgeFault("INVALID_PAYLOAD_SCHEMA")
        raw = json_bytes(payload)
        if len(raw) > MAX_PAYLOAD_BYTES:
            raise BridgeFault("PAYLOAD_TOO_LARGE")
        return json_bytes(
            {
                "protocol_version": "1.0.0",
                "key_id": self.key_id,
                "payload_b64": base64.b64encode(raw).decode("ascii"),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "hmac_sha256": hmac.digest(self._key, self._signed_bytes(raw), "sha256").hex(),
            }
        )

    def decode(
        self,
        raw: bytes,
        *,
        expected_sender: str,
        expected_kind: str | None = None,
        instance: str | None = None,
        now_ms: int | None = None,
    ) -> dict[str, Any]:
        if len(raw) > MAX_WIRE_BYTES:
            raise BridgeFault("WIRE_TOO_LARGE")
        wire = strict_json(raw)
        if not self._wire.is_valid(wire) or wire["key_id"] != self.key_id:
            raise BridgeFault("INVALID_WIRE_SCHEMA")
        try:
            payload_bytes = base64.b64decode(wire["payload_b64"], validate=True)
        except (binascii.Error, ValueError) as exc:
            raise BridgeFault("INVALID_PAYLOAD_ENCODING") from exc
        if len(payload_bytes) > MAX_PAYLOAD_BYTES:
            raise BridgeFault("PAYLOAD_TOO_LARGE")
        digest = hashlib.sha256(payload_bytes).hexdigest()
        signature = hmac.digest(self._key, self._signed_bytes(payload_bytes), "sha256").hex()
        if not hmac.compare_digest(digest, wire["sha256"]) or not hmac.compare_digest(
            signature, wire["hmac_sha256"]
        ):
            raise BridgeFault("AUTHENTICATION_FAILED")
        payload = strict_json(payload_bytes)
        if not self._payload.is_valid(payload):
            raise BridgeFault("INVALID_PAYLOAD_SCHEMA")
        if payload["sender"] != expected_sender or (
            expected_kind and payload["kind"] != expected_kind
        ):
            raise BridgeFault("WRONG_MESSAGE_DIRECTION")
        if instance is not None and payload["ea_instance_id"] != instance:
            raise BridgeFault("WRONG_EA_INSTANCE")
        now = int(time.time() * 1000) if now_ms is None else now_ms
        if payload["issued_at_ms"] > now + 5000 or payload["expires_at_ms"] <= now:
            raise BridgeFault("EXPIRED_OR_FUTURE_MESSAGE")
        if not 0 < payload["expires_at_ms"] - payload["issued_at_ms"] <= 86400000:
            raise BridgeFault("INVALID_MESSAGE_LIFETIME")
        return payload  # type: ignore[no-any-return]
