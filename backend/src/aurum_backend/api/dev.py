"""Separate development harness explicitly requested for B1; never production routes."""

import json

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from aurum_backend.api.deps import fixture_state
from aurum_backend.api.envelope import envelope
from aurum_backend.api.errors import ApiFault

router = APIRouter(prefix="/__dev")


@router.post("/scenario")
async def scenario(request: Request) -> JSONResponse:
    try:
        value = json.loads(await request.body())
        if (
            not isinstance(value, dict)
            or set(value) != {"scenario"}
            or not isinstance(value["scenario"], str)
            or request.query_params
        ):
            raise ValueError
    except ValueError as exc:
        raise ApiFault("VALIDATION_ERROR", "Expected exactly one scenario name") from exc
    state = fixture_state(request)
    async with state.lock:
        state.reset(value["scenario"])
    return JSONResponse(envelope({"scenario": state.scenario}))
