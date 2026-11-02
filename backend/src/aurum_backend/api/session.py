"""Additive v2 control plane; existing HTTP v1 and bearer upgrade remain compatible."""

from typing import cast

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from aurum_backend.api.envelope import envelope
from aurum_backend.api.errors import ApiFault
from aurum_backend.core.config import Config
from aurum_backend.models.generated_session import SocketTicketEnvelope
from aurum_backend.security.tickets import Tickets

router = APIRouter(prefix="/api/v2/session")


@router.post("/ws-ticket")
async def websocket_ticket(request: Request) -> JSONResponse:
    config = cast(Config, request.app.state.config)
    origin = request.headers.get("origin")
    if origin not in config.origins:
        raise ApiFault("UNAUTHORIZED", "An explicit trusted Origin is required", 403)
    if await request.body() not in {b"", b"{}"} or request.query_params:
        raise ApiFault("VALIDATION_ERROR", "This operation accepts no payload or query")
    tickets = cast(Tickets, request.app.state.socket_tickets)
    value = SocketTicketEnvelope.model_validate(
        envelope({"ticket": tickets.issue(origin), "expires_in_seconds": 10})
    )
    return JSONResponse(value.model_dump(mode="json"))
