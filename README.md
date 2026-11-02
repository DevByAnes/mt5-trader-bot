# Aurum Control

React / TypeScript / Tauri 2 operations console for an XAUUSD EA through a local Python bridge. The dashboard displays server-reported values and requests limited management actions. It never sizes positions, computes trading risk/RR, signs HMAC payloads or talks to MT5 directly.

Use Node 24 and pnpm 10.28.2. Direct dependency versions are pinned; `pnpm-lock.yaml` is the CI lock. The npm lock is retained for the existing npm workflow.

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

The current Tauri shell exposes only a memory session-token command. Renderer shell/updater permissions and placeholder release updater/binary declarations have been removed. The token is not yet shared with Python. Python sidecar lifecycle, authenticated readiness, OS keyring provisioning, native WebSocket authentication and release signing require the backend executable/protocol and a Rust toolchain. They are documented integration gaps, not completed release features. Cargo is unavailable in the delivery environment; native builds have not been verified. CSP retains inline styles for chart/React style attributes while scripts, frames, objects and remote connections are restricted.
