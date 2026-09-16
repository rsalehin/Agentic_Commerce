"""Interactive run service (P3-07).

Drives the Kundenagent orchestrator against a running gateway while the three
human-only approvals (mandate, tax, contract) are answered from the UI by
clicking Signieren / Ablehnen. Default driver is the recorded script
(deterministic, no LLM); the live LLM driver is optional behind mode="live".

One run at a time. The run executes in a daemon thread; `ask_human` blocks that
thread on a per-prompt event until the UI POSTs a decision (or a 15-minute
timeout, treated as a decline). Signieren -> the orchestrator continues;
Ablehnen -> `CustomerDeclined` unwinds the run, the gateway session (if one
exists) is cancelled (-> CANCELLED), and the run finishes `declined`.
"""

from __future__ import annotations

import asyncio
import json
import os
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from agent.llm import ScriptedProvider
from agent.llm.base import LLMProvider
from agent.orchestrator import Orchestrator
from agent.replay.runner import RUNS_DIR, build_http_harness, load_run
from agent.sender import build_sender_proof

SERVICE = "runner"
DEFAULT_PORT = 8083
UI_ORIGINS = ["http://localhost:5174", "http://127.0.0.1:5174"]
PERSONAS = {"lena", "marco", "sanction_test"}
DECLINE_TIMEOUT_S = 15 * 60


class CustomerDeclined(Exception):
    """The customer clicked Ablehnen (or the prompt timed out)."""


@dataclass
class Prompt:
    prompt_id: str
    purpose: str | None
    question_de: str
    payload: dict[str, Any] | None
    created_at: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


HttpFactory = Callable[[], Any]


def _default_http_factory() -> Any:
    gateway_url = os.environ.get("GATEWAY_URL", "http://localhost:8080")
    return httpx.Client(base_url=gateway_url, timeout=30.0)


class RunManager:
    """Holds a single active run and coordinates the blocking approvals."""

    def __init__(self, http_factory: HttpFactory | None = None) -> None:
        self._http_factory = http_factory or _default_http_factory
        self._lock = threading.Lock()
        self.run_id: str | None = None
        self.persona: str | None = None
        self.mode: str | None = None
        self.status: str = "idle"  # idle|running|waiting|finished|error
        self.session_id: str | None = None
        self.state: str | None = None
        self.declined: bool = False
        self.error: str | None = None
        self.pending: Prompt | None = None
        self.events: list[dict[str, Any]] = []
        self._seen_prompts: set[str] = set()
        self._decision_event: threading.Event | None = None
        self._decision_result: bool | None = None
        self._orch: Orchestrator | None = None

    # --- lifecycle -------------------------------------------------------------

    def start(self, persona: str, mode: str) -> tuple[dict[str, Any], int]:
        if persona not in PERSONAS:
            return {"error": {"code": "BAD_PERSONA", "detail": persona}}, 400
        if mode not in ("script", "live"):
            return {"error": {"code": "BAD_MODE", "detail": mode}}, 400
        if mode == "live" and not os.environ.get("ANTHROPIC_API_KEY"):
            return {"error": {"code": "NO_API_KEY", "detail": "ANTHROPIC_API_KEY not set"}}, 400
        with self._lock:
            if self.status in ("running", "waiting"):
                return {"error": {"code": "RUN_ACTIVE", "detail": self.run_id}}, 409
            run_id = f"run_{uuid.uuid4().hex[:12]}"
            self.run_id = run_id
            self.persona = persona
            self.mode = mode
            self.status = "running"
            self.session_id = None
            self.state = None
            self.declined = False
            self.error = None
            self.pending = None
            self.events = []
            self._seen_prompts = set()
            self._decision_event = None
            self._decision_result = None
            self._orch = None
        threading.Thread(target=self._run, args=(run_id, persona, mode), daemon=True).start()
        return {"run_id": run_id}, 200

    def _build_provider(self, run: Any, mode: str) -> LLMProvider:
        if mode == "live":
            from agent.llm.anthropic_provider import AnthropicProvider

            return AnthropicProvider()
        return ScriptedProvider.from_calls([(t["tool"], t["input"]) for t in run.turns])

    def _run(self, run_id: str, persona: str, mode: str) -> None:
        try:
            run = load_run(RUNS_DIR / f"{persona}.json")
            provider = self._build_provider(run, mode)
            with self._http_factory() as http:
                gateway, wallet, discover = build_http_harness(persona, http)
                decisions = iter(run.reviews)

                def on_review(session_id: str) -> None:
                    decision = next(decisions, None)
                    if decision is None:
                        return
                    open_reviews = gateway.list_open_reviews(session_id)
                    if open_reviews:
                        gateway.decide(
                            open_reviews[-1]["id"],
                            decision["decision"],
                            decision.get("actor", "adviser"),
                        )

                orch = Orchestrator(
                    provider,
                    gateway,
                    wallet,
                    self._ask_human,
                    discover=discover,
                    on_review=on_review,
                )
                with self._lock:
                    self._orch = orch
                try:
                    result = orch.run(run.intent_de)
                except CustomerDeclined:
                    self._handle_decline(gateway, wallet, orch)
                    return
                with self._lock:
                    self.session_id = result.session_id
                    self.state = result.state
                    self.status = "finished"
                self._publish(
                    {"type": "finished", "session_id": result.session_id, "state": result.state}
                )
        except Exception as exc:  # noqa: BLE001 - surface any run failure as an event
            with self._lock:
                self.status = "error"
                self.error = str(exc)
            self._publish({"type": "error", "message": str(exc)})
        finally:
            with self._lock:
                self._orch = None

    def _handle_decline(self, gateway: Any, wallet: Any, orch: Orchestrator) -> None:
        sid = orch._sid  # noqa: SLF001 - the manager owns this orchestrator
        if sid:
            proof = build_sender_proof(
                wallet.instance_key,
                wallet.instance_kid,
                htm="POST",
                htu=gateway.htu("onboarding.cancel", sid),
                session_id=sid,
                now=int(time.time()),
            )
            gateway.cancel(sid, proof)
            with self._lock:
                self.session_id = sid
                self.state = "CANCELLED"
                self.declined = True
                self.status = "finished"
            self._publish({"type": "declined", "session_id": sid, "state": "CANCELLED"})
        else:
            # Declined before onboarding.start: nothing was ever sent to the
            # provider, so there is no gateway session and no CANCELLED state.
            with self._lock:
                self.session_id = None
                self.state = None
                self.declined = True
                self.status = "finished"
            self._publish({"type": "declined", "session_id": None, "state": None})

    # --- approvals -------------------------------------------------------------

    def _ask_human(self, question_de: str, payload: dict[str, Any] | None) -> dict[str, Any]:
        purpose = (payload or {}).get("purpose")
        prompt = Prompt(
            prompt_id=f"prm_{uuid.uuid4().hex[:12]}",
            purpose=str(purpose) if purpose else None,
            question_de=question_de,
            payload=payload,
            created_at=time.time(),
        )
        event = threading.Event()
        with self._lock:
            self.pending = prompt
            self._seen_prompts.add(prompt.prompt_id)
            self._decision_event = event
            self._decision_result = None
            self.status = "waiting"
        self._publish({"type": "prompt", **prompt.to_dict()})

        got = event.wait(timeout=DECLINE_TIMEOUT_S)
        with self._lock:
            approved = bool(self._decision_result) if got else False
            self.pending = None
            self._decision_event = None
            self.status = "running"
        self._publish({"type": "decision", "prompt_id": prompt.prompt_id, "approved": approved})
        if not approved:
            raise CustomerDeclined(prompt.purpose or "prompt")
        return {"approved": True, "answer": "ja"}

    def decide(self, run_id: str, prompt_id: str, approved: bool) -> tuple[dict[str, Any], int]:
        with self._lock:
            if run_id != self.run_id or prompt_id not in self._seen_prompts:
                return {"error": {"code": "NOT_FOUND"}}, 404
            if self.pending is None or self.pending.prompt_id != prompt_id:
                return {"error": {"code": "NOT_PENDING"}}, 409
            self._decision_result = approved
            event = self._decision_event
        if event is not None:
            event.set()
        return {"ok": True}, 200

    # --- reads -----------------------------------------------------------------

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            state = self.state
            session_id = self.session_id
            if self._orch is not None and self.status not in ("finished", "error"):
                session_id = self._orch._sid or session_id  # noqa: SLF001
                state = self._orch._state or state  # noqa: SLF001
            return {
                "run_id": self.run_id,
                "status": self.status,
                "session_id": session_id,
                "state": state,
                "pending_prompt": self.pending.to_dict() if self.pending else None,
                "declined": self.declined,
                "error": self.error,
            }

    def _publish(self, frame: dict[str, Any]) -> None:
        with self._lock:
            self.events.append(frame)

    def events_after(self, index: int) -> list[dict[str, Any]]:
        with self._lock:
            return self.events[index:]

    def is_terminal(self) -> bool:
        with self._lock:
            return self.status in ("finished", "error", "idle")


