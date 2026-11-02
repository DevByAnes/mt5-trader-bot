"""Read-only acceptance of an already connected MT5 Demo account; never submits orders."""

import argparse
import json
import math
import time
from datetime import UTC, datetime, timedelta
from itertools import pairwise
from pathlib import Path
from typing import Any
from uuid import uuid4

from aurum_backend.data.clock import inspect_quote_clock
from aurum_backend.data.mt5_readonly import ReadOnlyTerminal
from aurum_backend.data.parquet import read_bars, write_bars

ROOT = Path(__file__).resolve().parents[2]


def positive(value: Any, label: str) -> float:
    if value is None or not math.isfinite(float(value)) or float(value) <= 0:
        raise RuntimeError(label + " unavailable or invalid")
    return float(value)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--terminal", default=r"C:\Program Files\MetaTrader 5\terminal64.exe")
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--source-offset-minutes", type=int, default=0)
    args = parser.parse_args()
    if "XAUUSD" not in args.symbol.upper():
        raise SystemExit("Only an explicitly named XAUUSD symbol is supported")
    # Diagnostic-only import: no execution/check/modification capability is imported.
    from MetaTrader5 import (
        ACCOUNT_MARGIN_MODE_RETAIL_HEDGING,
        ACCOUNT_TRADE_MODE_DEMO,
        ORDER_TYPE_BUY,
        ORDER_TYPE_SELL,
        account_info,
        order_calc_margin,
        order_calc_profit,
        symbol_info,
        symbol_info_tick,
        symbol_select,
        terminal_info,
    )

    terminal = ReadOnlyTerminal(args.terminal, source_utc_offset_minutes=args.source_offset_minutes)
    evidence = ROOT / "backend/.evidence/demo" / uuid4().hex
    try:
        connection = terminal_info()
        account = account_info()
        if connection is None or not connection.connected:
            raise RuntimeError("MT5 is not connected")
        if account is None or account.trade_mode != ACCOUNT_TRADE_MODE_DEMO:
            raise RuntimeError("This diagnostic requires a Demo account; no account was changed")
        initial_identity = (account.login, account.server)
        spec = symbol_info(args.symbol)
        if spec is None:
            raise RuntimeError("Requested broker gold symbol does not exist")
        if not spec.visible and not symbol_select(args.symbol, True):
            raise RuntimeError("Cannot subscribe to requested gold symbol")
        tick = symbol_info_tick(args.symbol)
        if tick is None:
            raise RuntimeError("No gold quote available")
        now = datetime.now(UTC)
        clock = inspect_quote_clock(
            float(tick.time_msc) / 1000 - args.source_offset_minutes * 60, now.timestamp()
        )
        bars = []
        for _ in range(10):
            try:
                bars = terminal.m15(args.symbol, now - timedelta(hours=12), now, as_of=now)
            except ValueError:
                bars = []
            if bars:
                break
            time.sleep(1)
        if not bars:
            raise RuntimeError("No validated closed M15 bars available")
        evidence.mkdir(parents=True)
        parquet_roundtrip = None
        if clock.usable:
            cache = evidence / "gold-m15.parquet"
            write_bars(cache, bars, timeframe_seconds=900, as_of=int(now.timestamp()))
            parquet_roundtrip = (
                read_bars(cache, timeframe_seconds=900, as_of=int(now.timestamp())) == bars
            )
            if not parquet_roundtrip:
                raise RuntimeError("Real market-data Parquet round-trip mismatch")
        ask, bid = positive(tick.ask, "ask"), positive(tick.bid, "bid")
        if ask < bid:
            raise RuntimeError("Crossed quote")
        step = positive(spec.trade_tick_size, "tick size")
        point = positive(spec.point, "point")
        volume = positive(spec.volume_min, "minimum volume")
        positive(spec.volume_step, "volume step")
        if positive(spec.volume_max, "maximum volume") < volume:
            raise RuntimeError("Inconsistent volume limits")
        # Fixed diagnostic movement/volume, not a signal, target or live position sizing decision.
        distance = 100 * step
        estimates = []
        for side, label, entry, direction in [
            (ORDER_TYPE_BUY, "BUY", ask, 1),
            (ORDER_TYPE_SELL, "SELL", bid, -1),
        ]:
            favorable = positive(
                order_calc_profit(side, args.symbol, volume, entry, entry + direction * distance),
                "favorable profit estimate",
            )
            adverse = order_calc_profit(
                side, args.symbol, volume, entry, entry - direction * distance
            )
            if adverse is None or not math.isfinite(adverse) or adverse >= 0:
                raise RuntimeError("Adverse profit estimate unavailable or invalid")
            margin = positive(
                order_calc_margin(side, args.symbol, volume, entry), "margin estimate"
            )
            estimates.append(
                {
                    "side": label,
                    "profit_signs_valid": True,
                    "margin_valid": True,
                    "favorable": favorable,
                    "adverse": adverse,
                    "margin": margin,
                }
            )
        final_account = account_info()
        if final_account is None or (final_account.login, final_account.server) != initial_identity:
            raise RuntimeError("Account changed during acceptance; discard results")
        report = {
            "checked_at_utc": datetime.now(UTC).isoformat(),
            "terminal_build": connection.build,
            "account_type": "DEMO",
            "margin_mode": "HEDGING"
            if account.margin_mode == ACCOUNT_MARGIN_MODE_RETAIL_HEDGING
            else "NETTING_OR_EXCHANGE",
            "account_currency": account.currency,
            "balance": account.balance,
            "equity": account.equity,
            "terminal_trade_allowed": connection.trade_allowed,
            "symbol": args.symbol,
            "symbol_rules": {
                "digits": spec.digits,
                "point": point,
                "tick_size": step,
                "volume_min": volume,
                "volume_max": spec.volume_max,
                "volume_step": spec.volume_step,
                "stops_points": spec.trade_stops_level,
                "freeze_points": spec.trade_freeze_level,
                "filling_flags": spec.filling_mode,
                "trade_mode": spec.trade_mode,
            },
            "quote_age_seconds": clock.age_seconds,
            "source_clock_status": clock.status,
            "explicit_source_offset_minutes": args.source_offset_minutes,
            "history_utc_accepted": clock.usable,
            "acceptance": "READS_ONLY" if clock.usable else "BLOCKED_SOURCE_CLOCK",
            "spread_points": (ask - bid) / point,
            "closed_m15_bars": len(bars),
            "last_bar_timestamp_as_reported": bars[-1].time,
            "history_gaps": sum(b.time - a.time != 900 for a, b in pairwise(bars)),
            "parquet_roundtrip": parquet_roundtrip,
            "broker_estimates": estimates,
            "commission_slippage_known": False,
            "orders_submitted": False,
            "project_ea_status": "NOT_IMPLEMENTED",
        }
        # Keep financial values, quotes and raw data local. Never record login/name/server/password.
        (evidence / "summary.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(report, indent=2))
        print("Local evidence:", evidence)
        if not clock.usable:
            raise SystemExit(2)
    finally:
        terminal.close()  # Disconnects this SDK client; does not close MT5.


if __name__ == "__main__":
    main()
