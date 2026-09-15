"""P2-05 tests: the Nachweis view (rule -> satisfying evidence) + JSON export."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from agent.replay import build_local_harness, load_run, replay
from gateway.app import create_app

RUN_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "recorded_runs" / "lena.json"


def _client_and_sid() -> tuple[TestClient, str]:
    run = load_run(RUN_PATH)
    gateway, wallet, discover = build_local_harness(run.persona)
    result = replay(run, gateway=gateway, wallet=wallet, discover=discover)
    assert result.session_id is not None
    return TestClient(create_app(gateway.service)), result.session_id


def test_evidence_maps_each_rule_to_its_law_and_evidence() -> None:
    client, sid = _client_and_sid()
    resp = client.get(f"/sessions/{sid}/evidence")
    assert resp.status_code == 200
    ev = resp.json()

    assert ev["state"] == "DEPOT_OPENED"
    assert ev["audit_chain_ok"] is True
    assert ev["policy_version"] == "1.1.0"

    idx = ev["rule_index"]
    # Every satisfied check carries its legal basis; lena's happy path passes all.
    assert idx["R-ID-01"]["outcome"] == "ALLOW"
    assert "GwG" in idx["R-ID-01"]["law"]
    assert idx["R-TAX-02"]["outcome"] == "ALLOW"
    assert idx["R-CTR-01"]["outcome"] == "ALLOW"
    assert idx["R-WPHG-01"]["outcome"] == "ALLOW"
    # Each indexed rule points at the audit event (evidence) that evaluated it.
    assert all(r["evidence_hash"] is None or r["evidence_hash"].startswith("sha256:")
               for r in idx.values())

    # Steps carry the per-step checks with legal citations.
    identify_step = next(s for s in ev["steps"] if s["tool"] == "onboarding.identify")
    assert any(r["id"] == "R-ID-01" for r in identify_step["rules"])


def test_evidence_json_export_headers() -> None:
    client, sid = _client_and_sid()
    resp = client.get(f"/sessions/{sid}/evidence")
    assert resp.headers["content-type"].startswith("application/json")
    assert f"nachweis-{sid}.json" in resp.headers.get("content-disposition", "")


def test_evidence_unknown_session_404() -> None:
    client, _ = _client_and_sid()
    assert client.get("/sessions/ses_missing/evidence").status_code == 404
