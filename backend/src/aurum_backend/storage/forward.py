"""Durable observations of authenticated snapshots, without inferred trade outcomes."""

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from typing import Any

TABLE = """
CREATE TABLE IF NOT EXISTS forward_records(
 category TEXT NOT NULL, identity TEXT NOT NULL, observed_ms INTEGER NOT NULL,
 body TEXT NOT NULL, PRIMARY KEY(category,identity)
);
CREATE INDEX IF NOT EXISTS forward_time ON forward_records(category,observed_ms);
"""


def observe(connection: sqlite3.Connection, payload: dict[str, Any]) -> None:
    """Called in the same transaction as inbox acceptance; a replay cannot add rows."""
    resources = payload["body"]["resources"]
    now = payload["issued_at_ms"]
    state = resources.get("EaState")
    if state:
        sample = {
            "time_utc": datetime.fromtimestamp(now / 1000, UTC).isoformat(),
            "equity": state.get("equity"),
            "currency": state.get("account_currency"),
            "mode": state.get("mode"),
            "spread": state.get("spread"),
            "atr": state.get("atr"),
            "entry_reason": state.get("risk_reason"),
            "settings": resources.get("SettingsData"),
            "status": resources.get("Status"),
        }
        insert(connection, "samples", str(now // 60000), now, sample)
    for category, resource in [("decisions", "Signals"), ("deals", "Journal")]:
        for row in (resources.get(resource) or {}).get("items", []):
            raw = json.dumps(row, sort_keys=True, ensure_ascii=False, allow_nan=False)
            identity = hashlib.sha256(raw.encode()).hexdigest()
            insert(connection, category, identity, now, row)


def insert(
    connection: sqlite3.Connection, category: str, identity: str, now: int, body: dict[str, Any]
) -> None:
    connection.execute(
        "INSERT OR IGNORE INTO forward_records VALUES(?,?,?,?)",
        (category, identity, now, json.dumps(body, ensure_ascii=False, allow_nan=False)),
    )


def report(connection: sqlite3.Connection, *, export: bool = False) -> dict[str, Any]:
    samples = connection.execute(
        "SELECT observed_ms,body FROM forward_records WHERE category='samples' "
        "ORDER BY observed_ms"
    ).fetchall()
    counts = dict(
        connection.execute("SELECT category,COUNT(*) FROM forward_records GROUP BY category")
    )
    first = samples[0][0] if samples else None
    last = samples[-1][0] if samples else None
    peak: float | None = None
    drawdown = 0.0
    equity_samples = 0
    currencies: set[str] = set()
    for _, raw in samples:
        sample = json.loads(raw)
        if sample["currency"]:
            currencies.add(sample["currency"])
        equity = sample["equity"]
        if equity is not None:
            equity_samples += 1
            peak = equity if peak is None else max(peak, equity)
            if peak > 0:
                drawdown = max(drawdown, (peak - equity) / peak * 100)
    reasons = [
        {"code": code, "count": count}
        for code, count in connection.execute(
            "SELECT json_extract(body,'$.reason_code'),COUNT(*) FROM forward_records "
            "WHERE category='decisions' AND json_extract(body,'$.reason_code') IS NOT NULL "
            "GROUP BY json_extract(body,'$.reason_code') ORDER BY COUNT(*) DESC"
        )
    ]
    gaps = sum(b[0] - a[0] > 180000 for a, b in zip(samples, samples[1:], strict=False))
    result: dict[str, Any] = {
        "report_version": 1,
        "source": "authenticated_ea_snapshots",
        "started_utc": datetime.fromtimestamp(first / 1000, UTC).isoformat() if first else None,
        "last_sample_utc": datetime.fromtimestamp(last / 1000, UTC).isoformat() if last else None,
        "target_end_utc": (
            datetime.fromtimestamp(first / 1000 + 7 * 86400, UTC).isoformat() if first else None
        ),
        "observed_span_hours": (last - first) / 3600000 if first and last else 0,
        "samples": counts.get("samples", 0),
        "decisions": counts.get("decisions", 0),
        "deals": counts.get("deals", 0),
        "sample_gaps_over_3_minutes": gaps,
        "sampled_max_drawdown_percent": (
            drawdown if equity_samples and len(currencies) == 1 else None
        ),
        "currencies": sorted(currencies),
        "reason_counts": reasons,
        "first_sample": json.loads(samples[0][1]) if samples else None,
        "latest_sample": json.loads(samples[-1][1]) if samples else None,
        "limitations": [
            "One equity sample per UTC minute while Python receives EA snapshots",
            "Gaps describe missing observations, not exact uptime",
            "Decisions and deals are separate records; counts are not trade or win counts",
            "Samples include whole-account equity; deposits and other EAs can affect drawdown",
            "No inferred win rate, historical R or profitability validation",
        ],
    }
    if export:
        records = {}
        truncated = {}
        for category in ("samples", "decisions", "deals"):
            rows = connection.execute(
                "SELECT body FROM forward_records WHERE category=? ORDER BY observed_ms "
                "LIMIT 100000", (category,)
            ).fetchall()
            records[category] = [json.loads(row[0]) for row in rows]
            truncated[category] = counts.get(category, 0) > len(rows)
        result["records"] = records
        result["export_truncated"] = truncated
    return result
