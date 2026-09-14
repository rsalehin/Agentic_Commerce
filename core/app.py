"""Core service entrypoint (P0-04 skeleton: /health only).

The mock Depotbank core (SQLModel tables, create_depot) and the BZSt/sanctions/
reference-account stubs are added in Phase 1.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI

SERVICE = "core"
DEFAULT_PORT = 8082


def create_app() -> FastAPI:
    app = FastAPI(title="Mock Depotbank Core")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": SERVICE}

    return app


app = create_app()


def main() -> None:
    import uvicorn

    load_dotenv()
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("CORE_PORT", DEFAULT_PORT))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
