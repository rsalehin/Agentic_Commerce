"""Gateway service entrypoint (P0-04 skeleton: /health only).

FastMCP tools, rules engine and state machine are added in Phase 1.
"""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from gateway.card import provider_jwks, signed_card
from gateway.service import GatewayService

SERVICE = "gateway"
DEFAULT_PORT = 8080


def create_app(service: GatewayService | None = None) -> FastAPI:
    app = FastAPI(title="Fonds AG Agent Gateway (Mock)")
    service = service or GatewayService()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": SERVICE}

    @app.get("/.well-known/agent-card.json")
    def agent_card() -> JSONResponse:
        return JSONResponse(signed_card())

    @app.get("/.well-known/jwks.json")
    def jwks() -> JSONResponse:
        return JSONResponse(provider_jwks())

    # --- canonical REST surface (docs/05 §0); MCP mirrors these handlers -------

    @app.post("/v1/onboarding/start")
    def start(body: dict[str, Any]) -> JSONResponse:
        return JSONResponse(service.handle("onboarding.start", body))

    @app.post("/v1/onboarding/{sid}/identify")
    def identify(sid: str, body: dict[str, Any]) -> JSONResponse:
        return JSONResponse(service.handle("onboarding.identify", {**body, "session_id": sid}))

    @app.post("/v1/onboarding/{sid}/tax")
    def tax(sid: str, body: dict[str, Any]) -> JSONResponse:
        return JSONResponse(
            service.handle("onboarding.tax_declaration", {**body, "session_id": sid})
        )

    @app.post("/v1/onboarding/{sid}/appropriateness")
    def appropriateness(sid: str, body: dict[str, Any]) -> JSONResponse:
        return JSONResponse(
            service.handle("onboarding.appropriateness", {**body, "session_id": sid})
        )

    @app.post("/v1/onboarding/{sid}/documents")
    def documents(sid: str, body: dict[str, Any]) -> JSONResponse:
        return JSONResponse(service.handle("onboarding.get_documents", {**body, "session_id": sid}))

    @app.post("/v1/onboarding/{sid}/confirm")
    def confirm(sid: str, body: dict[str, Any]) -> JSONResponse:
        return JSONResponse(service.handle("onboarding.sign_contract", {**body, "session_id": sid}))

    @app.get("/v1/onboarding/{sid}")
    def status(sid: str) -> JSONResponse:
        return JSONResponse(service.handle("onboarding.status", {"session_id": sid}))

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
