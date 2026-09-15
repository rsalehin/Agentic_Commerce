"""P2-02 tests: resume at the blocked step + structured next-step to the agent."""

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


def _tax(svc: GatewayService, sid: str, decl: dict[str, Any]) -> dict[str, Any]:
    return svc.handle(
        "onboarding.tax_declaration",
        {
            "session_id": sid,
            "declaration": decl,
            "holder_signature": holder_sign("lena", sid, {"declaration": decl}),
            "sender_proof": sender(svc, "onboarding.tax_declaration", sid),
        },
    )


def test_approve_resumes_and_agent_reruns_blocked_step() -> None:
    svc = make_service()
    sid = _identified(svc, "lena")

    # Block at tax with a foreign residency -> REVIEW_REQUIRED.
    foreign = declaration_for("lena")
    foreign["residencies"] = [{"country": "DE", "tin": "1"}, {"country": "IT", "tin": "2"}]
    _tax(svc, sid, foreign)

    esc = svc.list_escalations(queue="review")[0]
    assert esc["blocked_tool"] == "onboarding.tax_declaration"

    # While blocked, status tells the agent to wait (no next_tool) and shows the escalation.
    blocked_status = svc.handle("onboarding.status", {"session_id": sid})["data"]
    assert blocked_status["state"] == "REVIEW_REQUIRED"
    assert blocked_status["next_tool"] is None
    assert blocked_status["escalation"]["id"] == esc["id"]

    # Adviser approves -> resumes at SCREENED, structured next-step points at the blocked tool.
    result = svc.decide_escalation(esc["id"], "approve", actor="adviser")
    assert result["state"] == "SCREENED"
    assert result["next_tool"] == "onboarding.tax_declaration"
    assert "wiederholen" in result["message_de"].lower()

    # The agent re-runs the step (now DE-only) and proceeds.
    env = _tax(svc, sid, declaration_for("lena"))
    assert env["ok"] is True and env["state"] == "TAX_CONFIRMED"
    assert svc.sessions[sid].session.audit_chain_ok() is True


def test_request_appointment_returns_handoff_next_step() -> None:
    svc = make_service()
    sid = _identified(svc, "lena")
    foreign = declaration_for("lena")
    foreign["residencies"] = [{"country": "IT", "tin": "2"}]
    _tax(svc, sid, foreign)
    esc = svc.list_escalations(queue="review")[0]

    result = svc.decide_escalation(esc["id"], "request_appointment", actor="adviser")
    assert result["state"] == "ADVISED_HANDOFF"
    assert result["next_tool"] is None
    assert "Termin" in result["message_de"]


def test_customer_required_status_points_at_blocked_tool() -> None:
    svc = make_service()
    sid = _identified(svc, "lena")
    # Unsigned tax -> CUSTOMER_REQUIRED; the agent should re-run tax after ask_human.
    svc.handle(
        "onboarding.tax_declaration",
        {
            "session_id": sid,
            "declaration": declaration_for("lena"),
            "holder_signature": None,
            "sender_proof": sender(svc, "onboarding.tax_declaration", sid),
        },
    )
    status = svc.handle("onboarding.status", {"session_id": sid})["data"]
    assert status["state"] == "CUSTOMER_REQUIRED"
    assert status["next_tool"] == "onboarding.tax_declaration"
