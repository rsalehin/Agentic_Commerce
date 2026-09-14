"""Wallet service entrypoint (P0-04 skeleton: /health only).

On server start it ensures the mock key material exists (P0-03). PID issuance,
SD-JWT presentation and the mock QES are added in Phase 1.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI

from wallet.keys import ensure_keys

SERVICE = "wallet"
DEFAULT_PORT = 8081


def create_app() -> FastAPI:
    app = FastAPI(title="Mock EUDI Wallet")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": SERVICE}

    return app


app = create_app()


def main() -> None:
    import uvicorn

    load_dotenv()
    ensure_keys()  # generate key material on first run
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("WALLET_PORT", DEFAULT_PORT))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
