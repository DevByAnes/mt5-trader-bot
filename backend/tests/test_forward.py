from copy import deepcopy
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from aurum_backend.bridge.codec import json_bytes
from aurum_backend.main import create_app
from aurum_backend.services.file_state import FileState
from aurum_backend.storage.forward import report
from tools.dashboard import create_dashboard

from .conftest import HEADERS, TOKEN
from .test_bridge_file import file_config, message


def test_forward_restart_dedup_gap_and_drawdown(tmp_path: Path) -> None:
    config = file_config(tmp_path)
    state = FileState(config)
    payload = message(issued_ms=1793613600000)
    resources = payload["body"]["resources"]
    resources["EaState"]["equity"] = 100
    resources["EaState"]["account_currency"] = "USD"
    assert state.repository.receive(payload, "first")
    assert not state.repository.receive(payload, "first")
    before = report(state.repository.connection)
    assert before["samples"] == 1
    assert before["decisions"] == len(resources["Signals"]["items"])
    second = deepcopy(payload)
    second.update(message_id="second", seq=2, issued_at_ms=1793613900000)
    second["body"]["resources"]["EaState"]["equity"] = 90
    state.repository.receive(second, "second")
    state.close()
    state = FileState(config)
    try:
        result = report(state.repository.connection, export=True)
        assert result["samples"] == 2
        assert result["decisions"] == before["decisions"]
        assert result["sample_gaps_over_3_minutes"] == 1
        assert result["sampled_max_drawdown_percent"] == 10
        assert result["target_end_utc"] == "2026-11-09T10:00:00+00:00"
        assert len(result["records"]["samples"]) == 2
        encoded = json_bytes(result)
        assert b"demo-123" not in encoded
        assert b"hmac_sha256" not in encoded
    finally:
        state.close()


def test_rejected_snapshot_not_recorded_and_api_auth(tmp_path: Path) -> None:
    app = create_app(file_config(tmp_path))
    state = app.state.fixture_state
    payload = message()
    wire = bytearray(state.codec.encode(payload))
    wire[-10] ^= 1
    state.files.write("state.json", bytes(wire))
    state.poll()
    assert report(state.repository.connection)["samples"] == 0
    with TestClient(app, base_url="http://127.0.0.1:8765", client=("127.0.0.1", 50000)) as client:
        assert client.get("/api/v2/forward-test").status_code == 401
        response = client.get("/api/v2/forward-test", headers=HEADERS)
        assert response.status_code == 200
        assert response.json()["data"]["samples"] == 0
        assert client.get("/api/v2/forward-test?x=1", headers=HEADERS).status_code == 422


def test_built_dashboard_bootstrap_and_static_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "index.html").write_text("<main>Aurum</main>", encoding="utf-8")
    monkeypatch.setenv("AURUM_LOCAL_DEV", "1")
    monkeypatch.setenv("AURUM_SESSION_TOKEN", TOKEN)
    with TestClient(
        create_dashboard(tmp_path), base_url="http://127.0.0.1:1420",
        client=("127.0.0.1", 50001)
    ) as client:
        assert client.get("/overview").status_code == 200
        assert TOKEN not in client.get("/overview").text
        assert client.get("/missing.js").status_code == 404
        assert client.post("/__aurum/session").status_code == 403
        headers = {
            "Origin": "http://127.0.0.1:1420", "Sec-Fetch-Site": "same-origin",
            "X-Aurum-Session": "1",
        }
        response = client.post("/__aurum/session", headers=headers)
        assert response.json()["token"] == TOKEN
        assert response.headers["cache-control"] == "no-store"
        headers["Origin"] = "https://attacker.example"
        assert client.post("/__aurum/session", headers=headers).status_code == 403
        assert client.get("/overview", headers={"Host": "attacker.example"}).status_code == 403
