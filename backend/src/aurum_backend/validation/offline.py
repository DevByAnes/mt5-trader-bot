"""Deterministic research helpers; never called by the execution path."""

from dataclasses import dataclass
from typing import TypedDict

import numpy as np


@dataclass(frozen=True)
class Fold:
    train_start: int
    train_end: int
    test_start: int
    test_end: int


class MonteCarloReport(TypedDict):
    method: str
    seed: int
    paths: int
    observations: int
    terminal_r_p05: float
    terminal_r_p50: float
    terminal_r_p95: float
    max_drawdown_r_p95: float


def walk_forward(length: int, train: int, test: int, gap: int = 0) -> list[Fold]:
    if min(length, train, test) <= 0 or gap < 0:
        raise ValueError("Invalid walk-forward dimensions")
    result = []
    start = 0
    while start + train + gap + test <= length:
        result.append(Fold(start, start + train, start + train + gap, start + train + gap + test))
        start += test
    return result


def monte_carlo_r(
    outcomes: list[float], *, seed: int, paths: int = 1000, costs_r: float = 0.0
) -> MonteCarloReport:
    values = np.asarray(outcomes, dtype=np.float64)
    if not len(values) or not np.isfinite(values).all() or not 1 <= paths <= 100000:
        raise ValueError("Finite, nonempty outcomes and bounded path count required")
    if costs_r < 0 or not np.isfinite(costs_r):
        raise ValueError("Cost stress must be finite and nonnegative")
    if len(values) * paths > 2_000_000:
        raise ValueError("Research allocation exceeds configured bound")
    samples = np.random.default_rng(seed).choice(values - costs_r, size=(paths, len(values)))
    curve = np.column_stack((np.zeros(paths), samples.cumsum(axis=1)))
    drawdowns = np.maximum.accumulate(curve, axis=1) - curve
    return {
        "method": "bootstrap_with_replacement",
        "seed": seed,
        "paths": paths,
        "observations": len(values),
        "terminal_r_p05": float(np.quantile(curve[:, -1], 0.05)),
        "terminal_r_p50": float(np.quantile(curve[:, -1], 0.5)),
        "terminal_r_p95": float(np.quantile(curve[:, -1], 0.95)),
        "max_drawdown_r_p95": float(np.quantile(drawdowns.max(axis=1), 0.95)),
    }
