"""Prepare this explicitly selected MetaQuotes Demo's research profile, without trading."""

import json
import math
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np

from aurum_backend.analysis.structure import atr
from aurum_backend.data.bars import Bar


def offset_minutes(at: datetime, zone: ZoneInfo) -> int:
    delta = at.astimezone(zone).utcoffset()
    if delta is None:
        raise ValueError("Explicit timezone offset unavailable")
    return int(delta.total_seconds() / 60)


def main() -> None:
    import MetaTrader5 as mt5

    if not mt5.initialize(r"C:\Program Files\MetaTrader 5\terminal64.exe", timeout=10000):
        raise SystemExit("Connected MT5 unavailable")
    try:
        account = mt5.account_info()
        if account is None or account.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
            raise SystemExit("Demo required")
        if account.server != "MetaQuotes-Demo":
            raise SystemExit("This timezone profile is only for MetaQuotes-Demo")
        now = datetime.now(UTC)
        zone = ZoneInfo("Europe/Helsinki")
        offset = offset_minutes(now, zone)
        tick = mt5.symbol_info_tick("XAUUSD")
        if tick is None or not -5 <= now.timestamp() - (tick.time - offset * 60) <= 30:
            raise SystemExit("Fresh quote does not match the declared EET/EEST broker policy")
        rates = mt5.copy_rates_from_pos("XAUUSD", mt5.TIMEFRAME_M15, 1, 20000)
        if rates is None or len(rates) < 10000:
            raise SystemExit("Insufficient broker training history")
        # Fixed chronological split. Validation/OOS are not used for threshold selection.
        train = rates[: int(len(rates) * 0.6)]
        bars = [
            Bar(
                int(r["time"]),
                float(r["open"]),
                float(r["high"]),
                float(r["low"]),
                float(r["close"]),
            )
            for r in train
        ]
        values = atr(bars, 14)
        ratios = []
        for i in range(114, len(values)):
            prior = values[i - 100 : i]
            current_atr = values[i]
            known = [x for x in prior if x is not None]
            if len(known) != len(prior) or current_atr is None:
                continue
            median = float(np.median(known))
            if median > 0:
                ratios.append(current_atr / median)
        spread = math.ceil(float(np.quantile(train["spread"], 0.9)))
        low, high = (float(x) for x in np.quantile(ratios, [0.1, 0.95]))
        common = Path(os.environ["APPDATA"]) / "MetaQuotes/Terminal/Common/Files/Aurum"
        common.mkdir(parents=True, exist_ok=True)
        # Explicit EET/EEST policy, supported by published MetaQuotes statement and
        # verified against today's fresh quote. Not a historical timestamp certificate.
        start = datetime(2025, 1, 1, tzinfo=UTC)
        finish = datetime(2028, 1, 1, tzinfo=UTC)
        rows = ["server_start,server_end,offset_minutes"]
        segment = start
        previous = offset_minutes(start, zone)
        cursor = start
        while cursor <= finish:
            current = offset_minutes(cursor, zone)
            if current != previous or cursor == finish:
                # Both transitions occur Sunday while gold is closed. Use one
                # contiguous server-time boundary; no traded ambiguity is invented.
                wall_start = segment.replace(tzinfo=None) + timedelta(minutes=previous)
                wall_end = cursor.replace(tzinfo=None) + timedelta(minutes=previous)
                rows.append(
                    f"{wall_start:%Y.%m.%d %H:%M:%S},{wall_end:%Y.%m.%d %H:%M:%S},{previous}"
                )
                segment = cursor + timedelta(minutes=previous - current)
                previous = current
            cursor += timedelta(hours=1)
        (common / "broker_clock.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
        data = Path(mt5.terminal_info().data_path)
        preset = data / "MQL5/Presets/AurumDemoSignal.set"
        preset.parent.mkdir(parents=True, exist_ok=True)
        settings = {
            "Mode": 0,
            "ConfirmDemoAutoExecute": "false",
            "TradingSymbol": "XAUUSD",
            "Magic": 260110,
            "CostsKnown": "true",
            "CommissionRoundTripPerLot": 0,
            "SlippagePoints": 0,
            "MaxSpreadPoints": spread,
            "AtrRatioLow": f"{low:.10f}",
            "AtrRatioHigh": f"{high:.10f}",
            "NativeNewsEnabled": "true",
            "BrokerClockCsv": "Aurum\\broker_clock.csv",
            "BridgeEnabled": "true",
            "RequirePythonHeartbeat": "true",
        }
        preset.write_text(
            "\n".join(f"{k}={v}" for k, v in settings.items()) + "\n", encoding="utf-16"
        )
        report = {
            "symbol": "XAUUSD",
            "train_bars": len(train),
            "total_bars": len(rates),
            "split": "60% train / 20% validation / 20% untouched OOS",
            "spread_p90_points": spread,
            "atr_ratio_p10": low,
            "atr_ratio_p95": high,
            "cost_assumption": "user explicitly requested commission=0 slippage=0; unverified",
            "clock_policy": "EET/EEST Europe/Helsinki; current quote verified; historical model",
            "clock_source": "https://www.mql5.com/en/forum/63796#comment_1866855",
            "preset": str(preset),
            "orders_submitted": False,
        }
        out = Path(".evidence/mvp/preparation.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
