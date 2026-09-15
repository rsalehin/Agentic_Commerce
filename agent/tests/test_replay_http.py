"""P1-13: replay the recorded lena run through the gateway over HTTP (REST)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from agent.replay import build_http_harness, build_service, load_run, replay
from gateway.app import create_app

RUN_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "recorded_runs" / "lena.json"


def test_replay_lena_through_http_reaches_depot_opened() -> None:
    run = load_run(RUN_PATH)
    service = build_service()
    http = TestClient(create_app(service))  # exercises the real REST surface

    gateway, wallet, discover = build_http_harness(run.persona, http)
    result = replay(run, gateway=gateway, wallet=wallet, discover=discover)

    assert result.state == run.expected_final_state == "DEPOT_OPENED"
    assert result.session_id is not None

    # The gateway behind HTTP has a verifying audit chain.
    session = service.sessions[result.session_id].session
    assert session.verify_chain() is None

    # And the same session is visible via the REST snapshot endpoint.
    snap = http.get(f"/sessions/{result.session_id}").json()
    assert snap["state"] == "DEPOT_OPENED"
    assert snap["audit_chain_ok"] is True
