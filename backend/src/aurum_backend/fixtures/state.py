"""In-memory B1 scenario state. No I/O bridge, persistence or trading calculations."""

import asyncio
import base64
import binascii
import json
import time
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from aurum_backend.api.errors import ApiFault
from aurum_backend.core.config import SCENARIOS, Config
from aurum_backend.core.resources import SETTINGS, read_object
from aurum_backend.core.time import utc_now
from aurum_backend.fixtures.loader import FixtureLoader
from aurum_backend.models.generated import ApplyRequest
from aurum_backend.models.generated_settings import SettingsMetadataValues
from aurum_backend.realtime.hub import EventHub

READS = {
    "/status": "Status",
    "/ea/state": "EaState",
    "/positions": "Positions",
    "/signals": "Signals",
    "/chart": "Chart",
    "/risk/daily": "DailyRisk",
    "/telemetry": "Telemetry",
    "/settings": "SettingsData",
    "/journal": "Journal",
    "/validation": "Validation",
    "/logs": "Logs",
    "/audit": "Audit",
}


@dataclass
class Operation:
    key: str
    endpoint: str
    signature: str
    request_id: str
    accepted: dict[str, Any]
    result: dict[str, Any]
    created: float
    ready: float
    outcome: str
    values: dict[str, Any] | None = None


