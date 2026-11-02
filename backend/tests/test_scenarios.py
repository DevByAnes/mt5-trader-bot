from typing import Any

import pytest
from starlette.testclient import TestClient

from aurum_backend.core.config import SCENARIOS
from aurum_backend.models.base import validate_schema

from .conftest import client_for
from .test_http import draft, post, resolve


def test_dev_routes_absent_in_production() -> None:
    with client_for(environment="production") as client:
        response = client.post("/__dev/scenario", json={"scenario": "normal"})
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_all_scenarios_selectable(client: TestClient, scenario: str) -> None:
    selected = client.post("/__dev/scenario", json={"scenario": scenario})
    assert selected.status_code == 200
    assert selected.json()["data"]["scenario"] == scenario
    response = client.get("/api/v1/status")
    if scenario in {"python-offline", "bridge-offline"}:
        assert response.status_code == 503
        validate_schema("ErrorEnvelope", response.json())
        return
    assert response.status_code == 200
    if scenario == "stale":
        assert response.json()["data"]["backend"]["state"] == "stale"
    if scenario == "ea-offline":
        assert post(client, "/commands/kill-switch", {}).json()["error"]["code"] == "EA_OFFLINE"
    if scenario.startswith("daily-"):
        risk = client.get("/api/v1/risk/daily").json()["data"]
        assert risk["state"] == "STOPPED" and risk["reason"] == scenario.upper()
    if scenario == "wide-spread":
        assert client.get("/api/v1/ea/state").json()["data"]["spread"] == 65
    if scenario in {"no-positions", "multi-positions"}:
        assert len(client.get("/api/v1/positions").json()["data"]) == (
            0 if scenario == "no-positions" else 2
        )


@pytest.mark.parametrize(
    "scenario,outcome",
    [("ack-applied", "APPLIED"), ("ack-rejected", "REJECTED"), ("ack-timeout", "TIMEOUT")],
)
def test_simulated_ack_does_not_prematurely_change_values(
    client: TestClient, scenario: str, outcome: str
) -> None:
    client.post("/__dev/scenario", json={"scenario": scenario})
    body = draft(client, maxSpread=30)
    response = post(client, "/settings/apply", body)
    assert response.status_code == 202 and response.json()["data"]["status"] == "PENDING"
    result = resolve(client, response.json()["data"]["request_id"])
    assert result["status"] == outcome
    current = client.get("/api/v1/settings").json()["data"]
    if outcome == "APPLIED":
        assert current["values"] == body["values"] and result["ea_ack_utc"]
    else:
        assert current["values"]["maxSpread"] == 35 and result["ea_ack_utc"] is None
    if outcome == "TIMEOUT":
        assert post(client, "/settings/apply", body).status_code == 409


def test_scenario_env_and_invalid_control(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from aurum_backend.core.config import Config

    from .conftest import TOKEN

    monkeypatch.setenv("AURUM_SESSION_TOKEN", TOKEN)
    monkeypatch.setenv("AURUM_SCENARIO", "no-positions")
    assert Config.from_env().scenario == "no-positions"
    for body in [{"scenario": "unknown"}, {"scenario": "normal", "extra": 1}, [], None]:
        response = client.post("/__dev/scenario", json=body)
        assert response.status_code == 422
    payload: dict[str, Any] = {"base_version": 7, "values": draft(client)["values"]}
    client.post("/__dev/scenario", json={"scenario": "version-conflict"})
    assert post(client, "/settings/validate", payload).status_code == 409
