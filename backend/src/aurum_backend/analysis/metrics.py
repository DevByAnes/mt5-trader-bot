"""Observed historical statistics only; missing values stay unavailable."""

import math
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class Observation:
    id: str
    side: str
    session: str
    regime: str
    r: float | None
    pnl: float | None = None
    currency: str | None = None

    def __post_init__(self) -> None:
        if self.side not in {"BUY", "SELL"} or self.r is not None and not math.isfinite(self.r):
            raise ValueError("Invalid historical observation")
        if self.pnl is not None and (not math.isfinite(self.pnl) or not self.currency):
            raise ValueError("Cash outcome requires a finite value and explicit currency")


@dataclass(frozen=True)
class Metrics:
    records: int
    known_outcomes: int
    unavailable_outcomes: int
    mean_r: float | None
    profit_factor: float | None
    profit_factor_r: float | None
    win_rate: float | None
    median_r: float | None


def summarize(rows: list[Observation]) -> Metrics:
    if len({row.id for row in rows}) != len(rows):
        raise ValueError("Duplicate observation identities")
    known = np.asarray([row.r for row in rows if row.r is not None], dtype=np.float64)
    losses = float(-known[known < 0].sum())
    gains = float(known[known > 0].sum())
    cash_factor = None
    if (
        rows
        and all(row.pnl is not None for row in rows)
        and len({row.currency for row in rows}) == 1
    ):
        cash = np.asarray([row.pnl for row in rows], dtype=np.float64)
        cash_loss = float(-cash[cash < 0].sum())
        cash_factor = float(cash[cash > 0].sum()) / cash_loss if cash_loss > 0 else None
    return Metrics(
        len(rows),
        len(known),
        len(rows) - len(known),
        float(known.mean()) if len(known) else None,
        cash_factor,
        gains / losses if losses > 0 else None,
        float((known > 0).mean()) if len(known) else None,
        float(np.median(known)) if len(known) else None,
    )


def grouped(rows: list[Observation]) -> dict[str, Any]:
    result: dict[str, Any] = {"overall": asdict(summarize(rows))}
    for field in ["side", "session", "regime"]:
        keys = sorted({getattr(row, field) for row in rows})
        result[field] = {
            key: asdict(summarize([row for row in rows if getattr(row, field) == key]))
            for key in keys
        }
    return result


def max_drawdown(equity: list[float | None]) -> float | None:
    if not equity or any(x is None for x in equity):
        return None
    values = np.asarray(equity, dtype=np.float64)
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("Equity curve requires finite positive observations")
    peaks = np.maximum.accumulate(values)
    return float(((peaks - values) / peaks).max())
