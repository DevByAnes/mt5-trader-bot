"""UTC closed-bar validation shared by offline analysis and read-only ingestion."""

import math
from dataclasses import dataclass
from datetime import UTC, datetime


class DataQualityError(ValueError):
    pass


@dataclass(frozen=True)
class Bar:
    time: int
    open: float
    high: float
    low: float
    close: float
    volume: int = 0

    def __post_init__(self) -> None:
        if (
            not isinstance(self.time, int)
            or isinstance(self.time, bool)
            or not isinstance(self.volume, int)
            or isinstance(self.volume, bool)
            or any(isinstance(x, bool) for x in [self.open, self.high, self.low, self.close])
        ):
            raise DataQualityError("Invalid bar types")
        if (
            self.time < 0
            or self.volume < 0
            or not all(math.isfinite(x) for x in [self.open, self.high, self.low, self.close])
        ):
            raise DataQualityError("Invalid bar values")
        if (
            self.low <= 0
            or self.high < max(self.open, self.close, self.low)
            or (self.low > min(self.open, self.close))
        ):
            raise DataQualityError("Invalid OHLC geometry")


def validate_closed(bars: list[Bar], *, timeframe_seconds: int, as_of: int) -> list[Bar]:
    if timeframe_seconds <= 0:
        raise DataQualityError("Invalid timeframe")
    last = -1
    for bar in bars:
        if bar.time <= last:
            raise DataQualityError("Unsorted or duplicate bar timestamps")
        if bar.time + timeframe_seconds > as_of:
            raise DataQualityError("Open or future bar used for a closed-bar decision")
        last = bar.time
    return bars


def require_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise DataQualityError("Timezone-aware datetime required")
    return value.astimezone(UTC)
