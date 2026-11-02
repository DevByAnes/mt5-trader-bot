"""Conservative historical outcome study for an explicitly supplied signal."""

import math
from dataclasses import dataclass

from aurum_backend.data.bars import Bar, validate_closed


@dataclass(frozen=True)
class HypotheticalOutcome:
    status: str
    gross_r: float | None
    net_r: float | None
    resolved_at: int | None
    ambiguous: bool


def evaluate(
    side: str,
    entry: float,
    stop: float,
    target: float,
    bars: list[Bar],
    *,
    start: int,
    expiry: int,
    as_of: int,
    costs_r: float | None = None,
    m1: list[Bar] | None = None,
) -> HypotheticalOutcome:
    if (
        side not in {"BUY", "SELL"}
        or expiry <= start
        or any(type(x) is not int or x < 0 for x in [start, expiry, as_of])
        or (expiry - start) % 900 != 0
        or not all(math.isfinite(x) for x in [entry, stop, target])
    ):
        raise ValueError("Invalid historical signal")
    if not ((stop < entry < target) if side == "BUY" else (target < entry < stop)):
        raise ValueError("Invalid signal price geometry")
    validate_closed(bars, timeframe_seconds=900, as_of=as_of)
    if m1 is not None:
        validate_closed(m1, timeframe_seconds=60, as_of=as_of)
    if costs_r is not None and (not math.isfinite(costs_r) or costs_r < 0):
        raise ValueError("Costs must be finite and nonnegative")
    distance = abs(entry - stop)

    def hits(bar: Bar) -> tuple[bool, bool]:
        return (
            (bar.low <= stop, bar.high >= target)
            if side == "BUY"
            else (bar.high >= stop, bar.low <= target)
        )

    def finish(status: str, gross: float, at: int, ambiguous: bool = False) -> HypotheticalOutcome:
        return HypotheticalOutcome(
            status, gross, gross - costs_r if costs_r is not None else None, at, ambiguous
        )

    observed = [b for b in bars if start <= b.time and b.time + 900 <= expiry]
    expected = start
    for bar in observed:
        if bar.time != expected:
            return HypotheticalOutcome("UNAVAILABLE", None, None, None, False)
        expected += 900
        sl, tp = hits(bar)
        if sl and tp:
            fine = [b for b in m1 or [] if bar.time <= b.time < bar.time + 900]
            complete = [b.time for b in fine] == list(range(bar.time, bar.time + 900, 60))
            if complete:
                complete = all(
                    math.isclose(left, right, rel_tol=1e-9, abs_tol=1e-9)
                    for left, right in [
                        (fine[0].open, bar.open),
                        (fine[-1].close, bar.close),
                        (max(b.high for b in fine), bar.high),
                        (min(b.low for b in fine), bar.low),
                    ]
                )
            if complete:
                for candle in fine:
                    fine_sl, fine_tp = hits(candle)
                    if fine_sl:
                        return finish("SL", -1, candle.time + 60, fine_tp)
                    if fine_tp:
                        return finish("TP", abs(target - entry) / distance, candle.time + 60)
            return finish("SL", -1, bar.time + 900, True)
        if sl:
            return finish("SL", -1, bar.time + 900)
        if tp:
            return finish("TP", abs(target - entry) / distance, bar.time + 900)
    if not observed:
        return HypotheticalOutcome("UNAVAILABLE", None, None, None, False)
    if as_of >= expiry and observed[-1].time + 900 == expiry:
        signed = 1 if side == "BUY" else -1
        return finish("EXPIRED", signed * (observed[-1].close - entry) / distance, expiry)
    if expected + 900 <= min(as_of, expiry):
        return HypotheticalOutcome("UNAVAILABLE", None, None, None, False)
    return HypotheticalOutcome("PENDING", None, None, None, False)
