import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from uuid import uuid4

import pytest
from starlette.testclient import TestClient

from aurum_backend.core.resources import OPENAPI
from aurum_backend.fixtures.loader import FixtureLoader
from aurum_backend.fixtures.state import READS
from aurum_backend.models.base import validate_schema


def draft(client: TestClient, **changes: Any) -> dict[str, Any]:
    data = client.get("/api/v1/settings").json()["data"]
    return {"base_version": data["version"], "values": {**data["values"], **changes}}


def post(client: TestClient, path: str, body: Any, key: str | None = None) -> Any:
    return client.post(
        "/api/v1" + path, json=body, headers={"Idempotency-Key": key or str(uuid4())}
    )


def resolve(client: TestClient, identity: str) -> dict[str, Any]:
    for _ in range(100):
        response = client.get("/api/v1/requests/" + identity)
        assert response.status_code == 200, response.text
        data = response.json()["data"]
        if data["status"] != "PENDING":
            return data  # type: ignore[no-any-return]
        time.sleep(0.01)
    pytest.fail("Simulated acknowledgement never resolved")


@pytest.mark.parametrize("path,name", READS.items())
def test_read_contract_and_fixtures(client: TestClient, path: str, name: str) -> None:
    response = client.get("/api/v1" + path)
    assert response.status_code == 200, response.text
    body = response.json()
    validate_schema(name + "Envelope", body)
    fixture = FixtureLoader().data(name)
    if name == "Status":
        for key in ["backend", "ea", "mt5"]:
            assert body["data"][key]["state"] == fixture[key]["state"]
            assert body["data"][key]["latency_ms"] == fixture[key]["latency_ms"]
            assert body["data"][key]["heartbeat_utc"].endswith("Z")
    elif name == "DailyRisk":
        fixture["next_day_utc"] = body["data"]["next_day_utc"]
        assert body["data"] == fixture
    else:
        assert body["data"] == fixture
    assert response.headers["X-Aurum-Mode"] == "fixture"
    assert response.headers["Cache-Control"] == "no-store"


def test_every_frozen_operation_is_reachable(client: TestClient) -> None:
    paths: Any = OPENAPI["paths"]
    for path, operations in paths.items():
        for method in operations:
            url = path.replace("{id}", "audit-7" if "audit" in path else "missing")
            url = url.replace("{command}", "kill-switch")
            kwargs: dict[str, Any] = {}
            if method == "post":
                kwargs["headers"] = {"Idempotency-Key": str(uuid4())}
                if "settings" in path:
                    kwargs["json"] = draft(client, maxSpread=30)
                elif "commands" in path:
                    kwargs["json"] = {}
            response = client.request(method, "/api/v1" + url, **kwargs)
            assert response.status_code in {200, 202, 404, 409}, response.text
            if response.status_code == 404:
                assert path == "/requests/{id}"


def test_diff_and_readonly_rollback(client: TestClient) -> None:
    proposed = draft(client, maxSpread=30)
    response = post(client, "/settings/validate", proposed)
    assert response.status_code == 200
    assert response.json()["data"] == FixtureLoader().data("Diff")
    before = client.get("/api/v1/settings").json()["data"]
    rollback = client.post("/api/v1/audit/audit-7/rollback")
    assert rollback.status_code == 200
    assert rollback.json()["data"] == FixtureLoader().data("Diff")
    assert client.get("/api/v1/settings").json()["data"] == before
    accepted = post(client, "/settings/apply", proposed)
    assert accepted.status_code == 202
    assert accepted.json()["data"]["status"] == "PENDING"
    result = resolve(client, accepted.json()["data"]["request_id"])
    assert result["status"] == "APPLIED" and result["ea_ack_utc"].endswith("Z")
    assert client.get("/api/v1/settings").json()["data"]["version"] == before["version"] + 1
    assert (
        client.get("/api/v1/audit").json()["data"]["items"][0]["previous_values"]
        == before["values"]
    )


