"""Optional official SDK access through a capability containing data reads only."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from aurum_backend.data.bars import Bar, DataQualityError, require_utc, validate_closed


@dataclass(frozen=True)
class TerminalReads:
    initialize: Callable[[str], bool]
    shutdown: Callable[[], None]
    rates: Callable[[str, int, datetime, datetime], Any]
    timeframe_m15: int


def official_reads() -> TerminalReads:
    # This single explicit import is checked against an allowlist by tools.no_orders.
    try:
        from MetaTrader5 import (
            TIMEFRAME_M15,
            copy_rates_range,
            initialize,
            shutdown,
        )
    except ImportError:
        raise DataQualityError("Optional Windows SDK unavailable; install the mt5 extra") from None
    return TerminalReads(initialize, shutdown, copy_rates_range, TIMEFRAME_M15)


class ReadOnlyTerminal:
    def __init__(
        self,
        terminal_path: str,
        reads: TerminalReads | None = None,
        *,
        source_utc_offset_minutes: int = 0,
    ) -> None:
        if not terminal_path:
            raise DataQualityError("Explicit terminal path required")
        if (
            type(source_utc_offset_minutes) is not int
            or not -720 <= source_utc_offset_minutes <= 840
            or source_utc_offset_minutes % 15
        ):
            raise DataQualityError("Explicit bounded source clock offset required")
        self.source_offset = timedelta(minutes=source_utc_offset_minutes)
        self.source_offset_seconds = source_utc_offset_minutes * 60
        self.reads = reads or official_reads()
        if not self.reads.initialize(terminal_path):
            raise DataQualityError("Terminal data connection unavailable")

    def close(self) -> None:
        self.reads.shutdown()

    def m15(self, symbol: str, start: datetime, end: datetime, *, as_of: datetime) -> list[Bar]:
        if "XAUUSD" not in symbol.upper():
            raise DataQualityError("Only the configured gold symbol is supported")
        start, end, now = require_utc(start), require_utc(end), require_utc(as_of)
        if start >= end or end > now:
            raise DataQualityError("Invalid historical interval")
        # Default follows the SDK UTC contract. Exceptional server-clock feeds require an
        # explicitly verified offset; never guess it or reuse it across DST transitions.
        raw = self.reads.rates(
            symbol, self.reads.timeframe_m15, start + self.source_offset, end + self.source_offset
        )
        if raw is None:
            raise DataQualityError("Terminal did not provide market data")
        bars = [
            Bar(
                int(row["time"]) - self.source_offset_seconds,
                float(row["open"]),
                float(row["high"]),
                float(row["low"]),
                float(row["close"]),
                int(row["tick_volume"]),
            )
            for row in raw
            if int(row["time"]) - self.source_offset_seconds + 900 <= int(now.timestamp())
        ]
        return validate_closed(bars, timeframe_seconds=900, as_of=int(now.timestamp()))
