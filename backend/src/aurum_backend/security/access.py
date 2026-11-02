"""Small ASGI perimeter: no proxy trust, query credentials, wildcard CORS or secret logs."""

import asyncio
import hmac
import time
from collections import deque

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from starlette.websockets import WebSocket

from aurum_backend.api.envelope import error_response
from aurum_backend.core.config import Config


class RateLimiter:
    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.hits: deque[float] = deque()

    def admit(self) -> bool:
        now = time.monotonic()
        while self.hits and self.hits[0] <= now - 60:
            self.hits.popleft()
        if len(self.hits) >= self.limit:
            return False
        self.hits.append(now)
        return True


class SecurityMiddleware:
    def __init__(self, app: ASGIApp, config: Config) -> None:
        self.app = app
        self.config = config
        self.authenticated = RateLimiter(config.requests_per_minute)
        self.unauthenticated = RateLimiter(config.requests_per_minute)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return
        headers = Headers(scope=scope)
        origin = headers.get("origin")

        async def respond(status: int, code: str, message: str) -> None:
            response = error_response(status, code, message)
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Aurum-Mode"] = "fixture"
            if status == 503:
                response.headers["Retry-After"] = "60"
            if status == 401:
                response.headers["WWW-Authenticate"] = "Bearer"
            if origin in self.config.origins:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Vary"] = "Origin"
            if scope["type"] == "websocket":
                await WebSocket(scope, receive, send).send_denial_response(response)
            else:
                await response(scope, receive, send)

        peer = scope.get("client")
        host = headers.get("host", "").split(":", 1)[0]
        if not peer or peer[0] != "127.0.0.1" or host != "127.0.0.1":
            await respond(403, "UNAUTHORIZED", "Loopback access required")
            return
        if origin is not None and origin not in self.config.origins:
            await respond(403, "UNAUTHORIZED", "Origin not allowed")
            return
        if scope["type"] == "websocket" and scope.get("query_string"):
            await respond(422, "VALIDATION_ERROR", "WebSocket query parameters are not permitted")
            return
        if scope["type"] == "http" and scope["method"] == "OPTIONS":
            requested = headers.get("access-control-request-method", "")
            requested_headers = {
                v.strip().lower()
                for v in headers.get("access-control-request-headers", "").split(",")
                if v.strip()
            }
            if (
                origin not in self.config.origins
                or requested not in {"GET", "POST"}
                or not (requested_headers <= {"authorization", "content-type", "idempotency-key"})
            ):
                await respond(403, "UNAUTHORIZED", "CORS preflight not permitted")
                return
            response = error_response(204, "UNAVAILABLE", "")
            response.body = b""
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST"
            response.headers["Access-Control-Allow-Headers"] = (
                "Authorization, Content-Type, Idempotency-Key"
            )
            response.headers["Vary"] = "Origin"
            await response(scope, receive, send)
            return
        raw = headers.get("authorization", "")
        supplied = raw[7:] if raw.startswith("Bearer ") else ""
        valid = hmac.compare_digest(supplied.encode("utf-8"), self.config.token.encode("ascii"))
        if not valid:
            if self.unauthenticated.admit():
                await respond(401, "UNAUTHORIZED", "Session token required")
            else:
                await respond(503, "UNAVAILABLE", "Request rate exceeded")
            return
        if not self.authenticated.admit():
            await respond(503, "UNAVAILABLE", "Request rate exceeded")
            return

        async def safe_send(message: Message) -> None:
            if message["type"] in {"http.response.start", "websocket.http.response.start"}:
                outgoing = MutableHeaders(scope=message)
                outgoing["Cache-Control"] = "no-store"
                outgoing["X-Aurum-Mode"] = "fixture"
                outgoing["X-Content-Type-Options"] = "nosniff"
                if origin in self.config.origins:
                    outgoing["Access-Control-Allow-Origin"] = origin
                    outgoing["Vary"] = "Origin"
            await send(message)

        if scope["type"] == "websocket":
            await self.app(scope, receive, safe_send)
            return
        body = bytearray()
        try:
            async with asyncio.timeout(5):
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    body.extend(message.get("body", b""))
                    if len(body) > self.config.max_body_bytes:
                        await respond(422, "VALIDATION_ERROR", "Request body too large")
                        return
                    if not message.get("more_body", False):
                        break
        except TimeoutError:
            await respond(400, "VALIDATION_ERROR", "Request body deadline exceeded")
            return
        consumed = False

        async def buffered_receive() -> Message:
            nonlocal consumed
            if not consumed:
                consumed = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, buffered_receive, safe_send)
