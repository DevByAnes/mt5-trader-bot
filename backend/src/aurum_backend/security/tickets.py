"""One-use, origin-bound, in-memory WebSocket tickets; no URL credentials."""

import hashlib
import secrets
import time
from dataclasses import dataclass

from aurum_backend.api.errors import ApiFault


@dataclass(frozen=True)
class Ticket:
    origin: str
    expires: float


class Tickets:
    def __init__(self, lifetime: float = 10.0, capacity: int = 64) -> None:
        self.lifetime = lifetime
        self.capacity = capacity
        self.values: dict[bytes, Ticket] = {}
        self.pending = 0

    def issue(self, origin: str) -> str:
        now = time.monotonic()
        self.values = {key: value for key, value in self.values.items() if value.expires > now}
        if len(self.values) >= self.capacity:
            raise ApiFault("UNAVAILABLE", "Socket authentication capacity reached", 503)
        token = secrets.token_urlsafe(32)
        self.values[hashlib.sha256(token.encode()).digest()] = Ticket(origin, now + self.lifetime)
        return token

    def consume(self, token: str, origin: str) -> bool:
        if not token.isascii() or not 32 <= len(token) <= 128:
            return False
        value = self.values.pop(hashlib.sha256(token.encode()).digest(), None)
        return value is not None and value.expires > time.monotonic() and value.origin == origin
