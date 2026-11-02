import pytest

from aurum_backend.data.clock import inspect_quote_clock


@pytest.mark.parametrize("age", [-5, 0, 10, 120])
def test_quote_clock_accepts_only_bounded_fresh_observations(age: float) -> None:
    result = inspect_quote_clock(10000 - age, 10000)
    assert result.usable and result.age_seconds == age


def test_future_broker_clock_is_not_silently_rebased() -> None:
    result = inspect_quote_clock(17200, 10000)
    assert result.status == "FUTURE_QUOTE" and not result.usable
    assert result.age_seconds == -7200


def test_stale_quote_is_not_a_current_price() -> None:
    assert inspect_quote_clock(9879, 10000).status == "STALE_QUOTE"


@pytest.mark.parametrize("timestamp", [0, -1, float("nan"), float("inf"), True])
def test_invalid_source_clock_stays_unavailable(timestamp: float) -> None:
    result = inspect_quote_clock(timestamp, 10000)
    assert result.status == "INVALID_TIMESTAMP"
    assert result.age_seconds is None
