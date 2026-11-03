"""Compile and run non-trading MQL5 scripts in a fresh, account-free portable terminal."""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from aurum_backend.bridge.codec import SignedCodec, json_bytes
from aurum_backend.bridge.files import AtomicFiles
from aurum_backend.models.generated_settings_v2 import EASettings
from aurum_backend.services.profiles import defaults

ROOT = Path(__file__).resolve().parents[2]


def hidden() -> dict[str, Any]:
    factory = getattr(subprocess, "STARTUPINFO", None)
    if factory is None:
        raise RuntimeError("Native runner is Windows-only")
    startup = factory()
    startup.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 0)
    startup.wShowWindow = 0
    return {"startupinfo": startup, "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}


def compile_script(editor: Path, source: Path, evidence: Path) -> dict[str, Any]:
    log = evidence / (source.stem + ".compile.log")
    binary = source.with_suffix(".ex5")
    binary.unlink(missing_ok=True)
    # MetaEditor's parser requires quotes around the switch value when a path contains spaces.
    subprocess.run(  # noqa: S603
        f'"{editor}" /compile:"{source}" /log:"{log}"', timeout=60, **hidden()
    )
    raw = log.read_bytes() if log.exists() else b""
    text = raw.decode("utf-16") if raw.startswith(b"\xff\xfe") else raw.decode("utf-8")
    match = re.search(r"Result: (\d+) errors, (\d+) warnings", text)
    if not binary.is_file() or not match or match.groups() != ("0", "0"):
        raise RuntimeError(f"Native compile failed or warned: {source.name}; see {log}")
    return {"script": source.name, "errors": 0, "warnings": 0}


def run_script(
    runtime: Path,
    script: str,
    filename: str,
    *,
    preset: str = "",
    allow_dll: bool = False,
    environment: dict[str, str] | None = None,
) -> dict[str, Any]:
    result = runtime / "MQL5/Files" / filename
    result.unlink(missing_ok=True)
    config = runtime / "run.ini"
    config.write_text(
        "[Common]\nLogin=0\nKeepPrivate=0\nNewsEnable=0\n"
        f"[Experts]\nEnabled=1\nAllowLiveTrading=0\nAllowDllImport={int(allow_dll)}\n"
        f"[StartUp]\nScript=AurumTests\\Tests\\{script}\n"
        f"ScriptParameters={preset}\nSymbol=EURUSD\nPeriod=M15\nShutdownTerminal=1\n",
        encoding="utf-8",
    )
    process = subprocess.Popen(  # noqa: S603
        f'"{runtime / "terminal64.exe"}" /portable /config:"{config}"',
        cwd=runtime,
        env=environment,
        **hidden(),
    )
    try:
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline and not result.exists() and process.poll() is None:
            time.sleep(0.1)
        if not result.exists():
            raise RuntimeError(f"No native result for {script}; inspect isolated terminal logs")
        # The script closes its file before startup shutdown. Wait before reading or relaunching.
        process.wait(timeout=10)
        value: dict[str, Any] = json.loads(result.read_text(encoding="utf-8-sig"))
        return value
    finally:
        if process.poll() is None:
            process.terminate()  # Only this invocation's new, account-free process.
            process.wait(timeout=5)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installation", type=Path, default=Path(r"C:\Program Files\MetaTrader 5"))
    args = parser.parse_args()
    if sys.platform != "win32":
        raise SystemExit("Native checks require Windows and an installed MetaTrader 5")
    install = args.installation.resolve(strict=True)
    editor = install / "MetaEditor64.exe"
    terminal = install / "terminal64.exe"
    if not editor.is_file() or not terminal.is_file():
        raise SystemExit("MetaEditor64.exe and terminal64.exe are required")
    evidence = ROOT / "backend/.evidence/native" / uuid4().hex
    stage = evidence / "source"
    shutil.copytree(ROOT / "mql5", stage)
    compiled = [
        compile_script(editor, stage / "Tests" / name, evidence)
        for name in [
            "InputsTest.mq5",
            "EconomicsTest.mq5",
            "BrokerReadOnlyTest.mq5",
            "V1EngineTest.mq5",
            "V1BridgeTest.mq5",
        ]
    ]
    compiled.append(compile_script(editor, stage / "Experts/AurumControl.mq5", evidence))
    runtime = evidence / "runtime"
    runtime.mkdir()
    shutil.copy2(terminal, runtime / "terminal64.exe")
    # Only installation seed symbols; never copy user account/config/profile/credential files.
    if (install / "Bases").is_dir():
        shutil.copytree(install / "Bases", runtime / "Bases")
    shutil.copytree(stage, runtime / "MQL5/Scripts/AurumTests")
    presets = runtime / "MQL5/Presets"
    presets.mkdir(parents=True)
    inputs = run_script(runtime, "InputsTest", "aurum_inputs_test.json")
    EASettings.model_validate(inputs["settings"])
    if not inputs["valid"] or inputs["settings"] != defaults():
        raise RuntimeError("Native defaults differ from authoritative schema")
    if inputs["escape_sample"] != 'quote=" slash=\\\r\n\t' + chr(1) + " فارسی":
        raise RuntimeError("Native JSON Unicode/control escaping mismatch")
    cases = []
    for field, value in [
        ("InpMagic", "0"),
        ("InpMinNetRR", "1.9"),
        ("InpRiskPerTrade", "0.55"),
        ("InpExecutionMode", "-1"),
    ]:
        (presets / "invalid.set").write_text(f"{field}={value}\r\n", encoding="utf-16")
        invalid = run_script(runtime, "InputsTest", "aurum_inputs_test.json", preset="invalid.set")
        if invalid["valid"] or field not in invalid["reason"]:
            raise RuntimeError(f"Invalid native input was not rejected: {field}")
        cases.append({"field": field, "rejected": True})
    economics = run_script(runtime, "EconomicsTest", "aurum_economics_test.json")
    if economics["failures"] != 0 or economics["checks"] != 9:
        raise RuntimeError("Native economic vectors failed")
    v1 = run_script(runtime, "V1EngineTest", "aurum_v1_test.json")
    if v1["failures"] != 0 or v1["checks"] < 45:
        raise RuntimeError(f"Native V1 vectors failed: {v1}")
    decoded = SignedCodec(bytes(range(32))).decode(
        json_bytes(v1["wire"]),
        expected_sender="EA",
        expected_kind="ACK",
        now_ms=1793613600000,
    )
    if decoded["body"]["status"] != "APPLIED":
        raise RuntimeError("Native-to-Python signature/schema interoperability failed")
    v1.pop("wire")
    # Account-free kernel32 environment read only. Public test vector key, unique namespace;
    # no user terminal profile, credentials or operational Common folder are copied/modified.
    test_directory = "AurumNativeTests/" + uuid4().hex
    common = Path(os.environ["APPDATA"]) / "MetaQuotes/Terminal/Common/Files" / test_directory
    files = AtomicFiles(common)
    codec = SignedCodec(bytes(range(32)))
    now = int(time.time() * 1000)
    instance = "22345678-1234-4234-a234-123456789abc"

    def inbound(identity: str, kind: str, body: dict[str, Any]) -> bytes:
        return codec.encode(
            {
                "kind": kind,
                "sender": "PYTHON",
                "message_id": identity,
                "ea_instance_id": instance,
                "seq": 1,
                "issued_at_ms": now,
                "expires_at_ms": now + 300000,
                "body": body,
            }
        )

    kill_id = "32345678-1234-4234-a234-123456789abc"
    config_id = "42345678-1234-4234-a234-123456789abc"
    files.write(
        "command_" + kill_id + ".json",
        inbound(
            kill_id,
            "COMMAND",
            {
                "request_id": kill_id,
                "command": "kill-switch",
                "position_id": None,
            },
        ),
    )
    files.write(
        "config_" + config_id + ".json",
        inbound(
            config_id,
            "CONFIG",
            {
                "request_id": config_id,
                "base_version": 1,
                "config_version": 2,
                "values": {
                    "executionMode": "SIGNAL_ONLY",
                    "riskPerTrade": 0.4,
                    "dailyLossLimit": 2,
                    "maxSpread": 30,
                    "allowRemoteConfig": True,
                    "allowRealAccount": False,
                },
                "apply_at": "NEXT_M15",
                "confirmed_loosen": False,
            },
        ),
    )
    bad_id = "52345678-1234-4234-a234-123456789abc"
    bad = json.loads(
        inbound(
            bad_id,
            "COMMAND",
            {
                "request_id": bad_id,
                "command": "kill-switch",
                "position_id": None,
            },
        )
    )
    bad["hmac_sha256"] = "0" * 64
    files.write("command_" + bad_id + ".json", json_bytes(bad))
    files.write(
        "python_heartbeat.json", inbound(str(uuid4()), "HEARTBEAT", {"api_version": "1.0.0"})
    )
    (presets / "bridge.set").write_text(
        "AllowRemoteConfig=true\r\nTestDirectory=" + test_directory.replace("/", "\\") + "\r\n",
        encoding="utf-16",
        newline="",
    )
    native_bridge = run_script(
        runtime,
        "V1BridgeTest",
        "aurum_v1_bridge_test.json",
        preset="bridge.set",
        allow_dll=True,
        environment={**os.environ, "AURUM_BRIDGE_KEY_HEX": bytes(range(32)).hex()},
    )
    if native_bridge["failures"] or native_bridge["checks"] < 12:
        raise RuntimeError(f"Native bridge vectors failed: {native_bridge}")
    for name in ("kill", "config", "state"):
        observed = codec.decode(json_bytes(native_bridge.pop(name)), expected_sender="EA")
        if name != "state" and observed["body"]["status"] != "APPLIED":
            raise RuntimeError(f"Native {name} did not apply")
    report = {
        "build": inputs["build"],
        "compile": compiled,
        "input_defaults": len(inputs["settings"]),
        "schema_match": True,
        "unicode_controls_roundtrip": True,
        "invalid_inputs": cases,
        "economics": economics,
        "v1": v1,
        "v1_bridge": native_bridge,
        "native_python_wire_interoperability": True,
        "account_used": False,
        "orders_submitted": False,
    }
    (evidence / "summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print("Evidence:", evidence)


if __name__ == "__main__":
    main()
