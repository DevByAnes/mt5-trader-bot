# Phase 0 — checked 2026-11-02

Official package releases were checked on PyPI (including JSON release metadata) and Python.org. Exact selected packages are frozen in `uv.lock`; this is not a claim that newer versions cannot appear after this date.

| Tool | Current stable observed | Selection / important point |
|---|---|---|
| [Python](https://www.python.org/downloads/) | 3.15.2 | Test runtime 3.14.10 (maintained bugfix branch, broader wheel compatibility); requires 3.12–3.15, only 3.14.10 verified |
| [FastAPI](https://pypi.org/project/fastapi/) | 0.162.0 | Pinned; app lifespan owns simulation pump |
| [Pydantic](https://pypi.org/project/pydantic/) | 2.14.2 | Pinned v2; generated strict models plus authoritative JSON Schema validation |
| [Uvicorn](https://pypi.org/project/uvicorn/) | 0.54.0 | Pinned; asyncio/WebSocket SansIO, one loopback worker; proxy headers disabled |
| [uv](https://pypi.org/project/uv/) | 0.13.6 | Managed Python + frozen universal lock |
| [Ruff](https://pypi.org/project/ruff/) | 0.17.3 | Pinned; standard lint plus a separate whole-src no-execution lint |
| [mypy](https://pypi.org/project/mypy/) | 2.4.1 | Pinned strict with Pydantic plugin; tools/tests included |
| [pytest](https://pypi.org/project/pytest/) | 9.2.0 | Pinned; real HTTP fuzz server and lifecycle tests |
| [Hypothesis](https://pypi.org/project/hypothesis/) | 6.170.14 | Pinned; schema alignment properties and fuzzing |
| [Schemathesis](https://pypi.org/project/schemathesis/) | 4.33.0 | Pinned; all 17 frozen operations tested; six semantic-422 overrides documented |
| [datamodel-code-generator](https://pypi.org/project/datamodel-code-generator/) | 0.87.0 | Pinned Pydantic v2 target; deterministic regeneration for both schemas |

Intentionally unused: Pydantic v1 APIs (`parse_obj`, legacy `Config` and `@validator`), deprecated FastAPI startup/shutdown decorators ([lifespan guidance](https://fastapi.tiangolo.com/advanced/events/)), legacy WebSocket backend, wildcard CORS, proxy-trusted public binding and runtime-inferred OpenAPI. The installed Starlette TestClient deprecates HTTPX 0.x: HTTPX2 2.16.0 is used for that test transport; HTTPX remains a Schemathesis/tool dependency. No EA/MT5 SDK or persistence package is introduced.
