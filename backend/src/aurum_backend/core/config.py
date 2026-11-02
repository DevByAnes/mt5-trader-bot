"""No token arguments, environment dumps or implicit network bind overrides."""

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from aurum_backend.security.secrets import bridge_key

SCENARIOS = (
    "normal",
    "ack-applied",
    "ea-offline",
    "python-offline",
    "bridge-offline",
    "stale",
    "seq-gap",
    "ack-rejected",
    "ack-timeout",
    "version-conflict",
    "daily-loss",
    "daily-profit",
    "daily-count",
    "wide-spread",
    "no-positions",
    "multi-positions",
)
DEFAULT_ORIGINS = (
    "tauri://localhost",
    "http://tauri.localhost",
    "https://tauri.localhost",
    "http://localhost:1420",
    "http://127.0.0.1:1420",
)


@dataclass(frozen=True)
class Config:
    token: str = field(repr=False)
    environment: str = "development"
    scenario: str = "normal"
    origins: tuple[str, ...] = DEFAULT_ORIGINS
    requests_per_minute: int = 240
    heartbeat_seconds: float = 2.0
    ack_seconds: float = 0.7
    send_timeout: float = 1.0
    queue_size: int = 32
    max_clients: int = 32
    max_operations: int = 10000
    max_body_bytes: int = 65536
    backend_mode: str = "fixture"
    bridge_directory: Path | None = None
    database_path: Path | None = None
    bridge_key: bytes | None = field(default=None, repr=False)
    bridge_key_id: str = "local-v1"
    ea_account: str = ""
    ea_symbol: str = "XAUUSD"
    ea_magic: int = 260110

    def __post_init__(self) -> None:
        if self.backend_mode not in {"fixture", "file"}:
            raise ValueError("Invalid backend mode")
        if self.backend_mode == "file" and (
            self.bridge_directory is None
            or self.database_path is None
            or not self.bridge_key
            or len(self.bridge_key) < 32
            or not self.ea_account
        ):
            raise ValueError("FILE mode requires explicit paths, key and EA identity")
        if self.backend_mode == "file" and self.scenario != "normal":
            raise ValueError("Scenarios are unavailable in FILE mode")
        if self.backend_mode == "file":
            for path in [self.bridge_directory, self.database_path]:
                if path is None or not path.is_absolute() or path.drive.startswith("\\\\"):
                    raise ValueError("FILE storage requires absolute local paths")
        if len(self.token) < 32 or not self.token.isascii() or any(c.isspace() for c in self.token):
            raise ValueError(
                "Session token must contain at least 32 non-whitespace ASCII characters"
            )
        if self.environment not in {"development", "production"}:
            raise ValueError("Invalid environment")
        if self.scenario not in SCENARIOS:
            raise ValueError("Invalid scenario")
        if self.environment == "production" and self.scenario != "normal":
            raise ValueError("Scenario injection is development-only")
        if not self.origins or any("*" in origin or origin == "null" for origin in self.origins):
            raise ValueError("Origins must be explicit")
        if (
            min(
                self.requests_per_minute,
                self.queue_size,
                self.max_clients,
                self.max_operations,
                self.max_body_bytes,
            )
            < 1
        ):
            raise ValueError("Invalid resource limit")
        if min(self.heartbeat_seconds, self.send_timeout) <= 0 or self.ack_seconds < 0:
            raise ValueError("Invalid timing")

    @classmethod
    def from_env(cls) -> "Config":
        token = os.environ.get("AURUM_SESSION_TOKEN", "")
        if not token and os.environ.get("AURUM_TOKEN_STDIN") == "1":
            token = sys.stdin.readline(4097).rstrip("\r\n")
        origins = os.environ.get("AURUM_ALLOWED_ORIGINS")
        mode = os.environ.get("AURUM_BACKEND_MODE", "fixture")
        return cls(
            token=token,
            environment=os.environ.get("AURUM_ENV", "development"),
            scenario=os.environ.get("AURUM_SCENARIO", "normal"),
            origins=tuple(x.strip() for x in origins.split(",") if x.strip())
            if origins is not None
            else DEFAULT_ORIGINS,
            backend_mode=mode,
            bridge_directory=Path(os.environ["AURUM_BRIDGE_DIRECTORY"])
            if os.environ.get("AURUM_BRIDGE_DIRECTORY")
            else None,
            database_path=Path(os.environ["AURUM_DATABASE_PATH"])
            if os.environ.get("AURUM_DATABASE_PATH")
            else None,
            bridge_key=bridge_key(),
            bridge_key_id=os.environ.get("AURUM_BRIDGE_KEY_ID", "local-v1"),
            ea_account=os.environ.get("AURUM_EA_ACCOUNT", ""),
            ea_symbol=os.environ.get("AURUM_EA_SYMBOL", "XAUUSD"),
            ea_magic=int(os.environ.get("AURUM_EA_MAGIC", "260110")),
        )
