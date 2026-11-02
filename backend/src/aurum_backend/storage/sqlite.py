"""Local WAL repository for durable acceptance, outbox, reconciliation and audit."""

import hashlib
import json
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from aurum_backend.api.errors import ApiFault
from aurum_backend.bridge.codec import json_bytes
from aurum_backend.core.time import utc_now

MIGRATION = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS operations(
 scope TEXT NOT NULL, key TEXT NOT NULL, request_id TEXT NOT NULL UNIQUE,
 endpoint TEXT NOT NULL, body TEXT NOT NULL, accepted TEXT NOT NULL,
 result TEXT NOT NULL, target_instance TEXT NOT NULL, deadline_ms INTEGER NOT NULL,
 config_version INTEGER, apply_at TEXT, wire BLOB NOT NULL, filename TEXT NOT NULL UNIQUE,
 dispatched INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(scope,key)
);
CREATE UNIQUE INDEX IF NOT EXISTS pending_config ON operations(scope)
 WHERE config_version IS NOT NULL AND json_extract(result,'$.status') IN ('PENDING','TIMEOUT');
CREATE INDEX IF NOT EXISTS pending_deadline ON operations(scope,deadline_ms)
 WHERE json_extract(result,'$.status')='PENDING';
CREATE TABLE IF NOT EXISTS inbox(
 message_id TEXT PRIMARY KEY, instance TEXT NOT NULL, kind TEXT NOT NULL,
 seq INTEGER NOT NULL, digest TEXT NOT NULL, UNIQUE(instance,kind,seq)
);
CREATE TABLE IF NOT EXISTS audit(
 seq INTEGER PRIMARY KEY, time_utc TEXT NOT NULL, actor TEXT NOT NULL,
 action TEXT NOT NULL, resource TEXT NOT NULL, details TEXT NOT NULL,
 previous_hash TEXT NOT NULL, hash TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit
 BEGIN SELECT RAISE(ABORT,'audit is append-only'); END;
CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit
 BEGIN SELECT RAISE(ABORT,'audit is append-only'); END;
PRAGMA user_version=2;
"""


class Repository:
    def __init__(
        self, path: Path, scope: str = "local-operator", *, actor: str | None = None
    ) -> None:
        if sqlite3.sqlite_version_info < (3, 51, 3):
            raise RuntimeError("SQLite 3.51.3+ required for fixed WAL reset handling")
        path = path.absolute()
        if any(p.is_symlink() or p.is_junction() for p in [path, *path.parents]):
            raise ValueError("Linked database path is not supported")
        path.parent.mkdir(parents=True, exist_ok=True)
        self.scope = scope
        self.actor = actor or scope
        self.lock = threading.RLock()
        self.connection = sqlite3.connect(
            path, timeout=3, isolation_level=None, check_same_thread=False
        )
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        version = self.connection.execute("PRAGMA user_version").fetchone()[0]
        if version not in {0, 1, 2}:
            self.connection.close()
            raise RuntimeError("Unsupported database migration version")
        try:
            upgrade = "ALTER TABLE operations ADD COLUMN apply_at TEXT;\n" if version == 1 else ""
            self.connection.executescript("BEGIN IMMEDIATE;\n" + upgrade + MIGRATION + "\nCOMMIT;")
            self.verify_audit()
        except BaseException:
            if self.connection.in_transaction:
                self.connection.rollback()
            self.connection.close()
            raise

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self.lock:
            self.connection.execute("BEGIN IMMEDIATE")
            try:
                yield self.connection
                self.connection.execute("COMMIT")
            except BaseException:
                self.connection.execute("ROLLBACK")
                raise

    def close(self) -> None:
        with self.lock:
            self.connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            self.connection.close()

    def get(self, key: str) -> Any:
        with self.lock:
            row = self.connection.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
            return json.loads(row[0]) if row else None

    @staticmethod
    def put_tx(connection: sqlite3.Connection, key: str, value: Any) -> None:
        connection.execute(
            "INSERT INTO meta(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, json_bytes(value).decode()),
        )

    def audit_tx(
        self,
        connection: sqlite3.Connection,
        action: str,
        resource: str,
        details: Any,
        *,
        actor: str | None = None,
    ) -> None:
        row = connection.execute("SELECT seq,hash FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
        seq, previous = (row[0] + 1, row[1]) if row else (1, "0" * 64)
        payload = {
            "seq": seq,
            "time_utc": utc_now(),
            "actor": actor or self.actor,
            "action": action,
            "resource": resource,
            "details": details,
            "previous_hash": previous,
        }
        digest = hashlib.sha256(json_bytes(payload)).hexdigest()
        connection.execute(
            "INSERT INTO audit VALUES(?,?,?,?,?,?,?,?)",
            (
                seq,
                payload["time_utc"],
                payload["actor"],
                action,
                resource,
                json_bytes(details).decode(),
                previous,
                digest,
            ),
        )

    def verify_audit(self) -> None:
        previous = "0" * 64
        with self.lock:
            rows = self.connection.execute("SELECT * FROM audit ORDER BY seq").fetchall()
        for index, row in enumerate(rows, 1):
            payload = {
                "seq": row["seq"],
                "time_utc": row["time_utc"],
                "actor": row["actor"],
                "action": row["action"],
                "resource": row["resource"],
                "details": json.loads(row["details"]),
                "previous_hash": row["previous_hash"],
            }
            if (
                row["seq"] != index
                or row["previous_hash"] != previous
                or hashlib.sha256(json_bytes(payload)).hexdigest() != row["hash"]
            ):
                raise RuntimeError("Audit chain verification failed")
            previous = row["hash"]

    def replay(self, endpoint: str, key: str, body: Any) -> dict[str, Any] | None:
        with self.lock:
            row = self.connection.execute(
                "SELECT endpoint,body,accepted FROM operations WHERE scope=? AND key=?",
                (self.scope, key),
            ).fetchone()
        if not row:
            return None
        if row["endpoint"] != endpoint or row["body"] != json_bytes(body).decode():
            raise ApiFault(
                "IDEMPOTENCY_CONFLICT", "Key already identifies a different request", 409
            )
        return json.loads(row["accepted"])  # type: ignore[no-any-return]

    def accept(
        self,
        *,
        endpoint: str,
        key: str,
        body: Any,
        request_id: str,
        accepted: dict[str, Any],
        target: str,
        deadline_ms: int,
        config_version: int | None,
        wire: bytes,
        filename: str,
        base_version: int | None = None,
        apply_at: str | None = None,
    ) -> dict[str, Any]:
        with self.transaction() as connection:
            previous = self.replay(endpoint, key, body)
            if previous:
                return previous
            if config_version is not None:
                current = self.get("settings")
                if not current or current["version"] != base_version:
                    raise ApiFault("VERSION_CONFLICT", "Settings version changed", 409)
            try:
                connection.execute(
                    "INSERT INTO operations(scope,key,request_id,endpoint,body,accepted,"
                    "result,target_instance,deadline_ms,config_version,wire,filename,apply_at) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        self.scope,
                        key,
                        request_id,
                        endpoint,
                        json_bytes(body).decode(),
                        json_bytes(accepted).decode(),
                        json_bytes(accepted["data"]).decode(),
                        target,
                        deadline_ms,
                        config_version,
                        wire,
                        filename,
                        apply_at,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ApiFault(
                    "VERSION_CONFLICT", "Another settings request is unresolved", 409
                ) from exc
            self.audit_tx(
                connection,
                "REQUEST_ACCEPTED",
                request_id,
                {"endpoint": endpoint, "body": body, "target": target},
            )
        return accepted

    def pending_writes(self) -> list[sqlite3.Row]:
        with self.lock:
            return self.connection.execute(
                "SELECT * FROM operations WHERE dispatched=0 AND scope=? "
                "AND json_extract(result,'$.status')='PENDING'",
                (self.scope,),
            ).fetchall()

    def unresolved_config(self) -> sqlite3.Row | None:
        with self.lock:
            return cast(
                sqlite3.Row | None,
                self.connection.execute(
                    "SELECT * FROM operations WHERE scope=? AND config_version IS NOT NULL "
                    "AND json_extract(result,'$.status') IN ('PENDING','TIMEOUT') LIMIT 1",
                    (self.scope,),
                ).fetchone(),
            )

    def event_for(self, request_id: str) -> str:
        with self.lock:
            row = self.connection.execute(
                "SELECT config_version FROM operations WHERE scope=? AND request_id=?",
                (self.scope, request_id),
            ).fetchone()
        return "config_ack" if row and row[0] is not None else "command_ack"

    def dispatched(self, request_id: str) -> None:
        with self.transaction() as connection:
            connection.execute(
                "UPDATE operations SET dispatched=1 WHERE request_id=? AND scope=?",
                (request_id, self.scope),
            )

    def result(self, identity: str) -> dict[str, Any]:
        with self.lock:
            row = self.connection.execute(
                "SELECT result FROM operations WHERE scope=? AND (request_id=? OR key=?)",
                (self.scope, identity, identity),
            ).fetchone()
        if not row:
            raise ApiFault("NOT_FOUND", "Request not found", 404)
        return json.loads(row[0])  # type: ignore[no-any-return]

    def mark_timeouts(self, now_ms: int) -> None:
        with self.transaction() as connection:
            rows = connection.execute(
                "SELECT request_id,result FROM operations WHERE scope=? "
                "AND deadline_ms<=? AND json_extract(result,'$.status')='PENDING'",
                (self.scope, now_ms),
            ).fetchall()
            for row in rows:
                result = json.loads(row["result"])
                result.update(
                    status="TIMEOUT", reason="Outcome unknown; awaiting EA reconciliation"
                )
                connection.execute(
                    "UPDATE operations SET result=? WHERE request_id=?",
                    (json_bytes(result).decode(), row["request_id"]),
                )
                self.audit_tx(connection, "REQUEST_TIMEOUT", row["request_id"], result)

    def receive(self, payload: dict[str, Any], digest: str) -> bool:
        with self.transaction() as connection:
            known = connection.execute(
                "SELECT digest FROM inbox WHERE message_id=?", (payload["message_id"],)
            ).fetchone()
            if known:
                if known[0] != digest:
                    raise ValueError("Conflicting duplicate message")
                return False
            latest = connection.execute(
                "SELECT MAX(seq) FROM inbox WHERE instance=? AND kind=?",
                (payload["ea_instance_id"], payload["kind"]),
            ).fetchone()[0]
            if latest is not None and payload["seq"] <= latest:
                raise ValueError("Replay or sequence rollback")
            if payload["kind"] == "STATE":
                snapshot = self.get("ea_snapshot")
                if snapshot and payload["issued_at_ms"] < snapshot["issued_at_ms"]:
                    raise ValueError("State timestamp rollback")
                values = payload["body"]["resources"]["SettingsData"]
                current = self.get("settings")
                if (
                    values
                    and current
                    and values["version"] == current["version"]
                    and values["values"] != current["values"]
                ):
                    raise ValueError("Settings changed without version increment")
            connection.execute(
                "INSERT INTO inbox VALUES(?,?,?,?,?)",
                (
                    payload["message_id"],
                    payload["ea_instance_id"],
                    payload["kind"],
                    payload["seq"],
                    digest,
                ),
            )
            if payload["kind"] == "STATE":
                resources = payload["body"]["resources"]
                self.put_tx(connection, "ea_snapshot", payload)
                settings = resources["SettingsData"]
                known_settings = self.get("settings")
                if settings and (
                    not known_settings or settings["version"] >= known_settings["version"]
                ):
                    self.put_tx(connection, "settings", settings)
            elif payload["kind"] == "ACK":
                self._ack_tx(connection, payload)
            return True

    def _ack_tx(self, connection: sqlite3.Connection, payload: dict[str, Any]) -> None:
        ack = payload["body"]
        row = connection.execute(
            "SELECT * FROM operations WHERE request_id=? AND scope=?",
            (ack["request_id"], self.scope),
        ).fetchone()
        if not row or row["target_instance"] != payload["ea_instance_id"]:
            raise ValueError("Ack does not match accepted request and EA instance")
        previous = json.loads(row["result"])
        acknowledged = datetime.fromisoformat(ack["ea_ack_utc"]).timestamp() * 1000
        accepted_at = (
            datetime.fromisoformat(json.loads(row["accepted"])["server_time_utc"]).timestamp()
            * 1000
        )
        if acknowledged < accepted_at - 5000 or acknowledged > payload["issued_at_ms"] + 5000:
            raise ValueError("Ack timestamp outside operation lifetime")
        if previous["status"] in {"APPLIED", "REJECTED"}:
            if previous != ack:
                raise ValueError("Conflicting terminal acknowledgement")
            return
        if row["config_version"] is not None and ack["status"] == "APPLIED":
            if ack["version"] != row["config_version"]:
                raise ValueError("Acknowledged settings version does not match request")
            body = json.loads(row["body"])
            before = self.get("settings")
            self.put_tx(
                connection,
                "settings",
                {"version": ack["version"], "values": body["values"], "pending_next_day": False},
            )
            self.audit_tx(
                connection,
                "SETTINGS_APPLIED",
                ack["request_id"],
                {
                    "previous_values": before["values"] if before else None,
                    "values": body["values"],
                    "version": ack["version"],
                    "ack": ack,
                },
                actor="ea:" + payload["ea_instance_id"],
            )
        connection.execute(
            "UPDATE operations SET result=? WHERE request_id=?",
            (json_bytes(ack).decode(), ack["request_id"]),
        )
        self.audit_tx(
            connection,
            "EA_ACK",
            ack["request_id"],
            ack,
            actor="ea:" + payload["ea_instance_id"],
        )

    def audit_page(self) -> dict[str, Any]:
        with self.lock:
            rows = self.connection.execute(
                "SELECT * FROM audit WHERE action='SETTINGS_APPLIED' ORDER BY seq DESC"
            ).fetchall()
        items = []
        for row in rows:
            detail = json.loads(row["details"])
            if detail["previous_values"] is None:
                continue
            items.append(
                {
                    "id": str(row["seq"]),
                    "time_utc": row["time_utc"],
                    "actor": row["actor"],
                    "action": row["action"],
                    "version": detail["version"],
                    "result": "APPLIED",
                    "previous_values": detail["previous_values"],
                }
            )
        return {"items": items, "next_cursor": None}
