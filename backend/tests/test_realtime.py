import asyncio
import time
from typing import Any

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from aurum_backend.core.config import Config
from aurum_backend.fixtures.state import FixtureState
from aurum_backend.models.base import validate_schema
from aurum_backend.realtime.stream import send_event

from .conftest import HEADERS, ORIGIN, TOKEN, client_for
from .test_http import draft, post


def frames(socket: Any) -> list[dict[str, Any]]:
    result = [socket.receive_json() for _ in range(7)]
    for value in result:
        validate_schema("Event", value)
    return result


def test_reconnect_replays_telemetry_and_rest_full_snapshot(client: TestClient) -> None:
    for _ in range(2):
        with client.websocket_connect(
            "ws://127.0.0.1:8765/ws", headers={**HEADERS, "Origin": ORIGIN}
        ) as socket:
            initial = frames(socket)
            assert [e["seq"] for e in initial] == list(range(1, 8))
            assert {e["type"] for e in initial} == {
                "heartbeat",
                "ea_state",
                "position",
                "risk_mode",
                "signal",
                "log",
            }
            assert client.get("/api/v1/settings").status_code == 200
            assert client.get("/api/v1/chart").status_code == 200
            assert client.get("/api/v1/audit").status_code == 200
    for _ in range(50):
        if not client.app.state.fixture_state.subscribers:  # type: ignore[attr-defined]
            break
        time.sleep(0.01)
    assert not client.app.state.fixture_state.subscribers  # type: ignore[attr-defined]


def test_realtime_ack_correlated_and_all_event_types(client: TestClient) -> None:
    with client.websocket_connect("ws://127.0.0.1:8765/ws", headers=HEADERS) as socket:
        initial = frames(socket)
        accepted = post(client, "/commands/kill-switch", {}).json()["data"]
        seen = list(initial)
        while not any(e["type"] == "command_ack" for e in seen):
            seen.append(socket.receive_json())
        ack = next(e for e in seen if e["type"] == "command_ack")
        validate_schema("Event", ack)
        assert ack["payload"]["request_id"] == accepted["request_id"]
        assert ack["payload"]["status"] == "APPLIED" and ack["payload"]["ea_ack_utc"]
        seqs = [e["seq"] for e in seen]
        assert seqs == list(range(1, len(seqs) + 1))
        accepted_config = post(client, "/settings/apply", draft(client, maxSpread=30)).json()[
            "data"
        ]
        while not any(e["type"] == "config_ack" for e in seen):
            seen.append(socket.receive_json())
        config_ack = next(e for e in seen if e["type"] == "config_ack")
        validate_schema("Event", config_ack)
        assert config_ack["payload"]["request_id"] == accepted_config["request_id"]
        assert {e["type"] for e in seen} == {
            "ea_state",
            "position",
            "signal",
            "risk_mode",
            "log",
            "command_ack",
            "config_ack",
            "heartbeat",
        }


def test_seq_gap_scenario_recovery(client: TestClient) -> None:
    client.post("/__dev/scenario", json={"scenario": "seq-gap"})
    with client.websocket_connect("ws://127.0.0.1:8765/ws", headers=HEADERS) as socket:
        initial = frames(socket)
        next_event = socket.receive_json()
        assert next_event["seq"] == initial[-1]["seq"] + 2
    assert client.get("/api/v1/status").status_code == 200


def test_abrupt_connections_release_resources(client: TestClient) -> None:
    for _ in range(15):
        with client.websocket_connect("ws://127.0.0.1:8765/ws", headers=HEADERS) as socket:
            socket.receive_json()
    time.sleep(0.05)
    state: Any = client.app.state.fixture_state  # type: ignore[attr-defined]
    assert not state.subscribers and not state.overloaded


def test_invalid_client_frames_disconnect(client: TestClient) -> None:
    with client.websocket_connect("ws://127.0.0.1:8765/ws", headers=HEADERS) as socket:
        frames(socket)
        socket.send_text("not part of protocol")
        with pytest.raises(WebSocketDisconnect) as disconnected:
            while True:
                socket.receive_json()
        assert disconnected.value.code == 1008


def test_queue_backpressure_is_bounded() -> None:
    state = FixtureState(Config(token=TOKEN, queue_size=2))
    slow = state.subscribe()
    for _ in range(100):
        state.publish("heartbeat", state.read("Status"))
    assert slow.qsize() == 2 and slow in state.overloaded
    state.unsubscribe(slow)
    assert not state.subscribers and not state.overloaded


def test_full_client_queue_really_disconnects() -> None:
    with client_for(queue_size=2) as client:
        with client.websocket_connect("ws://127.0.0.1:8765/ws", headers=HEADERS) as socket:
            frames(socket)
            state: Any = client.app.state.fixture_state  # type: ignore[attr-defined]

            def overload() -> None:
                for _ in range(100):
                    state.publish("heartbeat", state.read("Status"))

            assert client.portal is not None
            client.portal.call(overload)
            with pytest.raises(WebSocketDisconnect) as disconnected:
                while True:
                    socket.receive_json()
            assert disconnected.value.code == 1013


def test_slow_network_write_times_out_without_blocking_other_clients() -> None:
    class SlowSocket:
        async def send_json(self, value: Any) -> None:
            await asyncio.sleep(60)

    async def run() -> None:
        state = FixtureState(Config(token=TOKEN, send_timeout=0.01))
        with pytest.raises(TimeoutError):
            await send_event(SlowSocket(), state, "heartbeat", state.read("Status"), 1)  # type: ignore[arg-type]

    asyncio.run(run())


def test_scenario_switch_disconnects_streams() -> None:
    with client_for(heartbeat_seconds=0.01) as client:
        with client.websocket_connect("ws://127.0.0.1:8765/ws", headers=HEADERS) as socket:
            frames(socket)
            client.post("/__dev/scenario", json={"scenario": "python-offline"})
            with pytest.raises(WebSocketDisconnect) as disconnected:
                while True:
                    socket.receive_json()
            assert disconnected.value.code == 1013
