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

router = APIRouter()


async def pump(state: FixtureState) -> None:
    """One task per app, not one timer/task per accepted mutation."""
    heartbeat = time.monotonic()
    while True:
        await asyncio.sleep(0.05)
        async with state.lock:
            if state.scenario in {"python-offline", "bridge-offline"}:
                state.overloaded.update(state.subscribers)
                continue
            state.settle()
            if time.monotonic() >= heartbeat:
                state.publish("heartbeat", state.read("Status"))
                heartbeat = time.monotonic() + state.config.heartbeat_seconds


async def send_event(
    websocket: WebSocket, state: FixtureState, kind: str, payload: Any, seq: int
) -> None:
    event = {"type": kind, "seq": seq, "server_time_utc": utc_now(), "payload": payload}
    validate_schema("Event", event)
    await asyncio.wait_for(websocket.send_json(event), timeout=state.config.send_timeout)


async def writer(
    websocket: WebSocket, state: FixtureState, queue: asyncio.Queue[tuple[str, Any]]
) -> None:
    seq = 0
    # Replay only frozen telemetry types. Settings/chart/history/audit remain REST GETs.
    async with state.lock:
        frames = [
            ("heartbeat", state.read("Status")),
            ("ea_state", state.read("EaState")),
            ("position", state.read("Positions")),
            ("risk_mode", state.read("DailyRisk")),
        ]
        frames += [("signal", x) for x in state.read("Signals")["items"]]
        frames += [("log", x) for x in state.read("Logs")["items"]]
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


@router.websocket("/ws")
async def stream(websocket: WebSocket) -> None:
    state = cast(FixtureState, websocket.app.state.fixture_state)
    try:
        state.available()
        queue = state.subscribe()
    except ApiFault as exc:
        await websocket.send_denial_response(error_response(exc.status, exc.code, exc.message))
        return
    tasks: list[asyncio.Task[None]] = []
    try:
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
