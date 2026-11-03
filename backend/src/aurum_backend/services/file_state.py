"""FILE service: observed EA telemetry and durable requests; no synthetic execution."""

import asyncio
import hashlib
import sqlite3
import time
from copy import deepcopy
from datetime import datetime
from typing import Any
from uuid import uuid4

from aurum_backend.api.envelope import envelope
from aurum_backend.api.errors import ApiFault
from aurum_backend.bridge.codec import BridgeFault, SignedCodec
from aurum_backend.bridge.files import AtomicFiles
from aurum_backend.core.config import Config
from aurum_backend.core.logging import log_event
from aurum_backend.core.time import utc_now
from aurum_backend.fixtures.state import FixtureState
from aurum_backend.models.base import validate_schema
from aurum_backend.models.generated import ApplyRequest
from aurum_backend.realtime.hub import EventHub
from aurum_backend.services.settings import review_settings
from aurum_backend.storage.sqlite import Repository


class FileState(EventHub):
    def __init__(self, config: Config) -> None:
        super().__init__(config)
        if (
            config.bridge_directory is None
            or config.database_path is None
            or config.bridge_key is None
        ):
            raise ValueError("Incomplete FILE configuration")
        self.config = config
        self.scenario = "normal"
        self.lock = asyncio.Lock()
        self.files = AtomicFiles(config.bridge_directory)
        self.codec = SignedCodec(config.bridge_key, config.bridge_key_id)
        self.repository = Repository(config.database_path, actor="local-session:" + str(uuid4()))
        identity = {
            "account_id": config.ea_account,
            "symbol": config.ea_symbol,
            "magic": config.ea_magic,
            "key_id": config.bridge_key_id,
        }
        try:
            with self.repository.transaction() as connection:
                bound = self.repository.get("bridge_identity")
                if bound and bound != identity:
                    raise ValueError("Database belongs to a different EA identity or key ID")
                cached = self.repository.get("ea_snapshot")
                if cached and any(
                    cached["body"][key] != identity[key]
                    for key in ["account_id", "symbol", "magic"]
                ):
                    raise ValueError("Cached EA identity does not match configuration")
                self.repository.put_tx(connection, "bridge_identity", identity)
        except BaseException:
            self.repository.close()
            raise
        self.subscribers: set[asyncio.Queue[tuple[str, Any]]] = set()
        self.overloaded: set[asyncio.Queue[tuple[str, Any]]] = set()
        self._events: list[tuple[str, Any]] = []
        self._last_heartbeat = 0.0
        self._last_error: str | None = None
        self._last_error_time = 0.0
        self._bridge_unavailable = False
        self._ack_cursor = ""

    paginate = staticmethod(FixtureState.paginate)

    @property
    def audit(self) -> list[dict[str, Any]]:
        return self.repository.audit_page()["items"]  # type: ignore[no-any-return]

    @property
    def version(self) -> int:
        return int(self.read("SettingsData")["version"])

    def available(self) -> None:
        if self._bridge_unavailable:
            raise ApiFault("UNAVAILABLE", "Bridge storage is unavailable", 503)

    def reset(self, scenario: str) -> None:
        raise ApiFault("UNAVAILABLE", "Simulation control is unavailable in FILE mode", 503)

    def close(self) -> None:
        self.repository.close()

    def _snapshot(self, *, fresh: bool = False) -> dict[str, Any]:
        if fresh:
            self.available()
        payload = self.repository.get("ea_snapshot")
        if not payload:
            raise ApiFault("UNAVAILABLE", "No authenticated EA snapshot available", 503)
        age = int(time.time() * 1000) - payload["issued_at_ms"]
        if fresh and age > 6000:
            raise ApiFault("EA_OFFLINE", "EA heartbeat is stale; request not sent", 503)
        status = payload["body"]["resources"]["Status"]
        if fresh and (
            status is None
            or status["ea"]["state"] != "healthy"
            or status["ea"]["heartbeat_utc"] is None
        ):
            raise ApiFault("EA_OFFLINE", "EA has not reported healthy status", 503)
        return payload  # type: ignore[no-any-return]

    def read(self, name: str) -> Any:
        if name == "Status":
            cached = self.repository.get("ea_snapshot")
            if not cached:
                missing = {"state": "offline", "heartbeat_utc": None, "latency_ms": None}
                return {
                    "backend": self._backend_status(),
                    "ea": dict(missing),
                    "mt5": dict(missing),
                    "broker_offset_minutes": None,
                }
            result = deepcopy(cached["body"]["resources"]["Status"])
            if result is None:
                raise ApiFault("UNAVAILABLE", "EA status resource unavailable", 503)
            result["backend"] = self._backend_status()
            age = int(time.time() * 1000) - cached["issued_at_ms"]
            if age > 6000:
                for node in ["ea", "mt5"]:
                    result[node]["state"] = "offline" if age > 15000 else "stale"
            return result
        if name == "Audit":
            return self.repository.audit_page()
        if name == "SettingsData":
            current = self.repository.get("settings")
            if current:
                pending = self.repository.unresolved_config()
                if pending:
                    current["pending_next_day"] = pending["apply_at"] == "NEXT_DAY"
                return current
        payload = self._snapshot()
        resource = payload["body"]["resources"].get(name)
        if resource is None:
            raise ApiFault("UNAVAILABLE", "Resource not reported by EA", 503)
        return deepcopy(resource)

    def validate(self, body: ApplyRequest) -> dict[str, Any]:
        self._snapshot(fresh=True)
        return review_settings(
            self.read("SettingsData"), body, self.read("EaState")["live_prerequisites"]
        )

    def accept(self, endpoint: str, key: str, payload: dict[str, Any]) -> dict[str, Any]:
        replay = self.repository.replay(endpoint, key, payload)
        if replay:
            return replay
        snapshot = self._snapshot(fresh=True)
        request_id = str(uuid4())
        config_version = None
        now = int(time.time() * 1000)
        deadline = now + 10000
        if endpoint == "/settings/apply":
            review = self.validate(ApplyRequest.model_validate(payload))
            if not self.read("SettingsData")["values"]["allowRemoteConfig"]:
                raise ApiFault(
                    "MT5_ONLY", "Remote configuration permission is disabled in MT5", 403
                )
            if any(x["direction"] == "LOOSER" for x in review["diff"]):
                raise ApiFault(
                    "VALIDATION_ERROR", "Risk loosening requires the explicit v2 confirmation flow"
                )
            if payload["values"]["executionMode"] == "LIVE":
                raise ApiFault("LIVE_LOCKED", "Native LIVE validation has not passed", 403)
            if (
                payload["values"]["executionMode"] == "AUTO_EXECUTE"
                and self.read("SettingsData")["values"]["executionMode"] != "AUTO_EXECUTE"
            ):
                raise ApiFault(
                    "MT5_ONLY", "Enable Demo AUTO_EXECUTE explicitly in MT5 inputs", 403
                )
            kind = "CONFIG"
            config_version = payload["base_version"] + 1
            deadline = now + 16 * 60000
            cold = any(x["apply"] == "COLD" for x in review["diff"])
            if cold:
                # EA's trade-day timestamp is authoritative; no broker-day arithmetic in Python.
                boundary = datetime.fromisoformat(self.read("DailyRisk")["next_day_utc"])
                deadline = int(boundary.timestamp() * 1000) + 60000
            body = {
                "request_id": request_id,
                "base_version": payload["base_version"],
                "config_version": config_version,
                "values": payload["values"],
                "apply_at": "NEXT_DAY" if cold else "NEXT_M15",
                "confirmed_loosen": False,
            }
        else:
            kind = "COMMAND"
            command = endpoint.rsplit("/", 1)[-1]
            position_id = payload.get("position_id")
            if command in {"risk-free-position", "close-position"}:
                if not position_id:
                    raise ApiFault("VALIDATION_ERROR", "position_id required", field="position_id")
                if position_id not in {p["id"] for p in self.read("Positions")}:
                    raise ApiFault("NOT_FOUND", "Position unavailable", 404)
            body = {"request_id": request_id, "command": command, "position_id": position_id}
        wire_payload = {
            "kind": kind,
            "sender": "PYTHON",
            "message_id": request_id,
            "ea_instance_id": snapshot["ea_instance_id"],
            "seq": self._sequence(),
            "issued_at_ms": now,
            "expires_at_ms": min(now + 86400000, deadline),
            "body": body,
        }
        wire = self.codec.encode(wire_payload)
        accepted = envelope(
            {
                "request_id": request_id,
                "status": "PENDING",
                "reason": None,
                "version": None,
                "ea_ack_utc": None,
            }
        )
        filename = ("config_" if kind == "CONFIG" else "command_") + request_id + ".json"
        # Durable outbox is committed before a file becomes visible. Redelivery has the same ID.
        return self.repository.accept(
            endpoint=endpoint,
            key=key,
            body=payload,
            request_id=request_id,
            accepted=accepted,
            target=snapshot["ea_instance_id"],
            deadline_ms=deadline,
            config_version=config_version,
            wire=wire,
            filename=filename,
            base_version=payload.get("base_version"),
            apply_at=body.get("apply_at"),
        )

    def _sequence(self) -> int:
        with self.repository.transaction() as connection:
            value = (self.repository.get("python_seq") or 0) + 1
            self.repository.put_tx(connection, "python_seq", value)
            return int(value)

    def request_result(self, identity: str) -> dict[str, Any]:
        return self.repository.result(identity)

    def settle(self) -> None:
        # Called by HTTP reconciliation too. File reads and HMAC validation happen in poll.
        self.repository.mark_timeouts(int(time.time() * 1000))

    def poll(self) -> list[tuple[str, Any]]:
        try:
            events = self._poll()
        except (OSError, sqlite3.Error, BridgeFault):
            if not self._bridge_unavailable:
                log_event("bridge_storage_unavailable", status=503)
            self._bridge_unavailable = True
            # Keep accepted outbox rows pending. Never acknowledge a failed write.
            return []
        self._bridge_unavailable = False
        return events

    def _backend_status(self) -> dict[str, Any]:
        return {
            "state": "stale" if self._bridge_unavailable else "healthy",
            "heartbeat_utc": utc_now(),
            "latency_ms": None,
        }

    def _poll(self) -> list[tuple[str, Any]]:
        names = sorted(p.name for p in self.files.root.glob("ack_*.json"))
        # Invalid files remain as evidence, but cannot starve a later valid Ack.
        names = [n for n in names if n > self._ack_cursor] + [
            n for n in names if n <= self._ack_cursor
        ]
        batch = names[:128]
        if batch:
            self._ack_cursor = batch[-1]
        for name in [
            "state.json",
            *batch,
        ]:
            try:
                raw = self.files.read(name)
                kind = "STATE" if name == "state.json" else "ACK"
                payload = self.codec.decode(raw, expected_sender="EA", expected_kind=kind)
                if kind == "STATE":
                    body = payload["body"]
                    if (body["account_id"], body["symbol"], body["magic"]) != (
                        self.config.ea_account,
                        self.config.ea_symbol,
                        self.config.ea_magic,
                    ):
                        raise BridgeFault("WRONG_EA_IDENTITY")
                if self.repository.receive(payload, hashlib.sha256(raw).hexdigest()):
                    if kind == "ACK":
                        result = payload["body"]
                        event = self.repository.event_for(result["request_id"])
                        self._events.append((event, result))
                    else:
                        for model, event in [
                            ("EaState", "ea_state"),
                            ("Positions", "position"),
                            ("DailyRisk", "risk_mode"),
                        ]:
                            value = body["resources"][model]
                            if value is not None:
                                self._events.append((event, value))
                if kind == "ACK":
                    self.files.remove(name)
            except FileNotFoundError:
                continue
            except (OSError, ValueError) as exc:
                code = type(exc).__name__
                if code != self._last_error or time.monotonic() - self._last_error_time > 10:
                    log_event("bridge_message_rejected")
                    self._last_error = code
                    self._last_error_time = time.monotonic()
        for row in self.repository.pending_writes():
            if row["deadline_ms"] <= int(time.time() * 1000):
                continue
            self.files.write(row["filename"], row["wire"])
            self.repository.dispatched(row["request_id"])
        self.settle()
        if time.monotonic() - self._last_heartbeat >= 2:
            snapshot = self.repository.get("ea_snapshot")
            if snapshot:
                now = int(time.time() * 1000)
                heartbeat = {
                    "kind": "HEARTBEAT",
                    "sender": "PYTHON",
                    "message_id": str(uuid4()),
                    "ea_instance_id": snapshot["ea_instance_id"],
                    "seq": self._sequence(),
                    "issued_at_ms": now,
                    "expires_at_ms": now + 15000,
                    "body": {"api_version": "1.0.0"},
                }
                self.files.write("python_heartbeat.json", self.codec.encode(heartbeat))
            self._events.append(("heartbeat", self.read("Status")))
            self._last_heartbeat = time.monotonic()
        events, self._events = self._events, []
        for kind, value in events:
            validate_schema(
                "Event", {"type": kind, "payload": value, "seq": 1, "server_time_utc": utc_now()}
            )
        return events
