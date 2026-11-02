"""Closed-bar reference structure with distinct occurrence and confirmation times."""

from dataclasses import dataclass

from aurum_backend.data.bars import Bar


@dataclass(frozen=True)
class Swing:
    side: str
    price: float
    occurred_at: int
    confirmed_at: int
    index: int


def confirmed_swings(
    bars: list[Bar], *, left: int = 2, right: int = 2, timeframe_seconds: int = 900
) -> list[Swing]:
    if min(left, right, timeframe_seconds) <= 0:
        raise ValueError("Positive swing windows required")
    if any(a.time >= b.time for a, b in zip(bars, bars[1:], strict=False)):
        raise ValueError("Bars must be strictly chronological")
    result = []
    for i in range(left, len(bars) - right):
        before, after, bar = bars[i - left : i], bars[i + 1 : i + right + 1], bars[i]
        # Ties consistently belong to the first extremum: left is strict, right is inclusive.
        if all(bar.high > x.high for x in before) and all(bar.high >= x.high for x in after):
            result.append(
                Swing("HIGH", bar.high, bar.time, bars[i + right].time + timeframe_seconds, i)
            )
        if all(bar.low < x.low for x in before) and all(bar.low <= x.low for x in after):
            result.append(
                Swing("LOW", bar.low, bar.time, bars[i + right].time + timeframe_seconds, i)
            )
    return result


def atr(bars: list[Bar], period: int = 14) -> list[float | None]:
    if period <= 0:
        raise ValueError("Positive ATR period required")
    output: list[float | None] = [None] * len(bars)
    ranges = [
        max(b.high - b.low, abs(b.high - bars[i - 1].close), abs(b.low - bars[i - 1].close))
        if i
        else b.high - b.low
        for i, b in enumerate(bars)
    ]
    if len(bars) < period:
        return output
    value = sum(ranges[:period]) / period
    output[period - 1] = value
    for i in range(period, len(bars)):
        value = (value * (period - 1) + ranges[i]) / period
        output[i] = value
    return output
