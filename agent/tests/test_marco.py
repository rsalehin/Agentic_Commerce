"""P2-04: marco end-to-end — two escalations, adviser decides, agent continues."""

from __future__ import annotations

from typing import Any

from agent.discovery import verify_card_against_directory
from agent.gateway_client import InProcessGatewayClient
from agent.llm import ScriptedProvider
from agent.orchestrator import Orchestrator, WalletContext
from agent.replay import build_service, build_wallet
from gateway.card import signed_card
from gateway.service import GatewayService
from gateway.tests.onboarding_helpers import PRESENT_CLAIMS, declaration_for, persona


def _marco_calls() -> list[tuple[str, dict[str, Any]]]:
    p = persona("marco")
    decl = declaration_for("marco")  # DE + IT residencies -> TAX_FOREIGN_RESIDENCY
    return [
        ("discovery.verify", {"url": "http://localhost:8080"}),
        ("ask_human", {"purpose": "mandate", "question_de": "Mandat erteilen?"}),
        ("wallet.create_mandate", {"scope": p["mandate_scope"]}),
        ("onboarding.start", {}),
        ("wallet.present_pid", {"requested_claims": PRESENT_CLAIMS}),
        ("onboarding.identify", {"reference_account_iban": p["reference_account"]["iban"]}),
        ("ask_human", {"purpose": "tax", "question_de": "Steuer bestätigen?"}),
        ("wallet.sign_tax", {"declaration": decl}),
        ("onboarding.tax_declaration", {"declaration": decl}),  # -> REVIEW (foreign residency)
        (
            "onboarding.appropriateness",
            {"profile": {
                "experience": p["experience"], "education": "Abitur", "occupation": "Ingenieur",
                "requested_classes": ["fonds", "etf", "zertifikate"], "advice_requested": False,
            }},
        ),  # -> REVIEW (complex product) -> request_appointment -> ADVISED_HANDOFF
    ]


def _frau_weber(service: GatewayService, sid: str) -> None:
    """Adviser decisions: approve a foreign-residency review; send a complex
    product to an appointment."""
    open_review = [
        e for e in service.list_escalations(queue="review")
        if e["session_id"] == sid and e["status"] == "open"
    ]
    esc = open_review[-1]
    if any(r in ("COMPLEX_PRODUCT", "ADVICE_REQUESTED") for r in esc["reasons"]):
        service.decide_escalation(esc["id"], "request_appointment", actor="adviser")
    else:
        service.decide_escalation(esc["id"], "approve", actor="adviser")


def test_marco_ends_in_advised_handoff_via_two_reviews() -> None:
    service = build_service()
    gateway = InProcessGatewayClient(service)
    wallet: WalletContext = build_wallet("marco")

    orch = Orchestrator(
        ScriptedProvider.from_calls(_marco_calls()),
        gateway,
        wallet,
        ask_human=lambda q, p: {"approved": True, "answer": "ja"},
        discover=lambda _u: verify_card_against_directory(signed_card()),
        on_review=lambda sid: _frau_weber(service, sid),
    )
    result = orch.run(persona("marco")["intent_de"])

    assert result.state == "ADVISED_HANDOFF"
    sess = service.sessions[result.session_id].session
    assert sess.audit_chain_ok() is True

    # Two review escalations were opened and decided (approve, then appointment).
    reviews = [e for e in service.list_escalations(queue="review")]
    assert len(reviews) == 2
    assert {e["status"] for e in reviews} == {"approved", "appointment"}
    reasons = {code for e in reviews for code in e["reasons"]}
    assert "TAX_FOREIGN_RESIDENCY" in reasons
    assert "COMPLEX_PRODUCT" in reasons