# --- app ----------------------------------------------------------------------


def create_runner_app(http_factory: HttpFactory | None = None) -> FastAPI:
    app = FastAPI(title="Kundenagent Runner (P3-07)")
    app.add_middleware(
        CORSMiddleware, allow_origins=UI_ORIGINS, allow_methods=["*"], allow_headers=["*"]
    )
    manager = RunManager(http_factory)
    app.state.manager = manager

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": SERVICE}

    @app.post("/runs")
    def start_run(body: dict[str, Any]) -> JSONResponse:
        result, code = manager.start(body.get("persona", ""), body.get("mode", "script"))
        return JSONResponse(result, status_code=code)

    @app.get("/runs/{run_id}")
    def get_run(run_id: str) -> JSONResponse:
        snap = manager.snapshot()
        if snap["run_id"] != run_id:
            return JSONResponse({"error": {"code": "NOT_FOUND"}}, status_code=404)
        return JSONResponse(snap)

    @app.post("/runs/{run_id}/prompts/{prompt_id}")
    def decide_prompt(run_id: str, prompt_id: str, body: dict[str, Any]) -> JSONResponse:
        result, code = manager.decide(run_id, prompt_id, bool(body.get("approved")))
        return JSONResponse(result, status_code=code)

    @app.get("/runs/{run_id}/events")
    async def run_events(run_id: str, request: Request, after: int = 0) -> StreamingResponse:
        async def stream() -> Any:
            index = after
            while True:
                for frame in manager.events_after(index):
                    yield f"data: {json.dumps(frame)}\n\n"
                    index += 1
                if manager.is_terminal() and manager.snapshot()["run_id"] == run_id:
                    # drain any last frames, then stop
                    for frame in manager.events_after(index):
                        yield f"data: {json.dumps(frame)}\n\n"
                        index += 1
                    yield "event: done\ndata: {}\n\n"
                    return
                if await request.is_disconnected():
                    return
                await asyncio.sleep(0.2)

        return StreamingResponse(stream(), media_type="text/event-stream")

    return app


app = create_runner_app()


def main() -> None:
    import uvicorn

    load_dotenv()
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("RUNNER_PORT", DEFAULT_PORT))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
