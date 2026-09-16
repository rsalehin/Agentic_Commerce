"""P2-01 tests: customer/review escalation queues and staff decisions."""

from __future__ import annotations

import json
from typing import Any

from gateway.service import GatewayService
from gateway.tests.onboarding_helpers import (
    declaration_for,
    holder_sign,
    make_service,
    persona,
    presentation,
    sender,
    start_payload,
)


def _identified(svc: GatewayService, pid: str) -> str:
    env = svc.handle("onboarding.start", start_payload(pid, svc))
    sid = env["data"]["session_id"]
    nonce = env["data"]["requested_credentials"]["nonce"]
    svc.handle(
        "onboarding.identify",
        {
            "session_id": sid,
            "presentation": presentation(pid, nonce),
            "reference_account_iban": persona(pid)["reference_account"]["iban"],
            "sender_proof": sender(svc, "onboarding.identify", sid),
        },
    )
    return str(sid)


def _tax(svc: GatewayService, pid: str, sid: str, declaration: dict[str, Any]) -> dict[str, Any]:
    return svc.handle(
        "onboarding.tax_declaration",
        {
            "session_id": sid,
            "declaration": declaration,
            "holder_signature": holder_sign(pid, sid, {"declaration": declaration}),
            "sender_proof": sender(svc, "onboarding.tax_declaration", sid),
        },
    )


def test_foreign_residency_creates_adviser_review_escalation_and_resume() -> None:
    svc = make_service()
    sid = _identified(svc, "lena")
    decl = declaration_for("lena")
    decl["residencies"] = [{"country": "DE", "tin": "12345678901"}, {"country": "IT", "tin": "X"}]
    env = _tax(svc, "lena", sid, decl)
    assert env["human_required"] is True and env["state"] == "REVIEW_REQUIRED"

    escs = svc.list_escalations(queue="review")
    assert len(escs) == 1
    esc = escs[0]
    assert esc["actor_role"] == "adviser"
    assert esc["confidential"] is False
    assert esc["reasons"] == ["TAX_FOREIGN_RESIDENCY"]
    assert esc["blocked_from"] == "SCREENED"

    result = svc.decide_escalation(esc["id"], "approve", actor="adviser", note="ok")
    assert result["ok"] is True
    assert result["state"] == "TAX_CONFIRMED"  # review approval completes the step
    assert svc.sessions[sid].session.audit_chain_ok() is True


def test_sanctions_creates_confidential_compliance_escalation_and_reject() -> None:
    svc = make_service()
    env = svc.handle("onboarding.start", start_payload("sanction_test", svc))
    sid = env["data"]["session_id"]
    nonce = env["data"]["requested_credentials"]["nonce"]
    ident = svc.handle(
        "onboarding.identify",
        {
            "session_id": sid,
            "presentation": presentation("sanction_test", nonce),
            "reference_account_iban": persona("sanction_test")["reference_account"]["iban"],
            "sender_proof": sender(svc, "onboarding.identify", sid),
        },
    )
    # (a) The agent only sees IN_REVIEW (GwG §47), never the real match — in the
    # identify envelope or in onboarding.status.
    assert ident["reason_codes"] == ["IN_REVIEW"]
    assert ident["state"] == "REVIEW_REQUIRED"
    assert "AML_SANCTIONS_HIT" not in json.dumps(ident)
    status = svc.handle("onboarding.status", {"session_id": sid})
    assert status["data"]["reason_codes"] == ["IN_REVIEW"]
    assert "AML_SANCTIONS_HIT" not in json.dumps(status)

    escs = svc.list_escalations(queue="review")
    assert len(escs) == 1
    esc = escs[0]
    assert esc["actor_role"] == "compliance"
    assert esc["confidential"] is True
    assert esc["reasons"] == ["AML_SANCTIONS_HIT"]  # real code, compliance-only

    # (b) The audit log DOES carry the real code (staff view / Nachweis).
    events = svc.sessions[sid].session.events
    assert any("AML_SANCTIONS_HIT" in e.reason_codes for e in events)

    # (c) An adviser may not decide a confidential §47 case: refused with
    # FORBIDDEN_ACTOR, state unchanged, and audited like a guard rejection.
    refused = svc.decide_escalation(esc["id"], "reject", actor="adviser")
    assert refused["ok"] is False
    assert refused["error"]["code"] == "FORBIDDEN_ACTOR"
    assert svc.sessions[sid].session.state == "REVIEW_REQUIRED"
    assert any(
        e.from_state == e.to_state == "REVIEW_REQUIRED"
        and e.actor == "adviser"
        and e.reason_codes == ["FORBIDDEN_ACTOR"]
        for e in svc.sessions[sid].session.events
    )

    # Compliance rejects -> REVIEW_REJECTED -> REJECTED, audited as actor compliance.
    result = svc.decide_escalation(esc["id"], "reject", actor="compliance", note="confirmed")
    assert result["ok"] is True
    assert result["state"] == "REJECTED"
    assert any(
        e.actor == "compliance" and e.to_state == "REJECTED"
        for e in svc.sessions[sid].session.events
    )


def test_confidential_decision_rest_returns_403_for_adviser() -> None:
    from fastapi.testclient import TestClient

    from gateway.app import create_app

    svc = make_service()
    env = svc.handle("onboarding.start", start_payload("sanction_test", svc))
    sid = env["data"]["session_id"]
    nonce = env["data"]["requested_credentials"]["nonce"]
    svc.handle(
        "onboarding.identify",
        {
            "session_id": sid,
            "presentation": presentation("sanction_test", nonce),
            "reference_account_iban": persona("sanction_test")["reference_account"]["iban"],
            "sender_proof": sender(svc, "onboarding.identify", sid),
        },
    )
    esc = svc.list_escalations(queue="review")[0]
    client = TestClient(create_app(svc))

    resp = client.post(
        f"/escalations/{esc['id']}/decision", json={"decision": "reject", "actor": "adviser"}
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN_ACTOR"

    ok = client.post(
        f"/escalations/{esc['id']}/decision", json={"decision": "reject", "actor": "compliance"}
    )
    assert ok.status_code == 200
    assert ok.json()["state"] == "REJECTED"


def test_customer_queue_and_decision_guards() -> None:
    svc = make_service()
    sid = _identified(svc, "lena")
    # Unsigned tax -> CUSTOMER_REQUIRED -> customer-queue escalation.
    env = _tax_unsigned(svc, sid)
    assert env["state"] == "CUSTOMER_REQUIRED"
    escs = svc.list_escalations(queue="customer")
    assert len(escs) == 1 and escs[0]["actor_role"] == "customer"
    # request_appointment/reject are review-only.
    bad = svc.decide_escalation(escs[0]["id"], "request_appointment", actor="adviser")
    assert bad["ok"] is False


def _tax_unsigned(svc: GatewayService, sid: str) -> dict[str, Any]:
    return svc.handle(
        "onboarding.tax_declaration",
        {
            "session_id": sid,
            "declaration": declaration_for("lena"),
            "holder_signature": None,
            "sender_proof": sender(svc, "onboarding.tax_declaration", sid),
        },
    )
