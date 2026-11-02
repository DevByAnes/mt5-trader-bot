import base64
import os
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from starlette.testclient import TestClient

from aurum_backend.api.errors import ApiFault
from aurum_backend.bridge.codec import BridgeFault, SignedCodec, json_bytes, strict_json
from aurum_backend.bridge.files import AtomicFiles
from aurum_backend.core.config import Config
from aurum_backend.core.time import utc_now
from aurum_backend.fixtures.loader import FixtureLoader
from aurum_backend.main import create_app
from aurum_backend.services.file_state import FileState
from aurum_backend.storage import sqlite as storage
from aurum_backend.storage.sqlite import Repository

from .conftest import HEADERS, TOKEN

KEY = bytes(range(32))


def file_config(root: Path) -> Config:
    return Config(
        token=TOKEN,
        backend_mode="file",
        bridge_directory=root / "common",
        database_path=root / "state.sqlite",
        bridge_key=KEY,
        ea_account="demo-123",
        requests_per_minute=100000,
    )


def message(
    kind: str = "STATE",
    *,
    seq: int = 1,
    instance: str | None = None,
    body: dict[str, Any] | None = None,
    issued_ms: int | None = None,
) -> dict[str, Any]:
    now = int(time.time() * 1000) if issued_ms is None else issued_ms
    if body is None:
        loader = FixtureLoader()
        body = {
            "account_id": "demo-123",
            "symbol": "XAUUSD",
            "magic": 260110,
            "resources": {
                name: loader.data(name)
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
            },
        }
        for key in ["backend", "ea", "mt5"]:
            body["resources"]["Status"][key]["heartbeat_utc"] = utc_now()
    return {
        "kind": kind,
        "sender": "EA",
        "message_id": str(uuid4()),
        "ea_instance_id": instance or str(uuid4()),
        "seq": seq,
        "issued_at_ms": now,
        "expires_at_ms": now + 30000,
        "body": body,
    }


def seed(state: FileState) -> dict[str, Any]:
    payload = message()
    state.files.write("state.json", state.codec.encode(payload))
    state.poll()
    return payload


def acknowledge(
    state: FileState,
    snapshot: dict[str, Any],
    request_id: str,
    *,
    seq: int = 1,
    status: str = "APPLIED",
    version: int | None = None,
) -> dict[str, Any]:
    body = {
        "request_id": request_id,
        "status": status,
        "reason": None,
        "version": version,
        "ea_ack_utc": utc_now(),
    }
    payload = message("ACK", instance=snapshot["ea_instance_id"], seq=seq, body=body)
    state.files.write("ack_" + payload["message_id"] + ".json", state.codec.encode(payload))
    return payload


def test_exact_byte_authentication_and_direction() -> None:
    codec = SignedCodec(KEY)
    value = message()
    encoded = codec.encode(value)
    assert codec.decode(encoded, expected_sender="EA") == value
    wire = strict_json(encoded)
    wire["payload_b64"] = base64.b64encode(b"{}").decode()
    with pytest.raises(BridgeFault, match="AUTHENTICATION"):
        codec.decode(json_bytes(wire), expected_sender="EA")
    with pytest.raises(BridgeFault, match="WRONG_MESSAGE_DIRECTION"):
        codec.decode(encoded, expected_sender="PYTHON")
    with pytest.raises(BridgeFault, match="WRONG_EA_INSTANCE"):
        codec.decode(encoded, expected_sender="EA", instance=str(uuid4()))
    assert KEY.hex() not in repr(codec)


@given(st.binary(min_size=0, max_size=400))
@settings(max_examples=100, deadline=None)
def test_arbitrary_bytes_cannot_authenticate(value: bytes) -> None:
    with pytest.raises(BridgeFault):
        SignedCodec(KEY).decode(value, expected_sender="EA")


@pytest.mark.parametrize(
    "raw", [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e9999}', b"\xef\xbb\xbf{}", b"\xff"]
)
def test_strict_json(raw: bytes) -> None:
    with pytest.raises(BridgeFault):
        strict_json(raw)


def test_expired_future_and_wrong_key() -> None:
    now = int(time.time() * 1000)
    codec = SignedCodec(KEY)
    with pytest.raises(BridgeFault, match="EXPIRED"):
        codec.decode(codec.encode(message(issued_ms=now - 31000)), expected_sender="EA", now_ms=now)
    with pytest.raises(BridgeFault, match="FUTURE"):
        codec.decode(codec.encode(message(issued_ms=now + 6000)), expected_sender="EA", now_ms=now)
    with pytest.raises(BridgeFault, match="AUTHENTICATION"):
        SignedCodec(b"x" * 32).decode(codec.encode(message()), expected_sender="EA")


