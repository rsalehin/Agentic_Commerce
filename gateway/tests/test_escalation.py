"""P2-01 tests: customer/review escalation queues and staff decisions."""

from __future__ import annotations

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
    assert result["state"] == "SCREENED"  # resumes at blocked_from
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
    # The agent only sees IN_REVIEW (GwG §47), never the real match.
    assert ident["reason_codes"] == ["IN_REVIEW"]
    assert ident["state"] == "REVIEW_REQUIRED"

    escs = svc.list_escalations(queue="review")
    assert len(escs) == 1
    esc = escs[0]
    assert esc["actor_role"] == "compliance"
    assert esc["confidential"] is True
    assert esc["reasons"] == ["AML_SANCTIONS_HIT"]  # real code, compliance-only

    result = svc.decide_escalation(esc["id"], "reject", actor="compliance", note="confirmed")
    assert result["ok"] is True
    assert result["state"] == "REJECTED"


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
