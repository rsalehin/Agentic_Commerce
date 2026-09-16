"""P3-07: the interactive run service (approvals + decline -> cancel)."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

from agent.replay.runner import build_service
from agent.runner_service import create_runner_app
from gateway.app import create_app


def _harness() -> tuple[TestClient, TestClient]:
    """A runner TestClient whose runs drive a shared in-memory gateway."""
    gateway_service = build_service()
    gateway_app = create_app(gateway_service)
    runner = TestClient(create_runner_app(lambda: TestClient(gateway_app)))
    gateway = TestClient(gateway_app)
    return runner, gateway


def _wait(
    runner: TestClient, run_id: str, pred: Callable[[dict[str, Any]], bool]
) -> dict[str, Any]:
    deadline = time.time() + 15
    while time.time() < deadline:
        snap = runner.get(f"/runs/{run_id}").json()
        if pred(snap):
            return snap
        time.sleep(0.05)
    raise AssertionError(f"timeout waiting; last snapshot: {runner.get(f'/runs/{run_id}').json()}")


def _waiting_for(purpose: str) -> Callable[[dict[str, Any]], bool]:
    def pred(s: dict[str, Any]) -> bool:
        return s["status"] == "waiting" and (s["pending_prompt"] or {}).get("purpose") == purpose

    return pred


def _approve(runner: TestClient, run_id: str, snap: dict[str, Any], approved: bool = True) -> Any:
    pid = snap["pending_prompt"]["prompt_id"]
    return runner.post(f"/runs/{run_id}/prompts/{pid}", json={"approved": approved})


def test_lena_script_run_reaches_depot_opened() -> None:
    runner, _ = _harness()
    run_id = runner.post("/runs", json={"persona": "lena", "mode": "script"}).json()["run_id"]

    for purpose in ("mandate", "tax", "contract"):
        snap = _wait(runner, run_id, _waiting_for(purpose))
        assert _approve(runner, run_id, snap).status_code == 200

    done = _wait(runner, run_id, lambda s: s["status"] == "finished")
    assert done["state"] == "DEPOT_OPENED"
    assert done["declined"] is False


def test_decline_at_tax_cancels_the_gateway_session() -> None:
    runner, gateway = _harness()
    run_id = runner.post("/runs", json={"persona": "lena", "mode": "script"}).json()["run_id"]

    snap = _wait(runner, run_id, _waiting_for("mandate"))
    _approve(runner, run_id, snap)
    snap = _wait(runner, run_id, _waiting_for("tax"))
    assert _approve(runner, run_id, snap, approved=False).status_code == 200

    done = _wait(runner, run_id, lambda s: s["status"] == "finished")
    assert done["declined"] is True
    assert done["state"] == "CANCELLED"
    sid = done["session_id"]
    assert sid is not None
    assert gateway.get(f"/sessions/{sid}").json()["state"] == "CANCELLED"


def test_decline_at_mandate_sends_nothing_to_the_gateway() -> None:
    runner, _ = _harness()
    run_id = runner.post("/runs", json={"persona": "lena", "mode": "script"}).json()["run_id"]

    snap = _wait(runner, run_id, _waiting_for("mandate"))
    assert _approve(runner, run_id, snap, approved=False).status_code == 200

    done = _wait(runner, run_id, lambda s: s["status"] == "finished")
    assert done["declined"] is True
    assert done["session_id"] is None
    assert done["state"] is None  # no gateway session ever existed


def test_marco_run_reaches_advised_handoff() -> None:
    runner, _ = _harness()
    run_id = runner.post("/runs", json={"persona": "marco", "mode": "script"}).json()["run_id"]

    for purpose in ("mandate", "tax"):
        snap = _wait(runner, run_id, _waiting_for(purpose))
        assert _approve(runner, run_id, snap).status_code == 200

    done = _wait(runner, run_id, lambda s: s["status"] == "finished")
    assert done["state"] == "ADVISED_HANDOFF"


def test_decision_on_non_pending_prompt_is_409() -> None:
    runner, _ = _harness()
    run_id = runner.post("/runs", json={"persona": "lena", "mode": "script"}).json()["run_id"]

    snap = _wait(runner, run_id, _waiting_for("mandate"))
    pid = snap["pending_prompt"]["prompt_id"]
    assert runner.post(f"/runs/{run_id}/prompts/{pid}", json={"approved": True}).status_code == 200
    # The same prompt is no longer pending.
    again = runner.post(f"/runs/{run_id}/prompts/{pid}", json={"approved": True})
    assert again.status_code == 409
    # An unknown prompt id -> 404.
    unknown = runner.post(f"/runs/{run_id}/prompts/prm_nope", json={"approved": True})
    assert unknown.status_code == 404


def test_second_run_refused_while_active_then_allowed_after_finish() -> None:
    runner, _ = _harness()
    run_id = runner.post("/runs", json={"persona": "lena", "mode": "script"}).json()["run_id"]
    _wait(runner, run_id, _waiting_for("mandate"))
    # A run is active (waiting) -> 409.
    assert runner.post("/runs", json={"persona": "marco", "mode": "script"}).status_code == 409
    # Finish it by declining the mandate.
    snap = runner.get(f"/runs/{run_id}").json()
    _approve(runner, run_id, snap, approved=False)
    _wait(runner, run_id, lambda s: s["status"] == "finished")
    # Now a new run is accepted (the demo starts Lena twice).
    assert runner.post("/runs", json={"persona": "lena", "mode": "script"}).status_code == 200


def test_live_mode_without_api_key_is_400(monkeypatch: Any) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    runner, _ = _harness()
    resp = runner.post("/runs", json={"persona": "lena", "mode": "live"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "NO_API_KEY"
