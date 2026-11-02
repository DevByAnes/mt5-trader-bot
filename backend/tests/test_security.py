import json
from typing import Any

import pytest
from starlette.requests import Request
from starlette.testclient import TestClient, WebSocketDenialResponse

from aurum_backend.core.config import Config
from aurum_backend.main import create_app
from aurum_backend.models.base import validate_schema

from .conftest import HEADERS, ORIGIN, TOKEN, client_for


@pytest.mark.parametrize("authorization", ["", "Bearer wrong", "Basic abc", "Bearer é"])
def test_token_required(client: TestClient, authorization: str) -> None:
    # TestClient/httpx prohibits non-ASCII header strings; bytes preserve the attack case.
    response = client.get("/api/v1/status", headers={b"authorization": authorization.encode()})
    assert response.status_code == 401
    validate_schema("ErrorEnvelope", response.json())
    assert response.json()["data"] is None
    assert TOKEN not in response.text


def test_closed_origins_and_cors_preflight(client: TestClient) -> None:
    good = client.get("/api/v1/status", headers={"Origin": ORIGIN})
    assert good.status_code == 200 and good.headers["access-control-allow-origin"] == ORIGIN
    for origin in ["https://evil.example", "null", ORIGIN + ".evil.example"]:
        bad = client.get("/api/v1/status", headers={"Origin": origin})
        assert bad.status_code == 403 and "access-control-allow-origin" not in bad.headers
        validate_schema("ErrorEnvelope", bad.json())
    response = client.options(
        "/api/v1/settings/apply",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type,idempotency-key",
        },
    )
    assert response.status_code == 204 and response.content == b""
    assert response.headers["access-control-allow-origin"] == ORIGIN
    bad = client.options(
        "/api/v1/status", headers={"Origin": ORIGIN, "Access-Control-Request-Method": "DELETE"}
    )
    assert bad.status_code == 403


def test_bind_perimeter_and_no_proxy_trust() -> None:
    app = create_app(Config(token=TOKEN))
    with TestClient(
        app, base_url="http://127.0.0.1:8765", headers=HEADERS, client=("192.0.2.1", 50000)
    ) as client:
        assert client.get("/api/v1/status").status_code == 403
    with client_for() as client:
        assert client.get("/api/v1/status", headers={"Host": "evil.example"}).status_code == 403
        assert (
            client.get("/api/v1/status", headers={"X-Forwarded-For": "192.0.2.1"}).status_code
            == 200
        )


def test_rate_limit_is_bounded_and_contract_shaped() -> None:
    with client_for(requests_per_minute=2) as client:
        assert client.get("/api/v1/status").status_code == 200
        assert client.get("/api/v1/status").status_code == 200
        response = client.get("/api/v1/status")
        assert response.status_code == 503 and response.headers["retry-after"] == "60"
        validate_schema("ErrorEnvelope", response.json())
        assert response.json()["error"]["code"] == "UNAVAILABLE"


def test_internal_fault_is_sanitized() -> None:
    app = create_app(Config(token=TOKEN))

    @app.get("/injected-fault")
    async def fault(request: Request) -> Any:
        raise RuntimeError("secret stack detail " + TOKEN)

    with TestClient(
        app,
        base_url="http://127.0.0.1:8765",
        headers=HEADERS,
        client=("127.0.0.1", 50000),
        raise_server_exceptions=False,
    ) as client:
        response = client.get("/injected-fault")
        assert response.status_code == 503
        validate_schema("ErrorEnvelope", response.json())
        assert "secret" not in response.text and TOKEN not in response.text


def test_payload_validation_and_size(client: TestClient) -> None:
    for body in [
        b'{"position_id":null}',
        b'{"extra":1}',
        b'{"x":1,"x":2}',
        b'{"position_id":NaN}',
        b"not json",
        b'"abc"',
    ]:
        response = client.post(
            "/api/v1/commands/kill-switch",
            content=body,
            headers={
                "Content-Type": "application/json",
                "Idempotency-Key": "2a520cb7-bade-486a-a864-d6324f72c10a",
            },
        )
        assert response.status_code == 422, response.text
    response = client.post("/api/v1/settings/apply", json={})
    assert response.status_code == 422
    assert client.get("/api/v1/status?unknown=1").status_code == 422
    with client_for(max_body_bytes=20) as limited:
        response = limited.post(
            "/api/v1/commands/kill-switch", content=json.dumps({"x": "a" * 100})
        )
        assert response.status_code == 422


def test_config_no_secret_repr_or_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    assert TOKEN not in repr(Config(token=TOKEN))
    monkeypatch.delenv("AURUM_SESSION_TOKEN", raising=False)
    monkeypatch.delenv("AURUM_TOKEN_STDIN", raising=False)
    with pytest.raises(ValueError, match="Session token"):
        Config.from_env()
    with pytest.raises(ValueError, match="development-only"):
        Config(token=TOKEN, environment="production", scenario="stale")
    with pytest.raises(ValueError, match="explicit"):
        Config(token=TOKEN, origins=("*",))


def test_websocket_rejects_missing_token_and_query_tokens(client: TestClient) -> None:
    with pytest.raises(WebSocketDenialResponse) as denied:
        with client.websocket_connect("ws://127.0.0.1:8765/ws", headers={"Authorization": ""}):
            pytest.fail("Unauthenticated socket accepted")
    assert denied.value.status_code == 401
    validate_schema("ErrorEnvelope", denied.value.json())
    with pytest.raises(WebSocketDenialResponse) as query_denied:
        with client.websocket_connect("ws://127.0.0.1:8765/ws?token=forbidden", headers=HEADERS):
            pytest.fail("URL credential accepted")
    assert query_denied.value.status_code == 422
    with pytest.raises(WebSocketDenialResponse) as origin_denied:
        with client.websocket_connect(
            "ws://127.0.0.1:8765/ws", headers={**HEADERS, "Origin": "https://evil.example"}
        ):
            pytest.fail("Foreign origin accepted")
    assert origin_denied.value.status_code == 403
