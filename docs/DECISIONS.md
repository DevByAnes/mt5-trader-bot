# Architecture and behavior decisions

## ADR-01 — ownership (user prompt, 2026-11-02)

EA owns independent execution/risk/position management in MQL5. Python owns bridge, data, analysis, validation, storage and local API. Existing Tauri/React UI is retained. Python and JS never submit execution entries or calculate position sizing for live trades.

## ADR-02 — net reward/risk (explicit user answer, 2026-11-02)

The user chose **net RR ≥ 2, with TP adjusted for costs**. This supersedes the conflicting gross TP=2R condition in the pasted prompt. For positive estimated costs, the target must cover those costs as well as the net reward relative to estimated total loss. The EA must use account-currency estimates, broker constraints and conservative cost assumptions; unknown costs or an obstructed valid target produce a rejection. Actual fills may differ from estimates; no guaranteed realized ratio is claimed. Python's offline reference may test this rule but is never on the live sizing/execution path.

## ADR-03 — progress without a terminal (explicit user question, 2026-11-02)

Continue source implementation and tests using deterministic data and signed peer simulation. MT5 installation is not required to write the code. Native compile, Strategy Tester, broker retcodes/stops/freeze/filling behavior, actual netting/hedging and demo E2E remain unverified until a terminal/compiler is supplied. No such gate is silently marked passed. SIGNAL_ONLY is the default; native LIVE activation still requires its explicit gates and demo/forward acceptance.

Update, 2026-11-02: user installed MT5/MetaEditor. Build 6295 compiled and ran the two existing non-trading test scripts in an isolated, account-free portable instance. The generated inputs and independent economic vectors pass. User confirmed no Demo account is connected. This clears the script-compilation gate only; the main EA, broker-dependent tests, Tester and Demo E2E remain outstanding. See `NATIVE_TESTS.fa.md`.
