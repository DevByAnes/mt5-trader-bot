# Native MQL5 modules — compiled and tested; EA acceptance pending

`Include/Aurum/GeneratedInputs.mqh` is generated from the draft v2 shared input catalog, with grouped native enum inputs, default values, range/step checks and JSON serialization. `Economics.mqh` implements account-currency loss/volume/margin estimates and a cost-adjusted target search for minimum net RR 2. Entry uses the actual side-specific quote, so spread already represented by entry/exit prices must not be charged a second time. Commission/slippage estimates must be known, conservative and expressed in account currency. Unknown estimates must block entry.

These are native **foundation modules and scripts**, not a finished EA. Both scripts compiled with zero errors/warnings and ran on installed MT5 build 6295 on 2026-11-02. The main EA's setup registry, autonomous execution/management, persistence, signed FILE consumer and tester harness remain checklist work. No current file starts an automated trading EA. The input `.mqh` contains no keys or tokens.

To reproduce on Windows, from `backend/` run:

```powershell
python -m uv run python -m tools.native_check --installation "C:\Program Files\MetaTrader 5"
```

The runner compiles both scripts, fails on any warning/error or missing EX5, creates a fresh portable terminal with no user credentials/profiles, disables trading/DLL imports, runs the scripts and validates their JSON output in Python. It leaves the user's open terminal untouched. It uses only the installed executable and installation seed symbols; no Demo account or market history is required. It closes only the processes it launches. Raw results/compiler logs stay in ignored `backend/.evidence/native/<run-id>/`; a sanitized [acceptance snapshot](../docs/evidence/native/mt5-build-6295.json) is tracked.

Verified: 94 default values match the shared schema, Unicode/control escaping round-trips, four invalid input presets are rejected (Magic, RR below 2, off-step risk, invalid mode), and nine economic/invalid-input vectors pass. These economic vectors do **not** verify broker-dependent OrderCalcProfit/OrderCalcMargin results. Live quotes, broker rules, actual volume/TP/margin calculations, Strategy Tester and Demo E2E remain unverified until a Demo account is connected and the main EA exists. See [the native test report](../docs/NATIVE_TESTS.fa.md).
