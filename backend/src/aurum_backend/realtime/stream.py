"""Bounded event queues; per-client seq; REST is the full authoritative snapshot."""

import asyncio
import time
from typing import Any, cast

import anyio
from fastapi import APIRouter, WebSocket
from starlette.websockets import WebSocketDisconnect

from aurum_backend.api.envelope import error_response
from aurum_backend.api.errors import ApiFault
from aurum_backend.core.time import utc_now
from aurum_backend.fixtures.state import FixtureState
from aurum_backend.models.base import validate_schema
from aurum_backend.security.tickets import Tickets
from aurum_backend.services.file_state import FileState

router = APIRouter()


async def pump(state: FixtureState | FileState) -> None:
    """One task per app, not one timer/task per accepted mutation."""
    heartbeat = time.monotonic()
    while True:
        await asyncio.sleep(0.05)
        async with state.lock:
            if isinstance(state, FileState):
                try:
                    events = await asyncio.to_thread(state.poll)
                    for kind, payload in events:
                        state.publish(kind, payload)
                except OSError:
                    from aurum_backend.core.logging import log_event

                    log_event("bridge_io_unavailable", status=503)
                continue
            if state.scenario in {"python-offline", "bridge-offline"}:
                state.overloaded.update(state.subscribers)
                continue
            state.settle()
            if time.monotonic() >= heartbeat:
                state.publish("heartbeat", state.read("Status"))
                heartbeat = time.monotonic() + state.config.heartbeat_seconds


async def send_event(
    websocket: WebSocket, state: FixtureState | FileState, kind: str, payload: Any, seq: int
) -> None:
    event = {"type": kind, "seq": seq, "server_time_utc": utc_now(), "payload": payload}
    validate_schema("Event", event)
    await asyncio.wait_for(websocket.send_json(event), timeout=state.config.send_timeout)


async def writer(
    websocket: WebSocket, state: FixtureState | FileState, queue: asyncio.Queue[tuple[str, Any]]
) -> None:
    seq = 0
    # Replay only frozen telemetry types. Settings/chart/history/audit remain REST GETs.
    async with state.lock:
        frames: list[tuple[str, Any]] = []
        for resource, event in [
            ("Status", "heartbeat"),
            ("EaState", "ea_state"),
            ("Positions", "position"),
            ("DailyRisk", "risk_mode"),
        ]:
            try:
                frames.append((event, state.read(resource)))
            except ApiFault:
                continue
        for resource, event in [("Signals", "signal"), ("Logs", "log")]:
            try:
                frames += [(event, x) for x in state.read(resource)["items"]]
            except ApiFault:
                continue
    for kind, payload in frames:
        seq += 1
        await send_event(websocket, state, kind, payload, seq)
    gap_sent = False
    while True:
        if queue in state.overloaded:
            await websocket.close(code=1013, reason="Resnapshot required")
            return
        try:
            kind, payload = await asyncio.wait_for(queue.get(), timeout=0.1)
        except TimeoutError:
            continue
        if state.scenario == "seq-gap" and not gap_sent:
            seq += 1
            gap_sent = True
        seq += 1
        await send_event(websocket, state, kind, payload, seq)


async def reader(websocket: WebSocket) -> None:
    # Client snapshot requests are not defined as an input schema. Reconnect + REST is normative.
    while True:
        message = await websocket.receive()
        if message["type"] == "websocket.disconnect":
            return
        await websocket.close(code=1008, reason="Client frames are not part of this contract")
        return


async def ticket_auth(websocket: WebSocket, state: FixtureState | FileState) -> bool:
    tickets = cast(Tickets, websocket.app.state.socket_tickets)
    if tickets.pending >= state.config.max_clients:
        await websocket.send_denial_response(
            error_response(503, "UNAVAILABLE", "Socket capacity reached")
        )
        return False
    tickets.pending += 1
    try:
        await websocket.accept()
        frame = await asyncio.wait_for(websocket.receive_json(), 5)
        valid = (
            isinstance(frame, dict)
            and set(frame) == {"type", "ticket"}
            and frame["type"] == "authenticate"
            and isinstance(frame["ticket"], str)
            and tickets.consume(frame["ticket"], websocket.headers.get("origin", ""))
        )
        if not valid:
            await websocket.close(code=1008, reason="Socket authentication failed")
        return valid
    except (ValueError, TimeoutError, WebSocketDisconnect):
        try:
            await websocket.close(code=1008, reason="Socket authentication failed")
        except RuntimeError:
            pass
        return False
    finally:
        tickets.pending -= 1


@router.websocket("/ws")
async def stream(websocket: WebSocket) -> None:
    state = cast(FixtureState | FileState, websocket.app.state.fixture_state)
    preaccepted = False
    if websocket.scope.get("state", {}).get("ws_requires_ticket"):
        if not await ticket_auth(websocket, state):
            return
        preaccepted = True
    try:
        state.available()
        queue = state.subscribe()
    except ApiFault as exc:
        if preaccepted:
            await websocket.close(code=1013, reason="Stream unavailable")
        else:
            await websocket.send_denial_response(error_response(exc.status, exc.code, exc.message))
        return
    tasks: list[asyncio.Task[None]] = []
    try:
        if not preaccepted:
            await websocket.accept()
        tasks = [
            asyncio.create_task(writer(websocket, state, queue)),
            asyncio.create_task(reader(websocket)),
        ]
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            try:
                task.result()
            except (TimeoutError, WebSocketDisconnect, OSError, RuntimeError):
                try:
                    await websocket.close(code=1013, reason="Stream unavailable; reconnect")
                except (RuntimeError, OSError):
                    pass
    except asyncio.CancelledError:
        # ASGI cancellation means the transport has gone; cleanup still owns its child tasks.
        pass
    finally:
        state.unsubscribe(queue)
        for task in tasks:
            task.cancel()
        with anyio.CancelScope(shield=True):
            await asyncio.gather(*tasks, return_exceptions=True)
