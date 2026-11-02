"""Full EA input catalog; v1's six public settings remain compatibility-only."""

import json
from pathlib import Path
from typing import Any


def main() -> None:
    fields: dict[str, Any] = {}

    def add(
        name: str,
        default: Any,
        group: str,
        *,
        low: float | None = None,
        high: float | None = None,
        step: float | None = None,
        choices: list[str] | None = None,
        apply: str = "HOT",
        risk: str = "MEDIUM",
        direction: str = "NONE",
        locked: bool = False,
        label: str = "",
        help_text: str = "",
    ) -> None:
        kind = (
            "boolean"
            if isinstance(default, bool)
            else "integer"
            if isinstance(default, int)
            else ("number" if isinstance(default, float) else "string")
        )
        item = {
            "key": name,
            "type": kind,
            "default": default,
            "min": low,
            "max": high,
            "step": step,
            "enum": choices,
            "group": group,
            "apply": apply,
            "risk_level": risk,
            "risk_direction": direction,
            "mt5_only": locked,
            "label_i18n": {"en": label or name, "fa": label or name},
            "help_i18n": {
                "en": help_text or "Experimental input; validate on Demo/Forward data.",
                "fa": "ورودی آزمایشی؛ پیش از LIVE با Demo و Forward بررسی شود.",
            },
        }
        if choices is None:
            item.pop("enum")
        if low is not None:
            item.update(minimum=low, maximum=high, multipleOf=step)
        if kind == "string":
            item.update(minLength=1, maxLength=128)
        fields[name] = item

    add(
        "InpExecutionMode",
        "SIGNAL_ONLY",
        "execution",
        choices=["SIGNAL_ONLY", "PAPER", "LIVE"],
        apply="COLD",
        risk="HIGH",
        label="Execution mode",
    )
    for key in [
        "InpConfirmLive",
        "InpAllowRealAccount",
        "InpAllowRemoteConfig",
        "InpAllowLiveFromConfig",
    ]:
        add(key, False, "execution", apply="COLD", risk="HIGH", locked=True)
    add("InpSymbol", "XAUUSD", "execution", apply="COLD", locked=True, label="Gold symbol")
    add("InpMagic", 260110, "execution", low=1, high=2147483647, step=1, apply="COLD", locked=True)
    add("InpDeviationPoints", 20, "execution", low=0, high=100, step=1)
    add("InpKillSwitch", False, "execution", risk="HIGH", locked=True)
    add("InpCapitalBasis", "EQUITY", "risk", choices=["EQUITY", "BALANCE"], apply="COLD")
    add(
        "InpRiskProfile",
        "CONSERVATIVE",
        "risk",
        choices=["CONSERVATIVE", "MODERATE", "AGGRESSIVE", "CUSTOM"],
    )
    add(
        "InpRiskPerTrade",
        0.5,
        "risk",
        low=0.1,
        high=2,
        step=0.1,
        risk="HIGH",
        direction="HIGHER_IS_LOOSER",
    )
    add(
        "InpMaxTradesPerDay",
        8,
        "risk",
        low=1,
        high=20,
        step=1,
        risk="HIGH",
        direction="HIGHER_IS_LOOSER",
    )
    add(
        "InpMaxSimultaneous",
        1,
        "risk",
        low=1,
        high=3,
        step=1,
        risk="HIGH",
        direction="HIGHER_IS_LOOSER",
    )
    add(
        "InpMinMarginLevel",
        300,
        "risk",
        low=100,
        high=2000,
        step=10,
        risk="HIGH",
        direction="LOWER_IS_LOOSER",
    )
    add(
        "InpDailyLossLimit",
        2.0,
        "daily",
        low=0.5,
        high=5,
        step=0.1,
        risk="HIGH",
        direction="HIGHER_IS_LOOSER",
    )
    add(
        "InpDailyProfitTarget",
        3.0,
        "daily",
        low=0.5,
        high=10,
        step=0.1,
        direction="HIGHER_IS_LOOSER",
    )
    add("InpForceCloseDailyLoss", False, "daily", risk="HIGH", locked=True)
    add("InpTradingDayStartUtcHour", 0, "daily", low=0, high=23, step=1, apply="COLD", locked=True)
    add("InpBreakEvenEnabled", True, "management")
    add("InpBreakEvenTriggerR", 1.0, "management", low=0.5, high=2, step=0.1)
    add("InpBreakEvenBufferAtr", 0.05, "management", low=0, high=0.3, step=0.01)
    add("InpPartialCloseEnabled", False, "management")
    add("InpPartialCloseAtR", 1.5, "management", low=0.5, high=3, step=0.1)
    add("InpPartialClosePercent", 50, "management", low=10, high=80, step=10)
    add("InpTrailingEnabled", False, "management")
    add("InpTrailingAtr", 1.5, "management", low=0.5, high=4, step=0.1)
    add("InpMaxHoldingHours", 24, "management", low=1, high=24, step=1)
    for key in ["InpPreNewsAction", "InpPreWeekendAction"]:
        add(key, "BREAK_EVEN", "management", choices=["NONE", "BREAK_EVEN", "CLOSE"])
    add("InpAbnormalAction", "ALERT", "management", choices=["NONE", "ALERT", "BREAK_EVEN"])
    for key in ["InpLondonEnabled", "InpOverlapEnabled", "InpNewYorkEnabled"]:
        add(key, True, "sessions")
    for prefix, start, end in [("London", 480, 660), ("Overlap", 780, 1020), ("NewYork", 480, 690)]:
        # Local civil minutes; each named zone applies its own DST rule.
        for boundary, value in [("Start", start), ("End", end)]:
            add(f"Inp{prefix}{boundary}Minute", value, "sessions", low=0, high=1435, step=5)
    add("InpEndOfDayEntryBufferMinutes", 30, "sessions", low=5, high=120, step=5)
    add("InpWeekendEntryBufferMinutes", 120, "sessions", low=30, high=360, step=15)
    add(
        "InpBrokerOffsetMode",
        "AUTO",
        "sessions",
        choices=["AUTO", "MANUAL"],
        apply="COLD",
        locked=True,
    )
    add(
        "InpBrokerUtcOffsetMinutes",
        120,
        "sessions",
        low=-720,
        high=840,
        step=15,
        apply="COLD",
        locked=True,
    )
    add("InpNewsFilterEnabled", True, "filters")
    add("InpNewsBeforeMinutes", 30, "filters", low=5, high=120, step=5, direction="LOWER_IS_LOOSER")
    add("InpNewsAfterMinutes", 30, "filters", low=5, high=120, step=5, direction="LOWER_IS_LOOSER")
    add("InpTesterNewsCsv", "aurum_news_test.csv", "filters", apply="COLD", locked=True)
    add("InpMaxSpreadPoints", 35, "filters", low=5, high=100, step=1, direction="HIGHER_IS_LOOSER")
    add(
        "InpMaxSpreadAtr",
        0.1,
        "filters",
        low=0.01,
        high=0.5,
        step=0.01,
        direction="HIGHER_IS_LOOSER",
    )
    add(
        "InpMaxSpreadStopRatio",
        0.1,
        "filters",
        low=0.01,
        high=0.3,
        step=0.01,
        direction="HIGHER_IS_LOOSER",
    )
    add("InpCostsKnown", False, "costs", risk="HIGH", locked=True)
    add("InpCommissionRoundTripPerLot", 0.0, "costs", low=0, high=100, step=0.1, locked=True)
    add("InpSlippagePoints", 10, "costs", low=0, high=100, step=1, locked=True)
    add(
        "InpMinNetRR",
        2.0,
        "costs",
        low=2,
        high=3,
        step=0.1,
        risk="HIGH",
        direction="LOWER_IS_LOOSER",
    )
    add("InpAtrPeriod", 14, "signals", low=5, high=50, step=1, apply="COLD")
    add("InpEmaPeriod", 200, "signals", low=50, high=400, step=10, apply="COLD")
    add("InpRsiPeriod", 14, "signals", low=5, high=30, step=1, apply="COLD")
    add("InpRsiUpper", 75, "signals", low=55, high=90, step=1)
    add("InpRsiLower", 25, "signals", low=10, high=45, step=1)
    add("InpAdxMin", 20, "signals", low=10, high=40, step=1)
    add("InpSwingLeft", 2, "signals", low=1, high=10, step=1, apply="COLD")
    add("InpSwingRight", 2, "signals", low=1, high=10, step=1, apply="COLD")
    add("InpReversalEnabled", True, "setups")
    add("InpContinuationEnabled", True, "setups")
    add("InpSweepAtr", 0.15, "setups", low=0.05, high=1, step=0.05)
    add("InpSweepConfirmBars", 3, "setups", low=1, high=3, step=1)
    add("InpDisplacementAtr", 0.8, "setups", low=0.5, high=2, step=0.1)
    add("InpBodyRatio", 0.6, "setups", low=0.5, high=0.9, step=0.05)
    add("InpRetestMinBars", 3, "setups", low=1, high=5, step=1)
    add("InpRetestMaxBars", 10, "setups", low=5, high=20, step=1)
    add("InpZoneWidthAtr", 0.2, "setups", low=0.1, high=0.3, step=0.05)
    add("InpMaxLevelTouches", 3, "setups", low=1, high=10, step=1)
    add("InpMaxLevelAgeBars", 96, "setups", low=4, high=480, step=1)
    add("InpStopBufferAtr", 0.1, "setups", low=0.05, high=0.5, step=0.05)
    add("InpMinStopAtr", 0.3, "setups", low=0.1, high=1, step=0.1)
    add("InpMaxStopAtr", 3.0, "setups", low=1, high=5, step=0.1)
    add("InpMaxSignalRangeAtr", 2.5, "setups", low=1, high=4, step=0.1)
    add("InpMaxAdrFraction", 0.8, "setups", low=0.3, high=1, step=0.05)
    add("InpCooldownAfterSlBars", 4, "setups", low=1, high=24, step=1, direction="LOWER_IS_LOOSER")
    for key in ["InpLogFvg", "InpLogOrderBlock", "InpLogCandlePatterns", "InpUseDxyFeature"]:
        add(key, False, "experimental")
    add(
        "InpBridgeMode",
        "FILE",
        "bridge",
        choices=["OFF", "FILE", "HTTP_LOCAL"],
        apply="COLD",
        locked=True,
    )
    add(
        "InpBridgeFailPolicy",
        "CONTINUE_WITHOUT",
        "bridge",
        choices=["CONTINUE_WITHOUT", "BLOCK_NEW_ENTRIES"],
        locked=True,
    )
    add(
        "InpConfigSource", "INPUTS", "bridge", choices=["INPUTS", "FILE"], apply="COLD", locked=True
    )
    add("InpTimerSeconds", 2, "bridge", low=1, high=10, step=1)
    for key, value in [
        ("InpAlertEnabled", True),
        ("InpPushEnabled", False),
        ("InpEmailEnabled", False),
        ("InpTelegramEnabled", False),
        ("InpDebugDeterminism", False),
        ("InpMlEnabled", False),
    ]:
        add(key, value, "notifications" if "Enabled" in key and "Ml" not in key else "experimental")
    root = Path(__file__).resolve().parents[2]
    result = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "EASettings",
        "type": "object",
        "additionalProperties": False,
        "schema_version": "2.0.0",
        "required": list(fields),
        "properties": fields,
        "x-policy": {
            "net_rr": "COST_ADJUSTED_MINIMUM",
            "min_net_rr": 2,
            "live_default": False,
            "loosening": "SECOND_CONFIRMATION_NEXT_DAY",
        },
    }
    (root / "schema/settings.v2.schema.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
