"""Marker interface only; concrete methods require the next phase contract."""

from typing import Protocol


class DataPort(Protocol):
    """Unimplemented extension boundary."""
