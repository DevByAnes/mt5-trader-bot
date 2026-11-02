# Native MQL5 artifacts — acceptance pending

`Include/Aurum/GeneratedInputs.mqh` is generated from the draft v2 shared input catalog, with grouped native enum inputs, default values, range/step checks and JSON serialization. `Economics.mqh` implements account-currency loss/volume/margin estimates and a cost-adjusted target search for minimum net RR 2. Entry uses the actual side-specific quote, so spread already represented by entry/exit prices must not be charged a second time. Commission/slippage estimates must be known, conservative and expressed in account currency. Unknown estimates must block entry.

These are native **foundation modules and scripts**, not a finished EA or a claim of native compilation. The main EA's setup registry, autonomous execution/management, persistence, signed FILE consumer and tester harness remain checklist work. No current file starts an automated trading EA. The input `.mqh` contains no keys or tokens.

After installing MetaEditor, compile `Tests/InputsTest.mq5` and `Tests/EconomicsTest.mq5` with zero errors/warnings, run them on a Demo terminal, and compare the input JSON to the shared schema. Native compilation and test results are currently unverified. The Python suite verifies generation consistency; economic vectors are defined in the unexecuted native scripts. Do not treat a text/syntax check as a native compile.
