"""Replay a recorded run through a RUNNING gateway over HTTP (P1-13).

    uv run python -m agent.replay                 # lena against http://localhost:8080
    uv run python -m agent.replay marco http://localhost:8080

Start the gateway first (run.ps1 / python -m gateway.app). This is the
interview fallback: no LLM call, only the recorded tool-call decisions replayed;
crypto is regenerated live and verified by the real gateway.
"""

from __future__ import annotations

import os
import sys

import httpx

from agent.replay.runner import RUNS_DIR, build_http_harness, load_run, replay


def main(persona: str, base_url: str) -> int:
    run = load_run(RUNS_DIR / f"{persona}.json")
    with httpx.Client(base_url=base_url, timeout=10.0) as http:
        gateway, wallet, discover = build_http_harness(run.persona, http)
        result = replay(run, gateway=gateway, wallet=wallet, discover=discover)
    print(f"[replay] {persona}: session {result.session_id} -> {result.state}")
    return 0 if result.state == run.expected_final_state else 1


if __name__ == "__main__":
    persona = sys.argv[1] if len(sys.argv) > 1 else "lena"
    base_url = sys.argv[2] if len(sys.argv) > 2 else os.environ.get(
        "GATEWAY_URL", "http://localhost:8080"
    )
    raise SystemExit(main(persona, base_url))
