from datetime import UTC, date, datetime

import pytest

from aurum_backend.data.bars import DataQualityError
from aurum_backend.data.calendar import NewsCalendar, NewsEvent, Session


def utc(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


def test_news_round_trip_and_window_edges() -> None:
    calendar = NewsCalendar(
        (NewsEvent("cpi", utc("2026-07-01T12:30"), "USD", "HIGH", "CPI, actual"),),
        utc("2026-07-01"),
        utc("2026-07-02"),
    )
    assert NewsCalendar.from_csv(calendar.to_csv()) == calendar
    assert calendar.blocked(utc("2026-07-01T12:00"), before_minutes=30, after_minutes=15)
    assert calendar.blocked(utc("2026-07-01T12:45"), before_minutes=30, after_minutes=15)
    assert not calendar.blocked(utc("2026-07-01T12:46"), before_minutes=30, after_minutes=15)
    assert calendar.blocked(utc("2026-07-01T23:50"), before_minutes=30, after_minutes=15) is None


def test_empty_known_calendar_differs_from_missing_coverage() -> None:
    calendar = NewsCalendar((), utc("2026-07-01"), utc("2026-07-02"))
    restored = NewsCalendar.from_csv(calendar.to_csv())
    assert restored.blocked(utc("2026-07-01T12:00"), before_minutes=30, after_minutes=30) is False
    with pytest.raises(DataQualityError):
        NewsCalendar.from_csv("time,title\n2026-07-01T12:00,CPI\n")
    malformed = calendar.to_csv().replace("2026-07-01T00:00:00Z", "2026-07-01T00:00:00")
    with pytest.raises(DataQualityError):
        NewsCalendar.from_csv(malformed)


def test_london_and_new_york_use_independent_dst_rules() -> None:
    london = Session("London morning", "Europe/London", 8 * 60, 11 * 60)
    new_york = Session("New York morning", "America/New_York", 8 * 60, 11 * 60 + 30)
    assert london.window(date(2026, 1, 5))[0] == utc("2026-01-05T08:00")
    assert london.window(date(2026, 7, 1))[0] == utc("2026-07-01T07:00")
    # During March the US has changed its clock while the UK has not.
    assert new_york.window(date(2026, 3, 16))[0] == utc("2026-03-16T12:00")
    assert london.window(date(2026, 3, 16))[0] == utc("2026-03-16T08:00")
    assert not london.contains(utc("2026-07-04T08:00"))
    assert london.contains(utc("2026-07-01T07:00"))
    assert not london.contains(utc("2026-07-01T10:00"))


def test_overnight_and_dst_gap_have_explicit_behavior() -> None:
    overnight = Session("Late", "UTC", 22 * 60, 2 * 60)
    assert overnight.contains(utc("2026-07-04T01:00"))  # Friday's session.
    assert not overnight.contains(utc("2026-07-05T01:00"))
    gap = Session("Invalid", "America/New_York", 2 * 60 + 30, 4 * 60)
    with pytest.raises(DataQualityError, match="DST gap"):
        gap.window(date(2026, 3, 8))
    repeated = Session("Repeated", "America/New_York", 60, 120)
    start, end = repeated.window(date(2026, 11, 1))
    assert (end - start).total_seconds() == 7200
