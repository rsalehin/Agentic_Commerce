"""Gateway service entrypoint (P0-04 skeleton: /health only).

FastMCP tools, rules engine and state machine are added in Phase 1.
"""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncIterator
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from gateway.card import provider_jwks, signed_card
from gateway.service import GatewayService

SERVICE = "gateway"
DEFAULT_PORT = 8080
UI_ORIGINS = ["http://localhost:5174", "http://127.0.0.1:5174"]


def create_app(service: GatewayService | None = None) -> FastAPI:
    app = FastAPI(title="Fonds AG Agent Gateway (Mock)")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=UI_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )
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

    # --- UI feeds (P1-11) ------------------------------------------------------

    @app.get("/sessions/{sid}")
    def get_session(sid: str) -> JSONResponse:
        snapshot = service.session_snapshot(sid)
        if snapshot is None:
            return JSONResponse({"error": {"code": "NOT_FOUND"}}, status_code=404)
        return JSONResponse(snapshot)

    @app.get("/events")
    async def events(request: Request, after: int = 0, once: bool = False) -> StreamingResponse:
        async def stream() -> AsyncIterator[str]:
            index = after
            log = service.event_log
            while index < len(log):
                yield f"data: {json.dumps(log[index])}\n\n"
                index += 1
            if once:
                yield "event: done\ndata: {}\n\n"
                return
            while not await request.is_disconnected():
                while index < len(service.event_log):
                    yield f"data: {json.dumps(service.event_log[index])}\n\n"
                    index += 1
                await asyncio.sleep(0.25)

        return StreamingResponse(stream(), media_type="text/event-stream")

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
