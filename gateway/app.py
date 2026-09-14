"""Gateway service entrypoint (P0-04 skeleton: /health only).

FastMCP tools, rules engine and state machine are added in Phase 1.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI

SERVICE = "gateway"
DEFAULT_PORT = 8080


def create_app() -> FastAPI:
    app = FastAPI(title="Fonds AG Agent Gateway (Mock)")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": SERVICE}

    return app


app = create_app()


def main() -> None:
    import uvicorn

    load_dotenv()
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("GATEWAY_PORT", DEFAULT_PORT))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
