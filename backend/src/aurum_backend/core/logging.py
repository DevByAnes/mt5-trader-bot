"""Allow-listed structured messages; no requests, credentials or exception text."""

import json
import logging
import sys

from aurum_backend.core.time import utc_now

LOGGER = logging.getLogger("aurum")


def configure_logging() -> None:
    if not LOGGER.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(message)s"))
        LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = False


def log_event(event: str, *, status: int | None = None) -> None:
    LOGGER.info(json.dumps({"event": event, "status": status, "time_utc": utc_now()}))
