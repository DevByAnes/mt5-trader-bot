"""Start the installed CLI on its fixed port; check real HTTP/WS; always stop it."""

import asyncio
import json
import os
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from websockets.asyncio.client import connect


def run_smoke(*, stdin: bool = False) -> None:
    token = secrets.token_urlsafe(48)
    environment = {
        **os.environ,
        "AURUM_ENV": "production",
        "AURUM_SCENARIO": "normal",
        "AURUM_BACKEND_MODE": "fixture",
    }
    environment.pop("AURUM_SESSION_TOKEN", None)
    environment.pop("AURUM_TOKEN_STDIN", None)
    if stdin:
        environment["AURUM_TOKEN_STDIN"] = "1"  # noqa: S105 -- boolean mode, not a credential
    else:
        environment["AURUM_SESSION_TOKEN"] = token
    executable = Path(sys.executable).with_name(
        "aurum-backend.exe" if os.name == "nt" else "aurum-backend"
    )
    process = subprocess.Popen(  # noqa: S603
        [str(executable)],
        env=environment,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0,
    )
    try:
        if stdin:
            assert process.stdin is not None  # noqa: S101
            process.stdin.write((token + "\n").encode())
            process.stdin.close()
            process.stdin = None
        url = "http://127.0.0.1:8765/api/v1/status"
        # Explicitly disable environment-configured proxies for loopback checks.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for _ in range(100):
            if process.poll() is not None:
                raise RuntimeError("CLI exited before readiness")
            try:
                request = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
                with opener.open(request, timeout=0.5) as response:  # noqa: S310
                    body = json.load(response)
                    if body["api_version"] == "1.0.0":
                        break
            except (OSError, urllib.error.URLError):
                time.sleep(0.05)
        else:
            raise RuntimeError("CLI readiness deadline exceeded")
        try:
            opener.open(url, timeout=1).close()  # noqa: S310
        except urllib.error.HTTPError as error:
            if error.code != 401:
                raise RuntimeError("Missing-token check failed") from None
            if json.load(error)["error"]["code"] != "UNAUTHORIZED":
                raise RuntimeError("Missing-token error envelope invalid") from None
        else:
            raise RuntimeError("Unauthenticated HTTP accepted")

        async def socket_check() -> None:
            async with connect(
                "ws://127.0.0.1:8765/ws",
                additional_headers={
                    "Authorization": "Bearer " + token,
                    "Origin": "http://127.0.0.1:1420",
                },
                open_timeout=2,
                proxy=None,
            ) as websocket:
                event = json.loads(await asyncio.wait_for(websocket.recv(), 2))
                if event["type"] != "heartbeat" or event["seq"] != 1:
                    raise RuntimeError("WebSocket initial event invalid")

        asyncio.run(socket_check())
        print(
            f"CLI smoke PASS ({'stdin' if stdin else 'environment'} token): "
            "127.0.0.1:8765 HTTP=200, missing token=401, WS heartbeat seq=1"
        )
    finally:
        process.terminate()
        stdout, stderr = process.communicate(timeout=5)
        if token.encode() in stdout + stderr:
            raise RuntimeError("Credential was leaked to process output")


def main() -> None:
    run_smoke()
    run_smoke(stdin=True)


if __name__ == "__main__":
    main()
