"""Additive, authenticated read-only forward-test report, separate from frozen v1."""

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from aurum_backend.api.deps import fixture_state
from aurum_backend.api.envelope import envelope
from aurum_backend.api.errors import ApiFault
from aurum_backend.services.file_state import FileState
from aurum_backend.storage.forward import report

router = APIRouter(prefix="/api/v2/forward-test")


@router.get("")
@router.get("/export")
async def forward_report(request: Request) -> JSONResponse:
    if request.query_params:
        raise ApiFault("VALIDATION_ERROR", "This report accepts no query parameters")
    state = fixture_state(request)
    if not isinstance(state, FileState):
        raise ApiFault("UNAVAILABLE", "Forward recording requires real FILE mode", 503)
    export = request.url.path.endswith("/export")
    async with state.lock:
        with state.repository.lock:
            value = report(state.repository.connection, export=export)
    return JSONResponse(envelope(value))
