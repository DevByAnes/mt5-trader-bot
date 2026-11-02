"""Bounded file sandbox and atomic replacement; never follows a user-supplied path."""

import os
import re
import stat
import tempfile
from pathlib import Path

from aurum_backend.bridge.codec import MAX_WIRE_BYTES, BridgeFault


class AtomicFiles:
    def __init__(self, root: Path) -> None:
        root = root.absolute()
        if any(parent.is_symlink() or parent.is_junction() for parent in [root, *root.parents]):
            raise BridgeFault("LINKED_BRIDGE_DIRECTORY")
        root.mkdir(parents=True, exist_ok=True)
        if any(parent.is_symlink() or parent.is_junction() for parent in [root, *root.parents]):
            raise BridgeFault("LINKED_BRIDGE_DIRECTORY")
        self.root = root.resolve(strict=True)

    def path(self, name: str) -> Path:
        if any(p.is_symlink() or p.is_junction() for p in [self.root, *self.root.parents]):
            raise BridgeFault("LINKED_BRIDGE_DIRECTORY")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,96}\.json", name):
            raise BridgeFault("INVALID_FILENAME")
        path = self.root / name
        if path.is_symlink() or path.is_junction():
            raise BridgeFault("LINKED_BRIDGE_FILE")
        return path

    def remove(self, name: str) -> None:
        self.path(name).unlink(missing_ok=True)

    def read(self, name: str) -> bytes:
        path = self.path(name)
        with path.open("rb") as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                raise BridgeFault("NOT_A_REGULAR_FILE")
            value = handle.read(MAX_WIRE_BYTES + 1)
        if len(value) > MAX_WIRE_BYTES:
            raise BridgeFault("WIRE_TOO_LARGE")
        return value

    def write(self, name: str, value: bytes) -> None:
        if len(value) > MAX_WIRE_BYTES:
            raise BridgeFault("WIRE_TOO_LARGE")
        destination = self.path(name)
        descriptor, temporary = tempfile.mkstemp(prefix=".aurum-", suffix=".tmp", dir=self.root)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(value)
                handle.flush()
                os.fsync(handle.fileno())
            self.path(name)
            os.replace(temporary, destination)
            if os.name != "nt":
                directory = os.open(self.root, os.O_RDONLY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
        finally:
            Path(temporary).unlink(missing_ok=True)
