import time

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from aurum_backend.security.tickets import Tickets

from .conftest import ORIGIN


def test_ticket_one_use_expiry_and_origin_binding() -> None:
    tickets = Tickets(lifetime=0.01)
    token = tickets.issue(ORIGIN)
    assert tickets.consume(token, ORIGIN)
    assert not tickets.consume(token, ORIGIN)
    wrong = tickets.issue(ORIGIN)
    assert not tickets.consume(wrong, "https://evil.example")
    expired = tickets.issue(ORIGIN)
    time.sleep(0.02)
    assert not tickets.consume(expired, ORIGIN)


def test_ticket_requires_bearer_and_trusted_origin(client: TestClient) -> None:
    path = "/api/v2/session/ws-ticket"
    assert client.post(path, headers={"Authorization": "", "Origin": ORIGIN}).status_code == 401
    assert client.post(path).status_code == 403
    assert client.post(path, headers={"Origin": "https://evil.example"}).status_code == 403
    response = client.post(path, headers={"Origin": ORIGIN})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["data"]["expires_in_seconds"] == 10


def test_browser_authenticates_without_token_in_url(client: TestClient) -> None:
    ticket = client.post("/api/v2/session/ws-ticket", headers={"Origin": ORIGIN}).json()["data"][
        "ticket"
    ]
    # TestClient otherwise inherits its default Authorization; remove it explicitly.
    client.headers.pop("authorization")
    with client.websocket_connect("ws://127.0.0.1:8765/ws", headers={"Origin": ORIGIN}) as socket:
        socket.send_json({"type": "authenticate", "ticket": ticket})
        assert socket.receive_json()["type"] == "heartbeat"
    with client.websocket_connect("ws://127.0.0.1:8765/ws", headers={"Origin": ORIGIN}) as socket:
        socket.send_json({"type": "authenticate", "ticket": ticket})
        with pytest.raises(WebSocketDisconnect) as disconnected:
            socket.receive_json()
        assert disconnected.value.code == 1008
