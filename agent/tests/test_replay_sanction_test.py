"""P3-06: replay the recorded sanction_test run (confidential AML) to REJECTED.

The agent sees only the masked IN_REVIEW envelope; a compliance decision rejects
the case out of band, and the run ends at REJECTED without further recorded turns.
"""

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

RUN_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "recorded_runs" / "sanction_test.json"


def test_replay_sanction_test_ends_rejected() -> None:
    run = load_run(RUN_PATH)
    assert run.expected_final_state == "REJECTED"
    assert run.reviews == [{"decision": "reject", "actor": "compliance"}]

    gateway, wallet, discover = build_local_harness(run.persona)
    result = replay(run, gateway=gateway, wallet=wallet, discover=discover)

    assert result.state == "REJECTED"
    session = gateway.service.sessions[result.session_id].session
    assert session.verify_chain() is None

    # The confidential compliance escalation was rejected by compliance.
    reviews = gateway.service.list_escalations(queue="review")
    assert len(reviews) == 1
    assert reviews[0]["confidential"] is True
    assert reviews[0]["actor_role"] == "compliance"
    assert reviews[0]["status"] == "rejected"


def test_replay_sanction_test_over_http() -> None:
    run = load_run(RUN_PATH)
    service = build_service()
    http = TestClient(create_app(service))
    gateway, wallet, discover = build_http_harness(run.persona, http)

    result = replay(run, gateway=gateway, wallet=wallet, discover=discover)

    assert result.state == "REJECTED"
    snap = http.get(f"/sessions/{result.session_id}").json()
    assert snap["state"] == "REJECTED"
    assert snap["audit_chain_ok"] is True
