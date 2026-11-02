import asyncio
from copy import deepcopy
from typing import Any

from aurum_backend.api.errors import ApiFault
from aurum_backend.core.config import Config


class EventHub:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.subscribers: set[asyncio.Queue[tuple[str, Any]]] = set()
        self.overloaded: set[asyncio.Queue[tuple[str, Any]]] = set()

    def subscribe(self) -> asyncio.Queue[tuple[str, Any]]:
        if len(self.subscribers) >= self.config.max_clients:
            raise ApiFault("UNAVAILABLE", "Stream capacity reached", 503)
        queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue(self.config.queue_size)
        self.subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[tuple[str, Any]]) -> None:
        self.subscribers.discard(queue)
        self.overloaded.discard(queue)

    def publish(self, kind: str, payload: Any) -> None:
        for queue in self.subscribers:
            try:
                queue.put_nowait((kind, deepcopy(payload)))
            except asyncio.QueueFull:
                self.overloaded.add(queue)
