"""Deterministically regenerate Pydantic v2 DTOs from both frozen schemas."""

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "backend/src/aurum_backend/models"
SOURCES = {
    "generated.py": ("openapi.yaml", "openapi"),
    "generated_settings.py": ("settings.schema.json", "jsonschema"),
}


def outputs() -> dict[str, str]:
    result: dict[str, str] = {}
    for filename, (source, kind) in SOURCES.items():
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / filename
            command = [
                sys.executable,
                "-m",
                "datamodel_code_generator",
                "--input",
                str(ROOT / "schema" / source),
                "--input-file-type",
                kind,
                "--output",
                str(output),
                "--output-model-type",
                "pydantic_v2.BaseModel",
                "--target-python-version",
                "3.12",
                "--disable-timestamp",
                "--use-standard-collections",
                "--use-union-operator",
                "--enum-field-as-literal",
                "all",
                "--field-constraints",
                "--use-annotated",
                "--strict-types",
                "str",
                "int",
                "float",
                "bool",
                "--formatters",
                "ruff-check",
                "ruff-format",
                "--no-allow-remote-refs",
                "--base-class",
                "aurum_backend.models.base.SchemaModel",
            ]
            if kind == "jsonschema":
                command += ["--class-name", "SettingsMetadataValues"]
            subprocess.run(command, check=True, capture_output=True)  # noqa: S603
            subprocess.run(  # noqa: S603
                [
                    sys.executable,
                    "-m",
                    "ruff",
                    "check",
                    "--fix",
                    "--config",
                    str(ROOT / "backend/pyproject.toml"),
                    str(output),
                ],
                check=True,
                capture_output=True,
            )
            result[filename] = output.read_text(encoding="utf-8")
    hashes = {
        p: hashlib.sha256((ROOT / "schema" / p).read_bytes()).hexdigest()
        for p in ["openapi.yaml", "settings.schema.json", "events.json"]
    }
    result["sources.json"] = json.dumps(hashes, indent=2, sort_keys=True) + "\n"
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for filename, content in outputs().items():
        path = TARGET / filename
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                raise SystemExit(f"Generated model drift: {filename}")
        else:
            path.write_text(content, encoding="utf-8", newline="\n")
    print("Generated models match frozen schemas" if args.check else "Generated Pydantic v2 models")


if __name__ == "__main__":
    main()
