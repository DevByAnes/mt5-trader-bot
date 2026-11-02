"""Fail-closed source-clock diagnostics; never infer or apply a broker timezone offset."""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class QuoteClock:
    status: str
    age_seconds: float | None

    @property
    def usable(self) -> bool:
        return self.status == "FRESH"


def inspect_quote_clock(observed_epoch: float, now_epoch: float) -> QuoteClock:
    if (
        isinstance(observed_epoch, bool)
        or isinstance(now_epoch, bool)
        or not all(math.isfinite(x) and x > 0 for x in [observed_epoch, now_epoch])
    ):
        return QuoteClock("INVALID_TIMESTAMP", None)
    age = now_epoch - observed_epoch
    if age < -5:
        return QuoteClock("FUTURE_QUOTE", age)
    if age > 120:
        return QuoteClock("STALE_QUOTE", age)
    return QuoteClock("FRESH", age)