class FixtureState(EventHub):
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        self.config = config
        self.loader = FixtureLoader()
        self.lock = asyncio.Lock()
        self.scenario = config.scenario
        self.operations: dict[str, Operation] = {}
        self.key_index: dict[str, str] = {}
        self.reserved = False
        self.values: dict[str, Any] = self.loader.data("SettingsData")["values"]
        self.version: int = self.loader.data("SettingsData")["version"]
        self.audit: list[dict[str, Any]] = self.loader.data("Audit")["items"]
        self.ack_templates: Any = read_object(Path(__file__).with_name("acks.json"))
        self.subscribers: set[asyncio.Queue[tuple[str, Any]]] = set()
        self.overloaded: set[asyncio.Queue[tuple[str, Any]]] = set()
        self.halted = False
        self.protected: set[str] = set()
        self.closed: set[str] = set()

    def reset(self, scenario: str) -> None:
        if scenario not in SCENARIOS:
            raise ApiFault("VALIDATION_ERROR", "Unknown simulation scenario", field="scenario")
        self.scenario = scenario
        self.operations.clear()
        self.key_index.clear()
        self.reserved = False
        self.values = self.loader.data("SettingsData")["values"]
        self.version = self.loader.data("SettingsData")["version"]
        self.audit = self.loader.data("Audit")["items"]
        self.halted = False
        self.protected.clear()
        self.closed.clear()
        self.overloaded.update(self.subscribers)

    def available(self) -> None:
        if self.scenario in {"python-offline", "bridge-offline"}:
            raise ApiFault("UNAVAILABLE", "SIMULATED_BRIDGE_UNAVAILABLE", 503)

    def read(self, name: str) -> Any:
        self.available()
        if name == "SettingsData":
            return {
                "version": self.version,
                "values": deepcopy(self.values),
                "pending_next_day": self.reserved,
            }
        if name == "Audit":
            return {"items": deepcopy(self.audit), "next_cursor": None}
        data = self.loader.data(name)
        if name == "Status":
            age = 12 if self.scenario == "stale" else 0
            heartbeat = (
                (datetime.now(UTC) - timedelta(seconds=age)).isoformat().replace("+00:00", "Z")
            )
            for key in ["backend", "ea", "mt5"]:
                data[key]["heartbeat_utc"] = heartbeat
                data[key]["state"] = "stale" if age else "healthy"
            if self.scenario == "ea-offline":
                data["ea"].update(state="offline", heartbeat_utc=None, latency_ms=None)
        if name == "EaState":
            data["mode"] = self.values["executionMode"]
            if self.scenario == "wide-spread":
                data["spread"] = 65
            if self.scenario.startswith("daily-") or self.halted:
                data["risk_active"] = False
                data["risk_reason"] = "OPERATOR_HALT" if self.halted else self.scenario.upper()
        if name == "DailyRisk":
            data["next_day_utc"] = (
                (
                    datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
                    + timedelta(days=1)
                )
                .isoformat()
                .replace("+00:00", "Z")
            )
            if self.scenario.startswith("daily-") or self.halted:
                data.update(
                    state="STOPPED",
                    reason="OPERATOR_HALT" if self.halted else self.scenario.upper(),
                )
                if self.scenario == "daily-loss":
                    data.update(loss_remaining=0, loss_remaining_percent=0)
                elif self.scenario == "daily-profit":
                    data.update(profit_remaining=0, profit_remaining_percent=0)
                elif self.scenario == "daily-count":
                    data["trades_remaining"] = 0
        if name == "Positions":
            if self.scenario == "no-positions":
                return []
            if self.scenario == "multi-positions":
                data.append({**data[0], "id": "XAU-1043", "side": "SELL", "r": -0.12})
            data = [p for p in data if p["id"] not in self.closed]
            for position in data:
                if position["id"] in self.protected:
                    position["risk_free"] = True
        return data

    @staticmethod
    def paginate(
        data: dict[str, Any], resource: str, cursor: str | None, limit: int
    ) -> dict[str, Any]:
        items = sorted(data["items"], key=lambda x: x.get("time_utc", ""), reverse=True)
        offset = 0
        if cursor:
            try:
                parsed = json.loads(base64.b64decode(cursor, validate=True))
                if not isinstance(parsed, dict) or parsed.get("resource") != resource:
                    raise ValueError
                index = next(i for i, item in enumerate(items) if item["id"] == parsed["after"])
                offset = index + 1
            except (ValueError, KeyError, StopIteration, binascii.Error, UnicodeError) as exc:
                raise ApiFault(
                    "VALIDATION_ERROR", "Invalid or expired cursor", field="cursor"
                ) from exc
        page = items[offset : offset + limit]
        next_cursor = None
        if offset + limit < len(items):
            next_cursor = base64.b64encode(
                json.dumps({"resource": resource, "after": page[-1]["id"]}).encode()
            ).decode()
        return {**data, "items": page, "next_cursor": next_cursor}

    def validate(self, body: ApplyRequest) -> dict[str, Any]:
        if body.base_version != self.version or self.scenario == "version-conflict":
            raise ApiFault("VERSION_CONFLICT", "Reload settings and review again", 409)
        proposed = body.values.model_dump(mode="json")
        SettingsMetadataValues.model_validate(proposed)
        properties: Any = SETTINGS["properties"]
        for key, meta in properties.items():
            if meta["mt5_only"] and proposed[key] != self.values[key]:
                raise ApiFault("MT5_ONLY", "Value is read-only outside MT5", 403, key)
        if proposed["executionMode"] == "LIVE":
            prerequisites = self.loader.data("EaState")["live_prerequisites"]
            if not self.values["allowRealAccount"] or any(not p["ok"] for p in prerequisites):
                raise ApiFault(
                    "LIVE_LOCKED", "LIVE prerequisites unavailable", 403, "executionMode"
                )
        diff = []
        for key, new in proposed.items():
            old, meta = self.values[key], properties[key]
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
        return {"base_version": self.version, "values": proposed, "diff": diff}

    def accept(self, endpoint: str, key: str, payload: dict[str, Any]) -> dict[str, Any]:
        signature = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        previous_id = self.key_index.get(key)
        if previous_id:
            op = self.operations[previous_id]
            if op.endpoint != endpoint or op.signature != signature:
                raise ApiFault("IDEMPOTENCY_CONFLICT", "Key reused with different request", 409)
            # Exact accepted response replay. Terminal result is resolved by GET /requests/{id}.
            return deepcopy(op.accepted)
        if len(self.operations) >= self.config.max_operations:
            raise ApiFault("UNAVAILABLE", "Simulation operation capacity reached", 503)
        if self.scenario == "ea-offline":
            raise ApiFault("EA_OFFLINE", "SIMULATED_EA_OFFLINE; request not accepted", 503)
        proposed = None
        if endpoint == "/settings/apply":
            if self.reserved:
                raise ApiFault("VERSION_CONFLICT", "A settings request is unresolved", 409)
            draft = ApplyRequest.model_validate(payload)
            proposed = self.validate(draft)["values"]
            self.reserved = True
        else:
            command = endpoint.rsplit("/", 1)[-1]
            if command in {"risk-free-position", "close-position"}:
                position_id = payload.get("position_id")
                if not position_id:
                    raise ApiFault("VALIDATION_ERROR", "position_id required", field="position_id")
                if position_id not in {p["id"] for p in self.read("Positions")}:
                    raise ApiFault("NOT_FOUND", "Position unavailable", 404)
        request_id = str(uuid4())
        ack = deepcopy(self.ack_templates["PENDING"])
        ack["request_id"] = request_id
        outcome = {"ack-rejected": "REJECTED", "ack-timeout": "TIMEOUT"}.get(
            self.scenario, "APPLIED"
        )
        accepted = {
            "data": deepcopy(ack),
            "error": None,
            "server_time_utc": utc_now(),
            "api_version": "1.0.0",
        }
        op = Operation(
            key,
            endpoint,
            signature,
            request_id,
            accepted,
            ack,
            time.monotonic(),
            time.monotonic() + self.config.ack_seconds,
            outcome,
            proposed,
        )
        self.operations[request_id] = op
        self.key_index[key] = request_id
        return deepcopy(accepted)

    def settle(self) -> None:
        now = time.monotonic()
        for op in self.operations.values():
            if op.result["status"] != "PENDING" or now < op.ready:
                continue
            result = (
                self.loader.data("Ack")
                if op.outcome == "APPLIED"
                else deepcopy(self.ack_templates[op.outcome])
            )
            result["request_id"] = op.request_id
            if op.outcome == "APPLIED":
                result["ea_ack_utc"] = utc_now()
                if op.values is not None:
                    previous = deepcopy(self.values)
                    self.values = deepcopy(op.values)
                    self.version += 1
                    self.audit.insert(
                        0,
                        {
                            "id": str(uuid4()),
                            "time_utc": utc_now(),
                            "actor": "fixture-session",
                            "action": "SETTINGS_APPLIED",
                            "version": self.version,
                            "result": "APPLIED",
                            "previous_values": previous,
                        },
                    )
                    self.reserved = False
                else:
                    command = op.endpoint.rsplit("/", 1)[-1]
                    payload = json.loads(op.signature)
                    if command == "kill-switch":
                        self.halted = True
                    if command == "risk-free-all":
                        self.protected.update(p["id"] for p in self.read("Positions"))
                    if command == "risk-free-position":
                        self.protected.add(payload["position_id"])
                    if command == "close-position":
                        self.closed.add(payload["position_id"])
                result["version"] = self.version if op.values is not None else None
            elif op.outcome == "REJECTED" and op.values is not None:
                self.reserved = False
            # TIMEOUT keeps a config reservation: unknown must not become implicit failure.
            op.result = result
            self.publish("config_ack" if op.values is not None else "command_ack", result)

    def request_result(self, identity: str) -> dict[str, Any]:
        request_id = self.key_index.get(identity, identity)
        if request_id not in self.operations:
            raise ApiFault("NOT_FOUND", "Request not found in this simulated session", 404)
        return deepcopy(self.operations[request_id].result)