def test_atomic_file_boundary_and_failure_preserves_previous(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    files = AtomicFiles(tmp_path / "common")
    files.write("state.json", b"previous")
    for name in ["../outside.json", "a/b.json", "C:\\bad.json", "state.json.tmp"]:
        with pytest.raises(BridgeFault):
            files.write(name, b"bad")

    def fail(*args: Any) -> None:
        raise OSError("Injected replace failure")

    monkeypatch.setattr(os, "replace", fail)
    with pytest.raises(OSError):
        files.write("state.json", b"next")
    assert files.read("state.json") == b"previous"
    assert not list(files.root.glob("*.tmp"))


def test_file_mode_never_fabricates_snapshot(tmp_path: Path) -> None:
    state = FileState(file_config(tmp_path))
    try:
        assert state.read("Status")["ea"]["state"] == "offline"
        with pytest.raises(ApiFault, match="No authenticated"):
            state.read("EaState")
        with pytest.raises(ApiFault):
            state.accept("/commands/kill-switch", str(uuid4()), {})
        assert not state.repository.pending_writes()
    finally:
        state.close()


def test_command_outbox_ack_restart_and_exact_replay(tmp_path: Path) -> None:
    config = file_config(tmp_path)
    state = FileState(config)
    snapshot = seed(state)
    key = str(uuid4())
    accepted = state.accept("/commands/kill-switch", key, {})
    request_id = accepted["data"]["request_id"]
    assert accepted["data"]["status"] == "PENDING"
    state.close()
    state = FileState(config)
    try:
        state.poll()
        command = state.codec.decode(
            state.files.read("command_" + request_id + ".json"), expected_sender="PYTHON"
        )
        assert command["body"]["command"] == "kill-switch"
        assert state.accept("/commands/kill-switch", key, {}) == accepted
        with pytest.raises(ApiFault, match="different"):
            state.accept("/commands/risk-free-all", key, {})
        acknowledge(state, snapshot, request_id)
        state.poll()
        assert state.request_result(key)["status"] == "APPLIED"
        assert not list(state.files.root.glob("ack_*.json"))
        state.repository.verify_audit()
    finally:
        state.close()
    state = FileState(config)
    try:
        assert state.request_result(request_id)["status"] == "APPLIED"
        assert state.accept("/commands/kill-switch", key, {}) == accepted
    finally:
        state.close()


def test_settings_ack_timeout_keeps_reservation_then_late_ack(tmp_path: Path) -> None:
    state = FileState(file_config(tmp_path))
    try:
        snapshot = seed(state)
        current = state.read("SettingsData")
        body = {"base_version": 7, "values": {**current["values"], "maxSpread": 30}}
        accepted = state.accept("/settings/apply", str(uuid4()), body)
        request_id = accepted["data"]["request_id"]
        assert state.read("SettingsData")["values"]["maxSpread"] == 35
        state.repository.mark_timeouts(int(time.time() * 1000) + 2_000_000)
        assert state.request_result(request_id)["status"] == "TIMEOUT"
        with pytest.raises(ApiFault):
            state.accept("/settings/apply", str(uuid4()), body)
        acknowledge(state, snapshot, request_id, version=8)
        events = state.poll()
        assert state.request_result(request_id)["status"] == "APPLIED"
        assert state.read("SettingsData")["values"]["maxSpread"] == 30
        assert state.audit[0]["previous_values"]["maxSpread"] == 35
        assert any(kind == "config_ack" for kind, _ in events)
    finally:
        state.close()


def test_replay_conflicting_ack_and_bad_identity_are_rejected(tmp_path: Path) -> None:
    state = FileState(file_config(tmp_path))
    try:
        first = seed(state)
        old = deepcopy(first)
        old["message_id"] = str(uuid4())
        state.files.write("state.json", state.codec.encode(old))
        state.poll()
        assert state.read("SettingsData")["version"] == 7
        foreign = message(seq=2, instance=first["ea_instance_id"])
        foreign["body"]["account_id"] = "other-account"
        state.files.write("state.json", state.codec.encode(foreign))
        state.poll()
        assert state.repository.get("ea_snapshot")["message_id"] == first["message_id"]
        request = state.accept("/commands/kill-switch", str(uuid4()), {})
        rid = request["data"]["request_id"]
        acknowledge(state, first, rid)
        state.poll()
        acknowledge(state, first, rid, seq=2, status="REJECTED")
        state.poll()
        assert state.request_result(rid)["status"] == "APPLIED"
    finally:
        state.close()


def test_audit_is_append_only_and_tampering_is_detected(tmp_path: Path) -> None:
    repository = Repository(tmp_path / "audit.sqlite")
    try:
        with repository.transaction() as connection:
            repository.audit_tx(connection, "TEST", "local", {"value": 1})
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            repository.connection.execute("UPDATE audit SET action='bad'")
        with pytest.raises(sqlite3.IntegrityError):
            repository.connection.execute("DELETE FROM audit")
        repository.verify_audit()
        repository.connection.execute("DROP TRIGGER audit_no_update")
        repository.connection.execute("UPDATE audit SET action='bad'")
        with pytest.raises(RuntimeError, match="Audit chain"):
            repository.verify_audit()
    finally:
        repository.close()


def test_real_http_observes_external_signed_peer(tmp_path: Path) -> None:
    config = file_config(tmp_path)
    app = create_app(config)
    with TestClient(
        app, base_url="http://127.0.0.1:8765", headers=HEADERS, client=("127.0.0.1", 50000)
    ) as client:
        assert client.get("/api/v1/ea/state").status_code == 503
        assert client.get("/api/v1/status").headers["x-aurum-mode"] == "file"
        state: FileState = app.state.fixture_state
        seed(state)
        assert client.get("/api/v1/ea/state").json()["data"]["mode"] == "PAPER"
        response = client.post(
            "/api/v1/commands/kill-switch", json={}, headers={"Idempotency-Key": str(uuid4())}
        )
        assert response.status_code == 202 and response.json()["data"]["status"] == "PENDING"
        assert client.post("/__dev/scenario", json={"scenario": "normal"}).status_code == 404


def test_disk_failure_keeps_outbox_and_recovers_same_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = FileState(file_config(tmp_path))
    try:
        seed(state)
        accepted = state.accept("/commands/kill-switch", str(uuid4()), {})
        identity = accepted["data"]["request_id"]
        original = state.files.write

        def disk_full(*args: Any) -> None:
            raise OSError("Injected disk full")

        monkeypatch.setattr(state.files, "write", disk_full)
        assert state.poll() == []
        assert state.read("Status")["backend"]["state"] == "stale"
        assert state.request_result(identity)["status"] == "PENDING"
        with pytest.raises(ApiFault, match="storage"):
            state.accept("/commands/kill-switch", str(uuid4()), {})
        monkeypatch.setattr(state.files, "write", original)
        state.poll()
        assert state.read("Status")["backend"]["state"] == "healthy"
        payload = state.codec.decode(
            state.files.read("command_" + identity + ".json"), expected_sender="PYTHON"
        )
        assert payload["message_id"] == identity
    finally:
        state.close()


def test_invalid_ack_files_cannot_starve_a_later_valid_ack(tmp_path: Path) -> None:
    state = FileState(file_config(tmp_path))
    try:
        snapshot = seed(state)
        accepted = state.accept("/commands/kill-switch", str(uuid4()), {})
        identity = accepted["data"]["request_id"]
        for index in range(129):
            state.files.write(f"ack_000_{index:04}.json", b"invalid")
        acknowledge(state, snapshot, identity)
        state.poll()
        state.poll()
        assert state.request_result(identity)["status"] == "APPLIED"
    finally:
        state.close()


def test_database_cannot_be_reused_for_a_different_account(tmp_path: Path) -> None:
    config = file_config(tmp_path)
    state = FileState(config)
    seed(state)
    state.close()
    with pytest.raises(ValueError, match="different EA identity"):
        FileState(replace(config, ea_account="other-account"))
    original = FileState(config)
    try:
        assert original.read("SettingsData")["version"] == 7
    finally:
        original.close()


def test_two_connections_reserve_only_one_config_version(tmp_path: Path) -> None:
    first = FileState(file_config(tmp_path))
    seed(first)
    second = FileState(file_config(tmp_path))
    body = {
        "base_version": 7,
        "values": {**first.read("SettingsData")["values"], "maxSpread": 30},
    }

    def accept(state: FileState) -> str:
        try:
            return state.accept("/settings/apply", str(uuid4()), body)["data"]["status"]  # type: ignore[no-any-return]
        except ApiFault as exc:
            assert exc.status == 409
            return "CONFLICT"

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(accept, [first, second]))
        assert sorted(results) == ["CONFLICT", "PENDING"]
        assert len(first.repository.pending_writes()) == 1
        first.repository.verify_audit()
    finally:
        second.close()
        first.close()


def test_failed_migration_rolls_back_schema_and_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "migration.sqlite"
    with monkeypatch.context() as patch:
        patch.setattr(
            storage, "MIGRATION", storage.MIGRATION + "INSERT INTO missing_table VALUES(1);"
        )
        with pytest.raises(sqlite3.OperationalError):
            Repository(path)
    with closing(sqlite3.connect(path)) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 0
        assert not connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    repository = Repository(path)
    try:
        assert repository.connection.execute("PRAGMA user_version").fetchone()[0] == 2
    finally:
        repository.close()
