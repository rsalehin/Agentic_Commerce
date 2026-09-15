"""P1-10: headless happy path for lena from a recorded transcript (no network)."""

from __future__ import annotations

from pathlib import Path

from agent.replay import build_local_harness, load_run, replay

RUN_PATH = Path(__file__).resolve().parents[2] / "fixtures" / "recorded_runs" / "lena.json"


def test_recorded_lena_run_reaches_depot_opened_with_valid_chain() -> None:
    run = load_run(RUN_PATH)
    assert run.expected_final_state == "DEPOT_OPENED"

    gateway, wallet, discover = build_local_harness(run.persona)
    result = replay(run, gateway=gateway, wallet=wallet, discover=discover)

    assert result.state == run.expected_final_state
    assert result.session_id is not None

    # A verifying, hash-chained audit trail ending at DEPOT_OPENED.
    session = gateway.service.sessions[result.session_id].session
    assert session.verify_chain() is None
    assert session.state == "DEPOT_OPENED"
    assert session.events[-1].to_state == "DEPOT_OPENED"

    # A Depot number was returned.
    depot_env = next(e for e in result.envelopes if (e.get("data") or {}).get("depot"))
    assert len(depot_env["data"]["depot"]["depot_number"]) == 10
