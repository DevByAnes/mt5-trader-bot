"""Typed, atomic Parquet cache; invalid data is never silently repaired."""

import os
import tempfile
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from aurum_backend.data.bars import Bar, DataQualityError, validate_closed

FIELDS = pa.schema(
    [
        ("time", pa.int64()),
        ("open", pa.float64()),
        ("high", pa.float64()),
        ("low", pa.float64()),
        ("close", pa.float64()),
        ("volume", pa.int64()),
    ]
)


def write_bars(path: Path, bars: list[Bar], *, timeframe_seconds: int, as_of: int) -> None:
    validate_closed(bars, timeframe_seconds=timeframe_seconds, as_of=as_of)
    if path.suffix != ".parquet" or any(
        p.is_symlink() or p.is_junction() for p in [path, *path.parents]
    ):
        raise DataQualityError("Invalid cache path")
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(
        [
            {
                "time": b.time,
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
            }
            for b in bars
        ],
        schema=FIELDS,
    )
    metadata = {
        b"timezone": b"UTC",
        b"timeframe_seconds": str(timeframe_seconds).encode(),
        b"as_of": str(as_of).encode(),
        b"schema_version": b"1.0.0",
    }
    table = table.replace_schema_metadata(metadata)
    fd, temporary = tempfile.mkstemp(prefix=".aurum-bars-", suffix=".parquet", dir=path.parent)
    os.close(fd)
    try:
        pq.write_table(table, temporary, compression="zstd")
        with Path(temporary).open("r+b") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def read_bars(path: Path, *, timeframe_seconds: int, as_of: int) -> list[Bar]:
    table = pq.read_table(path)
    if not table.schema.remove_metadata().equals(FIELDS):
        raise DataQualityError("Unexpected Parquet schema")
    metadata = table.schema.metadata or {}
    if (
        metadata.get(b"timezone") != b"UTC"
        or metadata.get(b"timeframe_seconds") != str(timeframe_seconds).encode()
    ):
        raise DataQualityError("Parquet timezone/timeframe mismatch")
    result = [Bar(**row) for row in table.to_pylist()]
    return validate_closed(result, timeframe_seconds=timeframe_seconds, as_of=as_of)
