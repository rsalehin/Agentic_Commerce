"""P2-06: replay the recorded marco run (two escalations) to ADVISED_HANDOFF."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from agent.replay import (
    build_http_harness,
    build_local_harness,
    build_service,
    load_run,
    replay,
)
from gateway.app import create_app

RUN_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "recorded_runs" / "marco.json"


def test_recorded_marco_reaches_advised_handoff_in_process() -> None:
    run = load_run(RUN_PATH)
    assert run.expected_final_state == "ADVISED_HANDOFF"
    assert len(run.reviews) == 2

    gateway, wallet, discover = build_local_harness(run.persona)
    result = replay(run, gateway=gateway, wallet=wallet, discover=discover)

    assert result.state == "ADVISED_HANDOFF"
    session = gateway.service.sessions[result.session_id].session
    assert session.verify_chain() is None

    reviews = gateway.service.list_escalations(queue="review")
    assert {e["status"] for e in reviews} == {"approved", "appointment"}


def test_recorded_marco_over_http() -> None:
    run = load_run(RUN_PATH)
    service = build_service()
    http = TestClient(create_app(service))
    gateway, wallet, discover = build_http_harness(run.persona, http)

    result = replay(run, gateway=gateway, wallet=wallet, discover=discover)

    assert result.state == "ADVISED_HANDOFF"
    snap = http.get(f"/sessions/{result.session_id}").json()
    assert snap["state"] == "ADVISED_HANDOFF"
    assert snap["audit_chain_ok"] is True
