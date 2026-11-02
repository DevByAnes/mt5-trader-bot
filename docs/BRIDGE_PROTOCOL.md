# Aurum FILE bridge v1

This separately versioned contract adds the user's requested Common-folder bridge. Public HTTP v1 schemas stay unchanged. It is implemented and tested in Python; an external signed peer used in tests is explicitly a test double, not an installed EA. Native MQL5 compatibility, provisioning and demo acceptance are separate checklist gates.

## Layout and ownership

Use a dedicated directory below MT5 `Terminal/Common/Files/Aurum/<account>-<symbol>-<magic>`. Configure the exact directory; Python does not search or modify unrelated terminal files. Each account/symbol/magic has a distinct key and database. All paths are local, bounded regular files. Symlinks/junctions and traversal names are rejected; an attacker with control of the OS account can still replace directories or read process memory, so this is not an OS isolation boundary.

| Name | Writer | Purpose |
|---|---|---|
| `state.json` | EA | Complete authenticated telemetry snapshot; replace every heartbeat |
| `command_<request_id>.json` | Python | One restricted management request; no execution-entry command |
| `config_<request_id>.json` | Python | Whole validated settings proposal, explicit version and effective boundary |
| `ack_<message_id>.json` | EA | Immutable APPLIED/REJECTED result for a request |
| `python_heartbeat.json` | Python | Authenticated backend presence; never required for ongoing position management |

Writers create a temporary sibling, flush and close it, then replace the target. Python also uses fsync. EA must check every FileOpen/FileWrite/FileFlush/FileMove result and keep the last valid configuration if replacement fails. This is not a transaction across SQLite and NTFS: Python commits an outbox first, then publishes the same signed file. Crash redelivery retains its request ID. EA must durably deduplicate IDs before any effect; an ambiguous in-flight operation after restart requires reconciliation, never blind execution.

## Envelope and authentication

`schema/bridge.schema.json` defines `Wire` and `Payload`. No secrets appear in either. `payload_b64` carries the exact UTF-8 bytes of the inner JSON (no BOM). SHA-256 covers decoded payload bytes. HMAC-SHA256 covers:

```text
ASCII("AURUM-FILE-V1\n") + ASCII(key_id) + ASCII("\n") + payload_bytes
```

Hex digests are lowercase. Compare digests in constant time. The receiver verifies size, outer schema, key ID, hash/HMAC, strict JSON (duplicate keys/nonfinite numbers rejected), inner schema, direction, EA instance and lifetime. Authenticating exact bytes avoids inconsistent float formatting/key sorting between languages. Python serializes sorted compact ASCII JSON, but EA may use any valid unambiguous UTF-8 JSON if it signs its exact bytes.

Secret ownership: Python receives a ≥32-byte key through `AURUM_BRIDGE_KEY_HEX`, or an approved OS keyring adapter. Do not place the key in settings, .set exports, SQLite, JS or logs. Secure provisioning of the same key to the native EA is not defined by storing a plaintext secret file; this needs a native/OS credential path and a real MT5 test. An absent key prevents FILE startup. A public test vector key must never be used for operation.

## Payload semantics

Every payload has kind, sender, UUID message_id, UUID ea_instance_id, seq, issued_at_ms, expires_at_ms and body. Times are UTC Unix milliseconds, integers ≤2^53−1. Maximum lifetime is 24h, future tolerance 5s. STATE should expire after 30s; ACK should remain valid for 24h to permit backend restart reconciliation. Python heartbeat lives 15s; commands normally expire after 10s. CONFIG waits until next M15 or the EA-reported next trading day; this scheduling is not a Python trading calculation.

EA emits a new instance UUID per startup and monotonically increasing sequence **per kind** (STATE and ACK); Python persists those checkpoints. Duplicates with identical message/hash are ignored. Reused IDs with changed bytes, rollback sequences, old state timestamps, incorrect account/symbol/magic, or changed settings without version increment are rejected. A STATE sequence gap is repaired by that complete snapshot; missing ACKs remain unresolved and are recovered from durable ack files. Do not infer operation success from a healthy heartbeat or a settings GET alone.

