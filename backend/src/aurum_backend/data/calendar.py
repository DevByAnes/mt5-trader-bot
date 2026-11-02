"""Timezone-explicit news snapshots and local session windows for offline research."""

import csv
import io
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from aurum_backend.data.bars import DataQualityError, require_utc

MAX_NEWS_BYTES = 4 * 1024 * 1024
NEWS_COLUMNS = ["event_id", "time_utc", "currency", "impact", "title"]


@dataclass(frozen=True)
class NewsEvent:
    event_id: str
    at: datetime
    currency: str
    impact: str
    title: str

    def __post_init__(self) -> None:
        require_utc(self.at)
        if (
            not 1 <= len(self.event_id) <= 128
            or not self.currency.isascii()
            or len(self.currency) != 3
            or not self.currency.isalpha()
            or self.currency != self.currency.upper()
            or self.impact not in {"LOW", "MEDIUM", "HIGH"}
            or not 1 <= len(self.title) <= 512
            or any(ord(c) < 32 for c in self.event_id + self.title)
        ):
            raise DataQualityError("Invalid news event")


@dataclass(frozen=True)
class NewsCalendar:
    events: tuple[NewsEvent, ...]
    coverage_start: datetime
    coverage_end: datetime

    def __post_init__(self) -> None:
        start, end = require_utc(self.coverage_start), require_utc(self.coverage_end)
        if start >= end or len(self.events) > 20000:
            raise DataQualityError("Invalid calendar coverage")
        if len({e.event_id for e in self.events}) != len(self.events):
            raise DataQualityError("Duplicate news identity")
        if any(not start <= e.at < end for e in self.events):
            raise DataQualityError("News event outside declared coverage")

    def blocked(
        self,
        at: datetime,
        *,
        before_minutes: int,
        after_minutes: int,
        currencies: frozenset[str] = frozenset({"USD"}),
    ) -> bool | None:
        instant = require_utc(at)
        if any(type(x) is not int or not 0 <= x <= 1440 for x in [before_minutes, after_minutes]):
            raise DataQualityError("Invalid news window")
        # Relevant events occur between now-after and now+before.
        first = instant - timedelta(minutes=after_minutes)
        last = instant + timedelta(minutes=before_minutes)
        if first < self.coverage_start or last >= self.coverage_end:
            return None  # No coverage must never mean that there is no important news.
        return any(
            first <= e.at <= last and e.currency in currencies and e.impact == "HIGH"
            for e in self.events
        )

    def to_csv(self) -> str:
        stream = io.StringIO(newline="")
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(
            ["AURUM_NEWS_V1", "UTC", _iso(self.coverage_start), _iso(self.coverage_end)]
        )
        writer.writerow(NEWS_COLUMNS)
        for event in sorted(self.events, key=lambda e: (e.at, e.event_id)):
            writer.writerow(
                [event.event_id, _iso(event.at), event.currency, event.impact, event.title]
            )
        result = stream.getvalue()
        if len(result.encode("utf-8")) > MAX_NEWS_BYTES:
            raise DataQualityError("News snapshot too large")
        return result

    @classmethod
    def from_csv(cls, raw: str) -> "NewsCalendar":
        if len(raw.encode("utf-8")) > MAX_NEWS_BYTES:
            raise DataQualityError("News snapshot too large")
        try:
            reader = csv.reader(io.StringIO(raw, newline=""), strict=True)
            header = next(reader)
            if len(header) != 4 or header[:2] != ["AURUM_NEWS_V1", "UTC"]:
                raise DataQualityError("Explicit UTC coverage header required")
            if next(reader) != NEWS_COLUMNS:
                raise DataQualityError("Invalid news columns")
            events: list[NewsEvent] = []
            for row in reader:
                if len(row) != 5 or len(events) >= 20000:
                    raise DataQualityError("Invalid news row")
                identity, at, currency, impact, title = row
                events.append(NewsEvent(identity, _parse_utc(at), currency, impact, title))
            return cls(tuple(events), _parse_utc(header[2]), _parse_utc(header[3]))
        except (StopIteration, csv.Error, ValueError) as exc:
            raise DataQualityError("Invalid UTC news snapshot") from exc


def _iso(value: datetime) -> str:
    return require_utc(value).isoformat().replace("+00:00", "Z")


def _parse_utc(value: str) -> datetime:
    result = datetime.fromisoformat(value)
    if result.utcoffset() != timedelta(0):
        raise DataQualityError("CSV timestamps must explicitly specify UTC")
    return require_utc(result)


@dataclass(frozen=True)
class Session:
    name: str
    timezone: str
    start_minute: int
    end_minute: int

    def __post_init__(self) -> None:
        ZoneInfo(self.timezone)
        if (
            not self.name
            or any(
                type(x) is not int or not 0 <= x < 1440
                for x in [self.start_minute, self.end_minute]
            )
            or self.start_minute == self.end_minute
        ):
            raise DataQualityError("Invalid session")

    def window(self, local_day: date) -> tuple[datetime, datetime]:
        end_day = local_day + timedelta(days=int(self.end_minute < self.start_minute))
        return (
            self._boundary(local_day, self.start_minute, end=False),
            self._boundary(end_day, self.end_minute, end=True),
        )

    def _boundary(self, day: date, minute: int, *, end: bool) -> datetime:
        civil = datetime.combine(day, time(minute // 60, minute % 60))
        zone = ZoneInfo(self.timezone)
        candidates = []
        for fold in [0, 1]:
            instant = civil.replace(tzinfo=zone, fold=fold).astimezone(UTC)
            if instant.astimezone(zone).replace(tzinfo=None) == civil:
                candidates.append(instant)
        if not candidates:
            raise DataQualityError("Session boundary falls in a DST gap")
        # A repeated hour includes both occurrences; this policy is explicit and deterministic.
        return max(candidates) if end else min(candidates)

    def contains(self, at: datetime) -> bool:
        instant = require_utc(at)
        local_day = instant.astimezone(ZoneInfo(self.timezone)).date()
        for day in [local_day - timedelta(days=1), local_day]:
            if day.weekday() < 5:
                start, end = self.window(day)
                if start <= instant < end:
                    return True
        return False
