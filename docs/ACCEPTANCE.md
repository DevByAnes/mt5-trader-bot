# Acceptance report — 2026-11-02

| Criterion | Result | Evidence / limits |
|---|---|---|
| Baseline audit before implementation | PASS | `AUDIT.md`; staged commits retain contract → settings → UI sequence |
| Versioned OpenAPI, generated types and drift rejection | PASS | `contract:check`, named models and fixtures for every response |
| Eight event payload contracts | PASS | Event fixtures validated; simulator emits heartbeat, signal and operation-driven events |
| All requested development scenarios | PASS | Fourteen scenarios; twenty browser tests exercise settings, commands, transport, daily stops, positions and spread |
| Settings machine / metadata validation | PASS | Guarded transitions; min/max/step/enum validation; nine unit tests include transport recovery |
| Frozen reviewed values / second confirmation / locks | PASS | Browser verifies immutable reviewed draft and backend enforcement of MT5-only values |
| Ack-only success / unknown timeout | PASS | APPLIED requires EA timestamp; Timeout remains unknown; no automatic mutation retry |
| Idempotency and concurrent settings versions | PASS | Browser tests same-key replay, mismatched payload, key-based lookup and concurrent version conflict |
| Rollback | PASS | Historical snapshot becomes a new draft; validation, review and Ack required |
| Persistent emergency controls | PASS | Header outside routes; offline/stale sends disabled; command result correlated by request |
| Daily risk, positions, M15 levels, context, decision feed | PASS | Server values; no frontend lot/risk/RR calculation; daily rejection aggregation supplied by server |
| Overview at 1440×900 without page scroll | PASS | Browser checks document height ≤ 900; compact design |
| English/Persian and RTL/LTR / independent digits / themes | PASS with limits | Browser tests directions, Persian heading/digits and theme. Backend enum/reason codes remain original. Some dynamic diagnostics remain English |
| Loading / Empty / Error / Unavailable / Stale / Offline | PASS with limits | Shared page states and persistent transport status; stale cached data labelled globally. No per-field provenance timestamp |
| Before/after image matrix | PASS with limits | Nine routes × normal/offline/stale × before/after = 54 PNGs. Baseline stale is unsupported and therefore identical to normal; baseline offline can show browser error, documented honestly |
| Contrast AA / complete keyboard audit | NOT FULLY VERIFIED | Visible focus, logical properties, improved tokens and native controls. Theme/direction/keyboard smoke tests pass; no comprehensive contrast or assistive-technology audit |
| Full mock backend equivalence | PARTIAL | Contract-bound simulated payloads, pagination, locks, idempotency and Ack. In-memory, resets on reload; no 24h persistence, real authentication, production scheduler or durable audit |
| Native Tauri session token / minimal renderer capability | PARTIAL | Memory-only token loaded through limited command; shell/updater permissions removed. No actual Python handshake |
| Native sidecar lifecycle / OS keyring / installer | NOT VERIFIED | Python executable/protocol missing; Cargo unavailable. Must be completed with backend/release engineering |
| CI quality workflow | CONFIGURED | GitHub workflow added; local lint, typecheck, unit, contract, browser and production-build checks run. Hosted CI result depends on push/run |

## Commands and delivery

Use pinned pnpm 10.28.2 (or `npx --yes pnpm@10.28.2`). `lint`, `typecheck`, `test`, `contract:check`, `test:e2e`, and `build` are the checks. Native Tauri build is not counted as passed. Production build currently reports a nonblocking bundle-size warning.

The frozen backend handoff is `CONTRACT.md` with schemas and reusable `fixtures/`. Eight backend integration questions are listed there. Their answers are prerequisites for claiming native production readiness.
