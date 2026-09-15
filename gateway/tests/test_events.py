"""P1-11 tests: /sessions/{id} snapshot and the SSE /events feed."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from agent.replay import build_local_harness, load_run, replay
from gateway.app import create_app

RUN_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "recorded_runs" / "lena.json"


def _run_and_client() -> tuple[TestClient, str]:
    run = load_run(RUN_PATH)
    gateway, wallet, discover = build_local_harness(run.persona)
    result = replay(run, gateway=gateway, wallet=wallet, discover=discover)
    assert result.session_id is not None
    return TestClient(create_app(gateway.service)), result.session_id


def test_session_snapshot() -> None:
    client, sid = _run_and_client()
    resp = client.get(f"/sessions/{sid}")
    assert resp.status_code == 200
    snap = resp.json()
    assert snap["state"] == "DEPOT_OPENED"
    assert snap["audit_chain_ok"] is True
    assert snap["service_mode"] == "non_advised"
    assert snap["events"]
    assert snap["events"][-1]["to_state"] == "DEPOT_OPENED"
    # Events carry hash-chain evidence for the Ops console.
    assert all(e["hash"].startswith("sha256:") for e in snap["events"])


def test_unknown_session_is_404() -> None:
    client, _ = _run_and_client()
    assert client.get("/sessions/ses_does_not_exist").status_code == 404


def test_events_sse_backlog() -> None:
    client, sid = _run_and_client()
    resp = client.get("/events?once=true")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    data_lines = [ln for ln in resp.text.splitlines() if ln.startswith("data: ")]
    payloads = [json.loads(ln[len("data: ") :]) for ln in data_lines if ln != "data: {}"]
    # The lena run produced a stream of audit events for this session.
    assert any(p.get("session_id") == sid for p in payloads)
    assert any(p.get("to_state") == "DEPOT_OPENED" for p in payloads)
    assert resp.text.strip().endswith("data: {}")  # 'done' sentinel
