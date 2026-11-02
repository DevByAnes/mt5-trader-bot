"""Fixture/FILE application factory and loopback-only launcher."""

import asyncio
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

import uvicorn
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from aurum_backend.api import dev, routes, session
from aurum_backend.api.envelope import error_response
from aurum_backend.api.errors import ApiFault
from aurum_backend.core.config import Config
from aurum_backend.core.logging import configure_logging, log_event
from aurum_backend.core.resources import OPENAPI
from aurum_backend.fixtures.state import FixtureState
from aurum_backend.realtime.stream import pump
from aurum_backend.realtime.stream import router as realtime_router
from aurum_backend.security.access import SecurityMiddleware
from aurum_backend.security.tickets import Tickets
from aurum_backend.services.file_state import FileState


def create_app(config: Config | None = None) -> FastAPI:
    settings = config or Config.from_env()
    state = FileState(settings) if settings.backend_mode == "file" else FixtureState(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        task = asyncio.create_task(pump(state), name="bridge-pump")
        log_event("backend_started")
        try:
            yield
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
            state.overloaded.update(state.subscribers)
            if isinstance(state, FileState):
                state.close()
            log_event("backend_stopped")

    app = FastAPI(
        title="Aurum local bridge",
        lifespan=lifespan,
        openapi_url=None,
        docs_url=None,
        redoc_url=None,
    )
    app.state.fixture_state = state
    app.state.config = settings
    app.state.socket_tickets = Tickets()
    app.include_router(routes.router)
    app.include_router(realtime_router)
    app.include_router(session.router)
    if settings.environment == "development" and settings.backend_mode == "fixture":
        app.include_router(dev.router)

    @app.exception_handler(ApiFault)
    async def api_error(request: Request, exc: ApiFault) -> JSONResponse:
        return error_response(exc.status, exc.code, exc.message, exc.field)

    @app.exception_handler(RequestValidationError)
    @app.exception_handler(ValidationError)
    async def invalid(request: Request, exc: Exception) -> JSONResponse:
        return error_response(422, "VALIDATION_ERROR", "Request violates frozen schema")

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        if exc.status_code == 405:
            response = error_response(405, "VALIDATION_ERROR", "Method not allowed")
            if exc.headers:
                response.headers.update(exc.headers)
            return response
        return error_response(
            404 if exc.status_code == 404 else 400,
            "NOT_FOUND" if exc.status_code == 404 else "VALIDATION_ERROR",
            "Resource not found" if exc.status_code == 404 else "Unsupported request",
        )

    @app.exception_handler(Exception)
    async def internal(request: Request, exc: Exception) -> JSONResponse:
        log_event("internal_failure", status=503)
        return error_response(503, "UNAVAILABLE", "Service temporarily unavailable")

    app.add_middleware(SecurityMiddleware, config=settings)
    # Consumers use the immutable source, never FastAPI's inferred DTO schema.
    app.openapi = lambda: OPENAPI  # type: ignore[method-assign]
    return app


def run() -> None:
    if len(sys.argv) != 1:
        raise SystemExit(
            "No CLI arguments supported; use documented environment/stdin configuration"
        )
    configure_logging()
    try:
        config = Config.from_env()
    except ValueError:
        raise SystemExit("Invalid configuration or missing session token") from None
    uvicorn.run(
        create_app(config),
        host="127.0.0.1",
        port=8765,
        workers=1,
        proxy_headers=False,
        access_log=False,
        log_level="critical",
        ws="websockets-sansio",
        ws_max_size=config.max_body_bytes,
        timeout_graceful_shutdown=5,
    )


if __name__ == "__main__":
    run()
