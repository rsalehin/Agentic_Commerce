"""P3-07: customer-initiated cancellation (onboarding.cancel)."""

from __future__ import annotations

from gateway.tests.onboarding_helpers import (
    holder_sign,
    make_service,
    run_to_informed,
    sender,
    start_payload,
)


def test_cancel_from_mandate_valid_reaches_cancelled() -> None:
    svc = make_service()
    env = svc.handle("onboarding.start", start_payload("lena", svc))
    sid = env["data"]["session_id"]
    assert env["state"] == "MANDATE_VALID"

    res = svc.handle(
        "onboarding.cancel",
        {"session_id": sid, "sender_proof": sender(svc, "onboarding.cancel", sid)},
    )
    assert res["ok"] is True
    assert res["state"] == "CANCELLED"

    sess = svc.sessions[sid].session
    assert sess.state == "CANCELLED"
    assert any(e.to_state == "CANCELLED" and e.actor == "human" for e in sess.events)
    assert sess.audit_chain_ok() is True


def test_cancel_after_confirmed_is_wrong_state() -> None:
    svc = make_service()
    sid, digest = run_to_informed(svc, "lena")
    conf = svc.handle(
        "onboarding.sign_contract",
        {
            "session_id": sid,
            "snapshot_digest": digest,
            "holder_signature": holder_sign("lena", sid, {"snapshot_digest": digest}),
            "idempotency_key": "lena-cancel-test",
            "sender_proof": sender(svc, "onboarding.sign_contract", sid),
        },
    )
    assert conf["state"] == "DEPOT_OPENED"  # past the point of no return

    res = svc.handle(
        "onboarding.cancel",
        {"session_id": sid, "sender_proof": sender(svc, "onboarding.cancel", sid)},
    )
    assert res["ok"] is False
    assert res["error"]["code"] == "WRONG_STATE"
    assert svc.sessions[sid].session.state == "DEPOT_OPENED"  # unchanged
