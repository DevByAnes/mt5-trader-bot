"""Actual HTTP fuzzing of every frozen operation with positive/negative cases."""

import socket
import threading
import time
from collections.abc import Iterator
from typing import Any

import pytest
import schemathesis
import uvicorn
from hypothesis import HealthCheck, settings

from aurum_backend.core.config import Config
from aurum_backend.core.resources import OPENAPI
from aurum_backend.main import create_app

from .conftest import HEADERS, TOKEN

# Opaque cursors and command-specific position requirements are semantic constraints not
# representable by the current frozen parameter schemas (CCP-06). Only those six operations
# allow the documented semantic 422 in the positive-acceptance check. All response-schema,
# negative-input, server-error and authentication checks remain enabled.
semantic_operations = [
    "GET /signals",
    "GET /journal",
    "GET /validation",
    "GET /logs",
    "GET /audit",
    "POST /commands/{command}",
]
config = schemathesis.Config.from_dict(
    {
        "operations": [
            {
                "include-name": name,
                "checks": {
                    "positive_data_acceptance": {
                        "expected-statuses": ["2xx", "3xx", 401, 403, 404, 409, 422, 429, "5xx"]
                    }
                },
            }
            for name in semantic_operations
        ]
    }
)
schema = schemathesis.openapi.from_dict(OPENAPI, config=config)


@pytest.fixture(scope="module")
def live_url() -> Iterator[str]:
    # Real loopback listener: exercises the same host/peer checks as the executable.
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    config = Config(token=TOKEN, requests_per_minute=100000, ack_seconds=0)
    server = uvicorn.Server(
        uvicorn.Config(
            create_app(config),
            access_log=False,
            log_level="critical",
            proxy_headers=False,
            ws="websockets-sansio",
        )
    )
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    try:
        for _ in range(100):
            if server.started:
                break
            if not thread.is_alive():
                pytest.fail("Loopback server stopped during startup")
            time.sleep(0.02)
        assert server.started
        yield f"http://127.0.0.1:{port}/api/v1"
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        listener.close()
        assert not thread.is_alive()


@schema.parametrize()
@settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_frozen_openapi(case: Any, live_url: str) -> None:
    case.call_and_validate(base_url=live_url, headers=HEADERS)
