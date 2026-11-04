"""Serve the compiled local dashboard and same-origin in-memory session bootstrap."""

import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from starlette.responses import FileResponse, JSONResponse, Response

ROOT = Path(__file__).resolve().parents[2] / "dist"


def create_dashboard(root: Path = ROOT) -> FastAPI:
    app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)

    @app.post("/__aurum/session")
    async def session(request: Request) -> Response:
        host = request.headers.get("host")
        if (
            os.environ.get("AURUM_LOCAL_DEV") != "1"
            or host not in {"127.0.0.1:1420", "localhost:1420"}
            or not request.client
            or request.client.host != "127.0.0.1"
            or request.headers.get("origin") != f"http://{host}"
            or request.headers.get("sec-fetch-site") != "same-origin"
            or request.headers.get("x-aurum-session") != "1"
        ):
            return Response(status_code=403)
        token = os.environ.get("AURUM_SESSION_TOKEN")
        if not token:
            return Response(status_code=503)
        return JSONResponse({"token": token}, headers={"Cache-Control": "no-store"})

    @app.get("/{path:path}")
    def page(path: str, request: Request) -> Response:
        if (
            not request.client
            or request.client.host != "127.0.0.1"
            or request.headers.get("host") not in {"127.0.0.1:1420", "localhost:1420"}
        ):
            return Response(status_code=403)
        candidate = (root / path).resolve()
        if not candidate.is_relative_to(root.resolve()):
            return Response(status_code=404)
        if not candidate.is_file():
            if Path(path).suffix or path.startswith("__aurum"):
                return Response(status_code=404)
            candidate = root / "index.html"
        if not candidate.is_file():
            return Response("Build the dashboard first", status_code=503)
        return FileResponse(candidate, headers={"Cache-Control": "no-store"})

    return app


if __name__ == "__main__":
    uvicorn.run(create_dashboard(), host="127.0.0.1", port=1420, access_log=False)
