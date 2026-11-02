# Aurum Control

React / TypeScript / Tauri 2 operations console for an XAUUSD EA through a local Python bridge. The dashboard displays server-reported values and requests limited management actions. It never sizes positions, computes trading risk/RR, signs HMAC payloads or talks to MT5 directly.

Use Node 24 and pnpm 10.28.2. Direct dependency versions are pinned; `pnpm-lock.yaml` is the CI lock. The npm lock is retained for the existing npm workflow.

The Python bridge now has a separate **FILE mode** with authenticated snapshots, durable SQLite outbox/idempotency, version reservations and hash-chained audit. Missing EA data stays unavailable. The MQL5 directory currently contains generated inputs, economic helpers and native test scripts; **the main EA and its native acceptance are unfinished**. This is a development milestone, not a trading release. See the [phased checklist](docs/IMPLEMENTATION_PLAN.md), [milestone test report](docs/REPORT_B2.fa.md), [architecture decisions](docs/DECISIONS.md), [research](docs/RESEARCH_SYSTEM.md) and [FILE protocol/activation](docs/BRIDGE_PROTOCOL.md).

```powershell
pnpm install --frozen-lockfile
pnpm dev
pnpm lint
pnpm typecheck
pnpm test
pnpm contract:check
pnpm test:e2e
pnpm build
```

If pnpm is absent, `npx --yes pnpm@10.28.2 <command>` runs the same commands. Install the test browser with `pnpm exec playwright install chromium` if needed.

Development starts MSW and the WebSocket simulator. The persistent bottom bar explicitly identifies simulated data and selects all 14 scenarios. Selecting a scenario reloads and resets its simulated session. `VITE_USE_MOCKS=false` uses the actual Python bridge; production bundles never start MSW. The UI supports Persian/English, independent digit selection and dark/light themes. Backend reason codes and protocol enums retain their stable original spelling.

Normative schemas live in `schema/`; API types derive from OpenAPI using `pnpm api:generate`. `pnpm contract:check` rejects generated drift, mismatched settings constraints and invalid response/event fixtures. Mock data lives in `fixtures/`, with runtime timestamps advanced for health simulation. COLD changes use an accelerated simulated EA day boundary; this is not a promise of immediate application by a real EA. Mock Ack delay is 700ms. Scenario TIMEOUT is terminal unknown and does not change values.

Read [the baseline audit](docs/AUDIT.md), [backend contract and open questions](docs/CONTRACT.md), and [acceptance results](docs/ACCEPTANCE.md). Before/after screenshots are in `docs/screenshots/`, with nine routes in three transport states. `pnpm screenshots` refreshes after images against a running dev server.

The current Tauri shell exposes only a memory session-token command. Renderer shell/updater permissions and placeholder release updater/binary declarations have been removed. The token is not yet shared with Python. Python sidecar lifecycle, authenticated readiness, native secret provisioning and release signing remain integration gaps. Cargo is unavailable in the delivery environment; native builds have not been verified. CSP retains inline styles for chart/React style attributes while scripts, frames, objects and remote connections are restricted.

Browser WebSocket authentication is implemented: obtain a one-use, Origin-bound 10-second ticket using the bearer-authenticated `/api/v2/session/ws-ticket`, then send it in the first frame. Session tokens never enter socket URLs. Native token handoff, Python lifecycle and EA credential provisioning remain separate work. Python can read its HMAC key from an approved OS keyring backend or an explicitly injected environment variable; no plaintext keyring fallback is accepted.

## Python and integration verification

```powershell
cd backend
python -m uv sync --frozen
python -m uv run aurum-lint
python -m uv run mypy
python -m uv run python -m tools.gen_models --check
python -m uv run python -m tools.shared_settings --check
python -m uv run pytest -q
cd ..
pnpm test:integration
```

`test:integration` starts real FastAPI and Vite with MSW disabled, emulates the unfinished native session handoff, verifies two consecutive Fixture settings acknowledgements, then restarts Python in FILE mode without an EA and checks offline telemetry/disabled commands. It cleans up its own processes and temporary database. Port 8765 must be free. This is not an installed-EA/Demo test. Screenshots are in `docs/screenshots/integration/`.

Python modules also provide closed-bar/Parquet validation, UTC news CSV with explicit coverage, DST session windows, observed metrics, confirmed swings/ATR, purged walk-forward indices, seeded Monte Carlo/cost stress and conservative counterfactual outcomes. These helpers are tested offline; full strategy validation, persistent journal ingestion and analytics API/UI integration remain in the checklist. Install the optional Windows read adapter with `python -m uv sync --extra mt5`; no Python trade-submission API is used.

`schema/settings.v2.schema.json` is the draft 94-input catalog. It generates Python, TypeScript and MQL5 input/validation tables. Safe profile and `.set` helpers are implemented; the current dashboard and FILE CONFIG still use the six-field v1 compatibility contract. The full v2 settings flow, server-verified second confirmation and all-input forms are unfinished. FILE mode rejects risk loosening through v1 and blocks LIVE.
