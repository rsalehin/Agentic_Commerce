"""Populate a gateway with a recorded run and serve it for the UI (P1-13).

Runs the recorded transcript in-process (no LLM), then serves that same gateway
over HTTP so the split-screen UI (ui/, port 5174) can show a completed session
via /events + /sessions/{id}. Deck-demo convenience:

    uv run python -m agent.replay.demo_server            # lena on :8080
    uv run python -m agent.replay.demo_server marco 8080
"""

from __future__ import annotations

import sys

import uvicorn

from agent.replay.runner import RUNS_DIR, build_local_harness, load_run, replay
from gateway.app import create_app


def main(persona: str = "lena", port: int = 8080) -> None:
    run = load_run(RUNS_DIR / f"{persona}.json")
    gateway, wallet, discover = build_local_harness(run.persona)
    result = replay(run, gateway=gateway, wallet=wallet, discover=discover)
    print(f"[demo] {persona}: session {result.session_id} -> {result.state}")
    uvicorn.run(create_app(gateway.service), host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    persona = sys.argv[1] if len(sys.argv) > 1 else "lena"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
    main(persona, port)
