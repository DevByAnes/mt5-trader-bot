# Baseline audit — 2026-11-02

Scope: the current workspace, not the unrelated Lastroject IDE tab. All application, schema, test, build and Tauri sources were inspected; generated dependencies and distribution bundles were excluded. Existing React, Router, Query, Zustand UI preferences, MSW, Tauri and Lightweight Charts are retained.

## Safety gaps
- `src/shared/api/client.ts`: manual DTOs diverge from OpenAPI; unrestricted records hide missing backend fields. No transport timeout or response version check.
- `src/mocks/handlers.ts`: synthetic data is not identified in the UI; every mutation immediately returns APPLIED; no deduplication, immutable audit, schema validation, lock enforcement or failure scenarios.
- `src/features/settings/SettingsPage.tsx`: editable draft can change after review; background refetch resets edits; mutation errors strand the workflow; disabled MT5 fields can disappear from submitted values. No rollback. Execution mode is locked wholesale instead of gating LIVE.
- `src/features/settings/machine.ts`: accepts every event from every state; equality is incorrectly TIGHTER; SUBMITTING is skipped.
- `src/shared/api/realtime.ts`, `src/App.tsx`: events are discarded, snapshot requests have no consumer, no stale watchdog, malformed JSON can throw. No HMAC/trading calculations or embedded HMAC keys found.

## Incomplete behavior
- `schema/openapi.yaml`: settings, daily risk and records are largely untyped; missing documented errors and Ack lookup. Profiles and rollback are advertised without mock/client implementation.
- `src/features/generic/GenericPage.tsx`: five routes are generic object dumps; no filtering, pagination or rollback action.
- `src/features/chart/ChartSignals.tsx`: no entry/SL/TP overlays. Overview lacks risk distances, compact positions, telemetry history, chart, rejection counts and decision links.
- `src-tauri/src/lib.rs`, `sidecar-policy.json`: session token is generated but never passed to a real bridge; sidecar lifecycle/keyring are statements, not implementations. Backend executable and release signing material are absent.

## Technical debt and access
- `src/shared/api/client.ts`, `SettingsPage.tsx`: duplicated schema/validation metadata. Query remains the server cache; connectivity is redundantly stored in Zustand.
- `src/shared/i18n.ts`, `src/App.tsx`: only English; hard-coded LTR; remaining page copy is untranslated.
- `src/shared/format.ts`: Persian default mixed with explicit English, invalid timestamps/NaN not handled.
- `src/styles.css`: physical margins/borders, weak light-theme handling and muted contrast. `tests/e2e/dashboard.spec.ts` covers two superficial paths only; no contract CI.

## Visual audit
Baseline screenshots: `docs/screenshots/before/`. All nine routes were launched at 1440×900. Baseline lacks a stale simulator: the `stale` captures intentionally show the same baseline rather than fabricate a state. Offline captures include the browser offline error because the baseline cannot reconnect/render a fresh offline route.
- Overview: equal-weight four KPIs, redundant green health badges, filler risk text, no operational hierarchy.
- Configuration: useful parameter grouping and visible locks retained; review has no stable draft boundary or recovery controls.
- Positions: large cards waste space compared with compact rows.
- Market: oversized standalone chart without order-level annotations.
- Risk, journal, validation, health, audit: generic tables expose implementation field names and offer little task-specific context.
- All routes: centered max-width, no execution mode/three-node heartbeat strip in the persistent header, small policy text, no locale/digit preferences.

## Priorities and change plan
**Must:** freeze typed contracts/events/settings and reusable fixtures; generated API drift check; honest simulated transport and Ack lifecycle; immutable reviewed draft; guarded machine, locks, second confirmation, rollback through the same review; global emergency controls; offline/stale visibility; meaningful tests. Files: `schema/*`, `src/shared/api/*`, `src/mocks/*`, `src/features/settings/*`, `tests/*`, `scripts/*`, `.github/workflows/*`.

**Should:** dense full-width operational Overview, compact positions, chart overlays, task-specific record views, health ages, English/Persian navigation and preferences, consistent digits/themes/logical layout, screenshot matrix and acceptance report. Files: `src/App.tsx`, `src/styles.css`, `src/features/*`, `src/shared/{i18n,format,store,ui}.*`, `docs/*`.

**Later:** actual Python executable, MT5 integration, native sidecar authentication/keyring provisioning, signed installer/updater release validation, very-large-log virtualization, profile import/export. Do not claim these are complete without backend artifacts. Remove unimplemented API promises and unnecessary renderer capabilities now; document the integration boundary.

Major-change rationale: replace free-form schema objects with named response schemas because backend implementation cannot infer payloads safely; replace unconditional settings transitions with guarded transitions because reviewed values must equal submitted values; replace generic record dumps with semantic tables while retaining shared table rendering.
