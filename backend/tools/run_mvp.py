"""Run the real FILE backend and local dashboard; optionally start MT5 with an inherited key."""

import argparse
import json
import os
import secrets
import socket
import subprocess
import sys
import time
from pathlib import Path

import keyring

from aurum_backend.security.secrets import bridge_key

ROOT = Path(__file__).resolve().parents[2]


def free(port: int) -> bool:
    with socket.socket() as probe:
        return probe.connect_ex(("127.0.0.1", port)) != 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account", required=True, help="Exact Demo account login (no password)")
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--magic", type=int, default=260110)
    parser.add_argument(
        "--terminal", type=Path, default=Path(r"C:\Program Files\MetaTrader 5\terminal64.exe")
    )
    parser.add_argument("--launch-terminal", action="store_true")
    parser.add_argument(
        "--provision-key", action="store_true", help="Create missing Windows Credential Manager key"
    )
    args = parser.parse_args()
    if sys.platform != "win32" or not args.account.isdecimal() or args.magic <= 0:
        parser.error("Windows, a numeric Demo login and positive magic are required")
    if not args.symbol or any(
        c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-"
        for c in args.symbol
    ):
        parser.error("Unsupported symbol characters")
    if not all(free(p) for p in (1420, 8765)):
        raise SystemExit("Ports 1420/8765 are occupied. Stop existing development servers first.")
    key_account = f"bridge/{args.account}-{args.symbol}-{args.magic}"
    os.environ["AURUM_KEYRING_ACCOUNT"] = key_account
    key = bridge_key()
    if key is None and args.provision_key:
        adapter = keyring.get_keyring()
        if not type(adapter).__module__.startswith("keyring.backends.Windows"):
            raise SystemExit("Windows Credential Manager adapter is required")
        keyring.set_password("AurumControl", key_account, secrets.token_hex(32))
        key = bridge_key()
    if key is None:
        raise SystemExit("No bridge key. Use --provision-key once or inject AURUM_BRIDGE_KEY_HEX.")
    if args.launch_terminal:
        running = subprocess.run(  # noqa: S603
            [
                str(Path(os.environ["SystemRoot"]) / "System32/tasklist.exe"),
                "/FI",
                "IMAGENAME eq terminal64.exe",
                "/FO",
                "CSV",
                "/NH",
            ],
            capture_output=True,
            text=True,
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if '"terminal64.exe"' in running.stdout.lower():
            raise SystemExit(
                "Close MT5 manually first so the newly launched process can inherit its key."
            )
        args.terminal = args.terminal.resolve(strict=True)
    directory = (
        Path(os.environ["APPDATA"])
        / "MetaQuotes/Terminal/Common/Files/Aurum"
        / f"{args.account}-{args.symbol}-{args.magic}"
    )
    directory.mkdir(parents=True, exist_ok=True)
    database = ROOT / "backend/.evidence/mvp" / f"{args.account}-{args.symbol}-{args.magic}.sqlite"
    database.parent.mkdir(parents=True, exist_ok=True)
    environment = {
        **os.environ,
        "AURUM_SESSION_TOKEN": secrets.token_urlsafe(48),
        "AURUM_BRIDGE_KEY_HEX": key.hex(),
        "AURUM_BACKEND_MODE": "file",
        "AURUM_ENV": "development",
        "AURUM_SCENARIO": "normal",
        "AURUM_BRIDGE_DIRECTORY": str(directory),
        "AURUM_DATABASE_PATH": str(database),
        "AURUM_EA_ACCOUNT": args.account,
        "AURUM_EA_SYMBOL": args.symbol,
        "AURUM_EA_MAGIC": str(args.magic),
        "AURUM_ALLOWED_ORIGINS": (
            "http://127.0.0.1:1420,http://localhost:1420,tauri://localhost,"
            "http://tauri.localhost,https://tauri.localhost"
        ),
        "AURUM_LOCAL_DEV": "1",
        "VITE_LOCAL_SESSION": "true",
        "VITE_USE_MOCKS": "false",
    }
    node = Path(
        subprocess.check_output(  # noqa: S603
            [str(Path(os.environ["SystemRoot"]) / "System32/where.exe"), "node"],
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        ).splitlines()[0]
    )  # noqa: S603,S607
    children: list[subprocess.Popen[bytes]] = []
    try:
        children.append(
            subprocess.Popen(  # noqa: S603
                [sys.executable, "-m", "aurum_backend.main"],
                cwd=ROOT / "backend",
                env=environment,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        )  # noqa: S603
        children.append(
            subprocess.Popen(  # noqa: S603
                [str(node), str(ROOT / "node_modules/vite/bin/vite.js"), "--host", "127.0.0.1"],
                cwd=ROOT,
                env=environment,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        )  # noqa: S603
        if args.launch_terminal:
            # Intentionally visible: user must attach EA and review its inputs inside MT5.
            subprocess.Popen([str(args.terminal)], env=environment)  # noqa: S603
        print(
            json.dumps(
                {
                    "dashboard": "http://127.0.0.1:1420",
                    "bridge": str(directory),
                    "mode": "FILE; EA default SIGNAL_ONLY",
                }
            )
        )
        print(
            "Ctrl+C stops this launcher's backend/dashboard. MT5 remains open to manage positions."
        )
        while all(child.poll() is None for child in children):
            time.sleep(0.5)
        if any(child.returncode not in (None, 0) for child in children):
            raise SystemExit("A local service exited; inspect its preceding output")
    except KeyboardInterrupt:
        pass
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            child.wait(timeout=10)


if __name__ == "__main__":
    main()
