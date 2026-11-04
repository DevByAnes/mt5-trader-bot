"""Build a source+compiled-UI Demo test bundle; never include local credentials or evidence."""

import hashlib
import json
import shutil
from pathlib import Path
from uuid import uuid4

from tools.native_check import compile_script

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    if not (ROOT / "dist/index.html").is_file():
        raise SystemExit("Run npm run release:build first")
    stage = ROOT / "releases" / ("aurum-forward-" + uuid4().hex[:8])
    stage.mkdir(parents=True)
    for name in ("dist", "mql5", "schema", "fixtures"):
        shutil.copytree(ROOT / name, stage / name, ignore=shutil.ignore_patterns("*.log", "*.ex5"))
    backend = stage / "backend"
    backend.mkdir()
    for name in ("src", "tools"):
        shutil.copytree(
            ROOT / "backend" / name, backend / name,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    for name in ("pyproject.toml", "uv.lock", ".python-version"):
        shutil.copy2(ROOT / "backend" / name, backend / name)
    compile_script(
        Path(r"C:\Program Files\MetaTrader 5\MetaEditor64.exe"),
        stage / "mql5/Experts/AurumControl.mq5", stage,
    )
    shutil.copy2(ROOT / "docs/FORWARD_WEEK.fa.md", stage / "README.fa.md")
    (stage / "Start.cmd").write_text(
        '@echo off\r\ncd /d "%~dp0backend"\r\n'
        'python -m uv sync --frozen --managed-python --no-dev --extra mt5\r\n'
        'if errorlevel 1 goto failed\r\n'
        '.venv\\Scripts\\python.exe -m tools.run_mvp --provision-key %*\r\n'
        ':failed\r\npause\r\n', encoding="ascii",
    )
    manifest = {}
    for file in sorted(stage.rglob("*")):
        if file.is_file() and file.suffix != ".log":
            manifest[str(file.relative_to(stage)).replace("\\", "/")] = hashlib.sha256(
                file.read_bytes()
            ).hexdigest()
    (stage / "SHA256.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    archive = shutil.make_archive(str(stage), "zip", stage)
    print(json.dumps({"bundle": str(stage), "archive": archive, "files": len(manifest)}))


if __name__ == "__main__":
    main()
