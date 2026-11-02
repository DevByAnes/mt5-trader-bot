import pytest

from aurum_backend.analysis.counterfactual import evaluate
from aurum_backend.data.bars import Bar


def test_ambiguous_bar_uses_conservative_stop_and_unknown_costs() -> None:
    bars = [Bar(0, 10, 13, 8, 10)]
    result = evaluate("BUY", 10, 9, 12, bars, start=0, expiry=900, as_of=900)
    assert result.status == "SL" and result.gross_r == -1 and result.ambiguous
    assert result.net_r is None


def test_complete_m1_can_resolve_the_sequence() -> None:
    coarse = [Bar(0, 10, 13, 8, 10)]
    fine = [Bar(i * 60, 10, 10.5, 9.5, 10) for i in range(15)]
    fine[0] = Bar(0, 10, 13, 9.5, 12)
    fine[1] = Bar(60, 10, 10.5, 8, 9)
    result = evaluate(
        "BUY", 10, 9, 12, coarse, start=0, expiry=900, as_of=900, m1=fine, costs_r=0.2
    )
    assert result.status == "TP" and result.resolved_at == 60 and result.net_r == 1.8
    incomplete = evaluate("BUY", 10, 9, 12, coarse, start=0, expiry=900, as_of=900, m1=fine[:-1])
    assert incomplete.status == "SL" and incomplete.ambiguous


def test_no_history_is_not_a_zero_return() -> None:
    result = evaluate("SELL", 10, 11, 8, [], start=0, expiry=900, as_of=900)
    assert result.status == "UNAVAILABLE" and result.gross_r is None


def test_expiry_requires_an_observed_close_at_the_deadline() -> None:
    bars = [Bar(0, 10, 10.5, 9.5, 10.2)]
    known = evaluate("BUY", 10, 9, 12, bars, start=0, expiry=900, as_of=900)
    assert known.status == "EXPIRED"
    missing = evaluate("BUY", 10, 9, 12, bars, start=0, expiry=1800, as_of=1800)
    assert missing.status == "UNAVAILABLE"


def test_missing_interval_cannot_produce_a_later_target() -> None:
    bars = [Bar(0, 10, 10.5, 9.5, 10), Bar(1800, 10, 13, 9.5, 12)]
    outcome = evaluate("BUY", 10, 9, 12, bars, start=0, expiry=2700, as_of=2700)
    assert outcome.status == "UNAVAILABLE" and outcome.gross_r is None


def test_inconsistent_m1_cannot_override_conservative_order() -> None:
    coarse = [Bar(0, 10, 13, 8, 10)]
    fine = [Bar(i * 60, 10, 12, 9.5, 10) for i in range(15)]
    outcome = evaluate("BUY", 10, 9, 12, coarse, start=0, expiry=900, as_of=900, m1=fine)
    assert outcome.status == "SL" and outcome.ambiguous


@pytest.mark.parametrize("cost", [float("nan"), float("inf"), -0.1])
def test_nonfinite_or_negative_costs_are_rejected(cost: float) -> None:
    with pytest.raises(ValueError):
        evaluate("BUY", 10, 9, 12, [], start=0, expiry=900, as_of=900, costs_r=cost)
