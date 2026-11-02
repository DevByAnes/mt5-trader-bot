"""Marker interface only; concrete methods require the next phase contract."""

from typing import Protocol


class BridgePort(Protocol):
    """Unimplemented extension boundary."""
