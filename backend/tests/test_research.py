from datetime import UTC, datetime
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from aurum_backend.analysis.metrics import Observation, grouped, max_drawdown, summarize
from aurum_backend.analysis.structure import atr, confirmed_swings
from aurum_backend.data.bars import Bar, DataQualityError, validate_closed
from aurum_backend.data.mt5_readonly import ReadOnlyTerminal, TerminalReads
from aurum_backend.data.parquet import read_bars, write_bars
from aurum_backend.validation.offline import monte_carlo_r, walk_forward


def bars() -> list[Bar]:
    return [
        Bar(i * 900, x, x + 1, x - 1, x, 20) for i, x in enumerate([10, 11, 14, 12, 11, 9, 10, 13])
    ]


def test_metrics_preserve_unknown_and_cash_units() -> None:
    empty = summarize([])
    assert empty.known_outcomes == 0 and empty.mean_r is None and empty.profit_factor is None
    rows = [
        Observation("a", "BUY", "London", "trend", 2, 20, "USD"),
        Observation("b", "SELL", "London", "trend", -1, -40, "USD"),
    ]
    result = summarize(rows)
    assert result.mean_r == 0.5 and result.profit_factor == 0.5 and result.profit_factor_r == 2
    assert grouped(rows)["side"]["BUY"]["known_outcomes"] == 1
    unknown = summarize([Observation("c", "BUY", "London", "unknown", None)])
    assert unknown.mean_r is None and unknown.unavailable_outcomes == 1
    assert summarize([Observation("d", "BUY", "London", "trend", 2)]).profit_factor is None
    with pytest.raises(ValueError, match="Duplicate"):
        summarize([rows[0], rows[0]])


def test_observed_cash_factor_does_not_require_a_known_initial_risk() -> None:
    result = summarize(
        [
            Observation("win", "BUY", "LONDON", "NORMAL", None, 20, "USD"),
            Observation("loss", "SELL", "NEW_YORK", "NORMAL", None, -10, "USD"),
        ]
    )
    assert result.profit_factor == 2
    assert result.known_outcomes == 0
    assert result.mean_r is None and result.win_rate is None


def test_equity_drawdown_is_not_inferred_from_missing_data() -> None:
    assert max_drawdown([100, 120, 90, 110]) == 0.25
    assert max_drawdown([100, None]) is None
    assert max_drawdown([]) is None
    with pytest.raises(ValueError):
        max_drawdown([100, 0])


def test_parquet_roundtrip_and_closed_bar_guard(tmp_path: Path) -> None:
    path = tmp_path / "gold.parquet"
    value = bars()
    write_bars(path, value, timeframe_seconds=900, as_of=7200)
    assert read_bars(path, timeframe_seconds=900, as_of=7200) == value
    with pytest.raises(DataQualityError, match="timeframe"):
        read_bars(path, timeframe_seconds=3600, as_of=7200)
    with pytest.raises(DataQualityError, match="Open or future"):
        validate_closed(value, timeframe_seconds=900, as_of=6300)


def test_swing_confirmation_has_no_lookahead_on_prefixes() -> None:
    value = bars()
    full = confirmed_swings(value, left=2, right=2)
    for end in range(1, len(value) + 1):
        known_at = value[end - 1].time + 900
        expected = [s for s in full if s.confirmed_at <= known_at]
        assert confirmed_swings(value[:end], left=2, right=2) == expected
    assert all(s.confirmed_at > s.occurred_at for s in full)
    output = atr(value, 3)
    assert output[:2] == [None, None]
    for end in range(1, len(value) + 1):
        assert atr(value[:end], 3) == output[:end]


@given(st.lists(st.floats(min_value=-10, max_value=10, allow_nan=False), min_size=1, max_size=30))
def test_monte_carlo_seed_and_cost_stress(outcomes: list[float]) -> None:
    first = monte_carlo_r(outcomes, seed=42, paths=30)
    assert first == monte_carlo_r(outcomes, seed=42, paths=30)
    stressed = monte_carlo_r(outcomes, seed=42, paths=30, costs_r=0.1)
    assert stressed["terminal_r_p50"] <= first["terminal_r_p50"]


def test_walk_forward_splits_are_chronological_and_purged() -> None:
    folds = walk_forward(100, 30, 10, gap=3)
    assert folds
    for fold in folds:
        assert fold.train_start < fold.train_end < fold.test_start < fold.test_end <= 100
        assert fold.test_start - fold.train_end == 3


def test_read_only_adapter_uses_explicit_data_capability() -> None:
    closed = []
    values = [
        {"time": 0, "open": 10, "high": 11, "low": 9, "close": 10, "tick_volume": 4},
        {"time": 900, "open": 10, "high": 11, "low": 9, "close": 10, "tick_volume": 4},
    ]
    reads = TerminalReads(
        lambda path: path == "demo-terminal",
        lambda: closed.append(True),
        lambda symbol, tf, start, end: values,
        15,
    )
    terminal = ReadOnlyTerminal("demo-terminal", reads)
    result = terminal.m15(
        "XAUUSD.a",
        datetime.fromtimestamp(0, UTC),
        datetime.fromtimestamp(1200, UTC),
        as_of=datetime.fromtimestamp(1200, UTC),
    )
    assert len(result) == 1 and result[0].time == 0
    terminal.close()
    assert closed == [True]
