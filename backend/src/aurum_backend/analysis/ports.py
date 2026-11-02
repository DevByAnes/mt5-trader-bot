"""Marker interface only; concrete methods require the next phase contract."""

from typing import Protocol


class AnalysisPort(Protocol):
    """Unimplemented extension boundary."""