STATE resources reuse the HTTP v1 models. A resource not yet available is null in the bridge snapshot and yields HTTP 503 UNAVAILABLE, never invented zero/empty data. Python reports its own measured health; stale/absent EA telemetry remains labelled. Validation/analysis records must come from actual runs, not Fixture examples in FILE mode.

CONFIG is all-or-nothing: base_version, config_version=base+1, complete values, request_id, apply_at (NEXT_M15/NEXT_DAY), confirmed_loosen. MT5-only fields cannot be changed. The EA independently revalidates schema, locks, version and timing. It may persist a pending proposal, but emits APPLIED only after actual effect. An existing position keeps its original policy unless explicitly permitted; SL never retreats.

HTTP v1 cannot prove the UI's second confirmation. Therefore real FILE mode rejects loosening through v1; a separately typed confirmation flow must be completed before loosening is enabled. The user resolved the RR policy: net RR ≥2 with a cost-adjusted target. LIVE remains blocked until native implementation/acceptance pass. Fixture mode retains its existing simulated behavior for development. CONFIG currently carries the six v1 settings; the draft 94-input v2 catalog is not yet connected to this wire kind or to a native EA.

ACK correlates exact request_id and target instance. APPLIED config version must equal the proposed version. Only signed EA ACK updates an operation to APPLIED/REJECTED. A conflicting terminal result is rejected. Timeout is UNKNOWN and retains the config reservation; a late matching ACK may resolve it. Successful processing commits the inbox/result/audit transaction **before** removing the ack file. Retries and restart cannot create a second acceptance for the same idempotency key.

## Durability and audit

SQLite 3.51.3+ is required (local runtime 3.53.1); WAL, synchronous=FULL, immediate write transactions, uniqueness constraints and migration versioning are enforced. Operation acceptance, version reservation and audit append share a transaction. Audit records are append-only through SQL triggers and hash-chained; startup verifies the chain. A local owner could drop tables/triggers or replace the whole DB: external notarization/backup is required for stronger tamper evidence.

The database binds its account/symbol/magic/key ID at first use and rejects reuse with a different identity. Request audits name a fresh local session ID; EA effects name their signed EA instance. Disk/database failures keep requests unresolved, mark backend health stale, reject new mutations and retry the same durable outbox after recovery. Invalid ack files are retained as evidence; batches rotate so they cannot permanently starve later valid files. Long-term journal retention, signed audit export and disk monitoring are not implemented in this milestone.

There is no automatic retry with a new idempotency key. No unresolved operation is silently discarded on restart. The same accepted response is replayed; GET /requests/{id-or-key} resolves current status. Namespace/session IDs and key rotation must not be changed while outcomes are unknown without reconciliation.

## Local activation

Set `AURUM_BACKEND_MODE=file`, `AURUM_BRIDGE_DIRECTORY`, `AURUM_DATABASE_PATH`, `AURUM_BRIDGE_KEY_HEX`, `AURUM_EA_ACCOUNT`; optionally exact `AURUM_EA_SYMBOL`, `AURUM_EA_MAGIC`, `AURUM_BRIDGE_KEY_ID`. Session token remains separately required. `uv run aurum-backend` serves the current HTTP API with `X-Aurum-Mode: file`. No EA snapshot → unknown/offline. Scenario endpoints are absent in FILE mode even during development. Do not enable LIVE as a way to test transport.

Paths must be absolute and local, not UNC. For OS keyring lookup, set `AURUM_KEYRING_ACCOUNT=bridge/<account-name>` and store the ≥32-byte hex key under service `AurumControl` using the OS credential manager. Approved native adapters are Windows/macOS/SecretService; unavailable or plaintext backends fail startup. The session bearer is a separate secret. The integration harness supplies a test-only in-memory browser handoff; the desktop production handoff is not complete.
