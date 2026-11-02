# Aurum backend — B1 fixture server

Only the project skeleton, frozen-contract HTTP server, scenario simulator, local security and realtime test transport are implemented. All data and acknowledgements are **simulated**. HTTP responses include `X-Aurum-Mode: fixture`; the contract payload shape is unchanged. There is no file bridge, EA/MT5 connection, persistent database, analysis engine or real trade action.

Run commands **inside `backend/`**, from this repository checkout. Runtime reads the existing root `schema/`, `fixtures/` and `docs/CONTRACT.md` directly, checks them at startup, and does not bundle silent copies. Moving only an installed wheel outside the checkout is not a supported deployment for B1.

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) (verified 0.13.6), then:

```powershell
cd backend
uv sync --frozen
$env:AURUM_SESSION_TOKEN = (& .venv/Scripts/python.exe -c 'import secrets; print(secrets.token_urlsafe(48))')
uv run aurum-backend
```

It binds exclusively to `127.0.0.1:8765`, single worker. A token of at least 32 ASCII non-whitespace characters is required before startup. Keep the token in memory; never provide it as a CLI argument or commit it. An alternative for a native parent is `AURUM_TOKEN_STDIN=1`: pass exactly one token line on stdin. No readiness/sidecar protocol is invented here.

Call `GET http://127.0.0.1:8765/api/v1/status` with `Authorization: Bearer <session token>`. Missing/incorrect bearer gives contract-shaped 401. Exact CORS origins default to `tauri://localhost`, `http://tauri.localhost`, `https://tauri.localhost`, `http://localhost:1420`, `http://127.0.0.1:1420`. `AURUM_ALLOWED_ORIGINS` may supply a comma-separated explicit allowlist. Requests without Origin are allowed for authenticated local CLI/native clients; foreign Origin/Host/peer is denied. Cookies and URL tokens are not accepted.

`AURUM_ENV=production` removes the scenario route entirely but **does not turn simulated data into a live backend**. `AURUM_SCENARIO` selects one of: normal, ack-applied, ea-offline, python-offline, bridge-offline, stale, seq-gap, ack-rejected, ack-timeout, version-conflict, daily-loss, daily-profit, daily-count, wide-spread, no-positions, multi-positions. In development, authenticated `POST /__dev/scenario` with `{"scenario":"stale"}` switches/reset the simulation. This separate harness is not added to the frozen production OpenAPI. Scenario reset clears memory and closes connected streams for resnapshot.

Requests default to 240/minute per session (separate unauthenticated limiter); 64KiB maximum body, 32 streams, 32 queued events/client, 1s write timeout and 10,000 accepted operations maximum. Full queues/slow writes close with 1013; neither blocks the simulation pump. Operations and idempotency responses remain in memory until reset/exit; capacity is rejected rather than evicting unresolved keys. There is no restart durability or multi-worker support.

Idempotency replay returns the **exact original accepted envelope**, including PENDING and original server timestamp. Poll `/requests/{request_id}` or `/requests/{original-idempotency-key}` for the terminal result. Body canonicalization ignores object key order. Same key with a different endpoint/body returns 409. One pending settings request reserves the version; TIMEOUT retains that reservation because its outcome is unknown. REJECTED does not change settings; APPLIED changes only simulated state and includes a simulated EA timestamp. COLD day boundaries are accelerated to the fixture Ack delay (700ms); there is no real scheduler.

WebSocket `/ws` requires the same bearer upgrade header and explicit allowlisted Origin if supplied. Header-capable local test clients can use it now. **The current browser/Tauri frontend cannot yet supply that header**: native same-origin provisioning remains unapproved CCP-02. No token-in-URL workaround is implemented. On every connection, existing telemetry event types replay; the full authoritative snapshot (settings/chart/history/audit included) is fetched through REST, as the frozen event protocol prescribes. Sequence starts at 1 per socket; seq-gap scenario intentionally skips one after replay. The server accepts no custom client-frame protocol.

Tests and lint:

```powershell
uv run ruff check
uv run mypy
uv run pytest -q
uv run python -m tools.gen_models --check
uv run aurum-lint
uv run python -m tools.guard_demo
uv run python -m tools.smoke
```

Regenerate models with `uv run python -m tools.gen_models`. No manual DTO modifications: the exact files and source hashes are checked. Generated validators enforce original JSON Schema for optional-vs-nullable, decimal enum/step precision and finite JSON values, supplementing generator limitations. Named models and response envelopes are validated against root fixtures. Dynamic JSON dictionaries are confined to schema/fixture routing and checked at the boundary.

Schemathesis runs real loopback HTTP across all 17 operations, positive and negative generation, 25 examples per operation plus coverage cases. The six list/position-command operations explicitly allow semantic `422` in its positive-data-acceptance check (random cursors and missing position identifiers otherwise count as schema-valid strings/objects). No response-schema/server-error/negative-input check is disabled. The unconfigured default reports this known frozen-schema gap; see CCP-06. Filters and sorting not declared in OpenAPI are rejected, not silently implemented.

Because 429 and 500 are absent from frozen response definitions, rate limiting and unexpected internal errors use documented **503 UNAVAILABLE**, with a generic message and no traceback. Limiter adds `Retry-After: 60`. Undeclared HTTP methods use standard 405 + envelope + Allow; they are not declared API operations. These constraints and future corrections are in [contract proposals](../docs/CONTRACT_CHANGE_PROPOSALS.md).

Future packages `bridge`, `data`, `analysis`, `validation`, `storage` contain a one-line README and marker Protocol only. There is no implementation behind those interfaces. Phase B2 must first agree the bridge schema, authentication provisioning, atomic snapshot/sequence semantics and actual Ack/effective-time behavior.
