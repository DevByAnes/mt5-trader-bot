from typing import cast

from pydantic import JsonValue
from starlette.responses import JSONResponse

from aurum_backend.core.time import utc_now


def envelope(data: JsonValue) -> dict[str, JsonValue]:
    return {"data": data, "error": None, "server_time_utc": utc_now(), "api_version": "1.0.0"}


def error_response(status: int, code: str, message: str, field: str | None = None) -> JSONResponse:
    body = envelope(None)
    error: dict[str, JsonValue] = {"code": code, "message": message}
    if field is not None:
        error["field"] = field
    body["error"] = cast(JsonValue, error)
    return JSONResponse(body, status_code=status)
