# B1 contract change proposals — pending user approval

No frozen schema, fixture, frontend or CONTRACT.md is changed by B1. These are proposed diffs, not approved contract amendments.

## CCP-01 — rate limit and internal error status

```diff
 paths.*.*.responses:
+  '429': ErrorEnvelope (UNAVAILABLE until a dedicated code is approved)
+  '500': ErrorEnvelope (UNAVAILABLE, generic message only)
 components.schemas.Error.properties.code.enum:
+  RATE_LIMITED
+  INTERNAL_ERROR
```

Reason: all operations currently list only 400/401/403/404/409/422/503. B1 therefore uses documented **503 UNAVAILABLE + Retry-After** for rate limiting and internal faults, avoiding an undocumented status/code. Frontend impact if approved: handle 429 backoff distinctly; still never retry mutations automatically.

## CCP-02 — WebSocket native/browser authentication

```diff
 docs/CONTRACT.md, WebSocket authentication:
- Native handshake is an open question.
+ Native transport may supply Authorization: Bearer <session token> on upgrade.
+ Browser WebView transport requires a separately approved, same-origin
+ HttpOnly/SameSite cookie provisioning handshake owned by Rust/Python.
+ Never pass session tokens in WebSocket URLs or event payloads.
```

Reason: the contract names same-origin provisioning without a concrete handshake; browser WebSocket cannot add Authorization headers. B1 authenticates header-capable **local test clients only** with the existing bearer credential and exact Origin checks. It does not implement cookies, token subprotocols or a new production auth endpoint. This is a test-transport assumption, not a completed dashboard integration. Approval and a frontend/native change are required before real WebView integration.

## CCP-03 — snapshot scope

```diff
 schema/events.json, x-protocol.snapshot:
   GET every active query after open or seq gap; HTTP remains authoritative.
+  Server may replay the six existing telemetry event types on each connection.
+  Settings, chart, history and audit snapshots remain authenticated REST GETs.
```

Reason: there is no `snapshot` event/payload type in the frozen union. B1 never invents one. It replays existing telemetry frames and keeps all contract REST resources available for the complete snapshot. Frontend already invalidates active queries on open/gap. A single atomic snapshot/version boundary, if required by B2, needs a new approved schema.

## CCP-04 — development control plane (requested by user, outside frozen API)

```diff
 development-only service surface (not added to frozen /api/v1 contract):
+ POST /__dev/scenario  {"scenario": "normal" | ...}
+ 200 standard envelope with current scenario name
+ 401/422/503 standard ErrorEnvelope
+ Absent entirely in production (404); bearer auth and Origin checks required.
```

This is the explicitly requested B1 development harness; it is not a proposed production endpoint. Frontend integration is deferred until approved; environment variable AURUM_SCENARIO also selects it. Switching resets simulated in-memory state and disconnects streams so clients obtain a fresh snapshot.

## CCP-05 — unspecified filters/order and Ack fixtures

```diff
 list operations:
+ Document newest-first, stable fixture order on equal timestamps.
+ Explicitly list any future filtering/sort query parameters before accepting them.
 fixture set:
+ AckPending.json / AckRejected.json / AckTimeout.json (contract-shaped examples)
```

B1 uses only declared `cursor` and `limit`; unknown query parameters are validation errors. It derives alternate simulated Ack values from the existing Ack schema/example in backend-local scenario fixtures without changing root fixtures. No trading filters or calculations are invented.

## CCP-06 — semantic validation and HTTP method rejection

```diff
 CommandRequest / command-specific request bodies:
+ Require nonempty position_id for risk-free-position and close-position only.
 cursor parameter documentation:
+ Opaque cursor must have been issued for this resource; invalid/expired cursor returns 422.
 transport documentation:
+ Unsupported HTTP methods return 405 + ErrorEnvelope + Allow header.
```

The current strings have no cursor format and CommandRequest has no conditional required field. Schemathesis's default positive-data check consequently calls random cursor strings and omitted position IDs "valid" even though they cannot identify a resource. B1 retains explicit validation and documents any test override for semantic 422 rather than accepting arbitrary identifiers. A 405 is a response to an **undeclared method**, not a new response for any declared operation. These clarifications remain proposals; the frozen files are unchanged.
