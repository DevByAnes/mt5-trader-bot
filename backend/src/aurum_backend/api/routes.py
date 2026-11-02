"""Implement frozen operations without auto-generating a divergent OpenAPI."""

import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request
from jsonschema import ValidationError as SchemaError
from pydantic import ValidationError
from starlette.responses import JSONResponse

from aurum_backend.api.deps import fixture_state
from aurum_backend.api.envelope import envelope
from aurum_backend.api.errors import ApiFault
from aurum_backend.core.resources import OPENAPI
from aurum_backend.fixtures.state import READS, FixtureState
from aurum_backend.models.base import validate_schema
from aurum_backend.models.generated import ApplyRequest, CommandRequest

router = APIRouter(prefix="/api/v1")


def success(name: str, data: Any, status: int = 200) -> JSONResponse:
    body = envelope(data)
    validate_schema(name + "Envelope", body)
    return JSONResponse(body, status_code=status)


def query(request: Request, allowed: set[str]) -> None:
    for key in request.query_params:
        if key not in allowed or len(request.query_params.getlist(key)) != 1:
            raise ApiFault("VALIDATION_ERROR", "Unsupported or repeated query parameter", field=key)


async def parse_body(request: Request, name: str) -> dict[str, Any]:
    if request.headers.get("content-type", "").split(";", 1)[0] != "application/json":
        raise ApiFault("VALIDATION_ERROR", "application/json required")
    try:

        def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            value: dict[str, Any] = {}
            for key, item in pairs:
                if key in value:
                    raise ValueError("Duplicate key")
                value[key] = item
            return value

        value = json.loads(await request.body(), object_pairs_hook=unique)
        validate_schema(name, value)
        if not isinstance(value, dict):
            raise ValueError("Expected object")
        return value
    except (ValueError, ValidationError, SchemaError) as exc:
        raise ApiFault("VALIDATION_ERROR", "Request body violates frozen schema") from exc


def idempotency_key(request: Request) -> str:
    values = request.headers.getlist("idempotency-key")
    if len(values) != 1:
        raise ApiFault("VALIDATION_ERROR", "Idempotency-Key required", field="Idempotency-Key")
    try:
        key = UUID(values[0])
    except ValueError as exc:
        raise ApiFault(
            "VALIDATION_ERROR", "Idempotency-Key must be UUID", field="Idempotency-Key"
        ) from exc
    return str(key)


def read_handler(resource: str) -> Any:
    async def handle(request: Request) -> JSONResponse:
        state = fixture_state(request)
        listed = resource in {"Signals", "Journal", "Validation", "Logs", "Audit"}
        query(request, {"cursor", "limit"} if listed else set())
        async with state.lock:
            data = state.read(resource)
            if listed:
                raw_limit = request.query_params.get("limit", "50")
                try:
                    # No floats, signs or booleans coerced into limits.
                    if not raw_limit.isascii() or not raw_limit.isdecimal():
                        raise ValueError
                    limit = int(raw_limit)
                    if not 1 <= limit <= 100:
                        raise ValueError
                except ValueError as exc:
                    raise ApiFault(
                        "VALIDATION_ERROR", "limit must be 1–100", field="limit"
                    ) from exc
                data = state.paginate(data, resource, request.query_params.get("cursor"), limit)
        return success(resource, data)

    return handle


for path, resource in READS.items():
    router.add_api_route(path, read_handler(resource), methods=["GET"], name="get" + resource)


@router.post("/settings/validate")
async def validate_settings(request: Request) -> JSONResponse:
    query(request, set())
    body = ApplyRequest.model_validate(await parse_body(request, "ApplyRequest"))
    state = fixture_state(request)
    async with state.lock:
        state.available()
        return success("Diff", state.validate(body))


@router.post("/settings/apply")
async def apply_settings(request: Request) -> JSONResponse:
    query(request, set())
    key = idempotency_key(request)
    body = await parse_body(request, "ApplyRequest")
    state = fixture_state(request)
    async with state.lock:
        state.available()
        accepted = state.accept("/settings/apply", key, body)
    validate_schema("AckEnvelope", accepted)
    return JSONResponse(accepted, status_code=202)


@router.post("/commands/{command}")
async def command(request: Request, command: str) -> JSONResponse:
    query(request, set())
    paths: Any = OPENAPI["paths"]
    allowed = paths["/commands/{command}"]["post"]["parameters"][0]["schema"]["enum"]
    if command not in allowed:
        raise ApiFault("NOT_FOUND", "Unknown restricted command", 404)
    key = idempotency_key(request)
    body = await parse_body(request, "CommandRequest")
    CommandRequest.model_validate(body)
    state = fixture_state(request)
    async with state.lock:
        state.available()
        accepted = state.accept("/commands/" + command, key, body)
    validate_schema("AckEnvelope", accepted)
    return JSONResponse(accepted, status_code=202)


@router.get("/requests/{identity}")
async def request_result(request: Request, identity: str) -> JSONResponse:
    query(request, set())
    state = fixture_state(request)
    async with state.lock:
        state.available()
        state.settle()
        return success("Ack", state.request_result(identity))


@router.post("/audit/{identity}/rollback")
async def rollback(request: Request, identity: str) -> JSONResponse:
    query(request, set())
    if await request.body() not in {b"", b"{}"}:
        raise ApiFault("VALIDATION_ERROR", "Rollback accepts no request payload")
    state: FixtureState = fixture_state(request)
    async with state.lock:
        state.available()
        row = next((row for row in state.audit if row["id"] == identity), None)
        if row is None:
            raise ApiFault("NOT_FOUND", "Audit record unavailable", 404)
        body = ApplyRequest.model_validate(
            {"base_version": state.version, "values": row["previous_values"]}
        )
        return success("Diff", state.validate(body))
