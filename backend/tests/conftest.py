from collections.abc import Iterator

import pytest
from starlette.testclient import TestClient

from aurum_backend.core.config import Config
from aurum_backend.main import create_app

TOKEN = "fixture-test-session-token-at-least-32-chars"  # noqa: S105
HEADERS = {"Authorization": "Bearer " + TOKEN}
ORIGIN = "http://127.0.0.1:1420"


def client_for(**options: object) -> TestClient:
    return TestClient(
        create_app(Config(token=TOKEN, **options)),  # type: ignore[arg-type]
        base_url="http://127.0.0.1:8765",
        headers=HEADERS,
        client=("127.0.0.1", 50000),
        raise_server_exceptions=False,
    )


@pytest.fixture
def client() -> Iterator[TestClient]:
    with client_for(ack_seconds=0.01, heartbeat_seconds=0.05, requests_per_minute=100000) as value:
        yield value