def test_idempotency_exact_replay_and_canonical_payload(client: TestClient) -> None:
    key = str(uuid4())
    body = draft(client, maxSpread=30)
    first = post(client, "/settings/apply", body, key)
    repeat = post(client, "/settings/apply", dict(reversed(list(body.items()))), key)
    assert first.status_code == repeat.status_code == 202
    assert first.content == repeat.content
    resolve(client, key)
    assert post(client, "/settings/apply", body, key).content == first.content
    mismatch = post(client, "/settings/apply", {**body, "base_version": 8}, key)
    assert mismatch.status_code == 409
    assert mismatch.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"
    assert post(client, "/commands/kill-switch", {}, key).status_code == 409


def test_atomic_concurrent_version_reservation(client: TestClient) -> None:
    body = draft(client, maxSpread=30)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda _: post(client, "/settings/apply", body).status_code, range(2))
        )
    assert sorted(results) == [202, 409]


@pytest.mark.parametrize(
    "changes,code",
    [
        ({"allowRealAccount": True}, "MT5_ONLY"),
        ({"allowRemoteConfig": False}, "MT5_ONLY"),
        ({"executionMode": "LIVE"}, "LIVE_LOCKED"),
        ({"maxSpread": 101}, "VALIDATION_ERROR"),
        ({"riskPerTrade": 0.15}, "VALIDATION_ERROR"),
        ({"riskPerTrade": True}, "VALIDATION_ERROR"),
        ({"maxSpread": "30"}, "VALIDATION_ERROR"),
    ],
)
def test_validation_and_locks(client: TestClient, changes: dict[str, Any], code: str) -> None:
    response = post(client, "/settings/validate", draft(client, **changes))
    assert response.status_code in {403, 422}
    assert response.json()["error"]["code"] == code


def test_pagination_stability_and_unknown_queries(client: TestClient) -> None:
    first = client.get("/api/v1/signals?limit=1").json()["data"]
    assert len(first["items"]) == 1 and first["next_cursor"]
    second = client.get("/api/v1/signals", params={"cursor": first["next_cursor"], "limit": 1})
    assert second.status_code == 200
    assert second.json()["data"]["items"][0]["id"] != first["items"][0]["id"]
    assert second.json()["data"]["next_cursor"] is None
    cases: list[dict[str, str | int]] = [
        {"limit": 0},
        {"limit": 101},
        {"limit": "1.5"},
        {"sort": "price"},
        {"cursor": "not-base64"},
        {"cursor": first["next_cursor"], "limit": "x"},
    ]
    for params in cases:
        response = client.get("/api/v1/signals", params=params)
        assert response.status_code == 422
        validate_schema("ErrorEnvelope", response.json())
    assert client.get("/api/v1/journal", params={"cursor": first["next_cursor"]}).status_code == 422


@pytest.mark.parametrize(
    "path,body",
    [
        ("/commands/risk-free-position", {}),
        ("/commands/close-position", {"position_id": "missing"}),
    ],
)
def test_position_command_requirements(client: TestClient, path: str, body: dict[str, str]) -> None:
    assert post(client, path, body).status_code in {404, 422}


def test_command_simulates_only_local_state(client: TestClient) -> None:
    result = post(client, "/commands/kill-switch", {})
    assert resolve(client, result.json()["data"]["request_id"])["status"] == "APPLIED"
    assert client.get("/api/v1/ea/state").json()["data"]["risk_active"] is False
    assert client.get("/api/v1/risk/daily").json()["data"]["reason"] == "OPERATOR_HALT"


def test_unavailable_never_becomes_zero(client: TestClient) -> None:
    client.post("/__dev/scenario", json={"scenario": "ea-offline"})
    node = client.get("/api/v1/status").json()["data"]["ea"]
    assert node == {"state": "offline", "heartbeat_utc": None, "latency_ms": None}
