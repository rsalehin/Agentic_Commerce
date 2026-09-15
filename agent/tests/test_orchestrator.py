"""P1-09 tests: the orchestrator drives the gateway to DEPOT_OPENED (scripted)."""

from __future__ import annotations

from typing import Any

from agent.discovery import verify_card_against_directory
from agent.gateway_client import InProcessGatewayClient
from agent.llm import ScriptedProvider
from agent.orchestrator import Orchestrator, WalletContext
from gateway.card import provider_fingerprint, signed_card
from gateway.tests.onboarding_helpers import (
    PRESENT_CLAIMS,
    PROVIDER,
    declaration_for,
    make_service,
    persona,
)
from wallet.keys import ensure_keys

REG = ensure_keys()


def _wallet(pid: str = "lena") -> WalletContext:
    holder = REG.holders[pid]
    instance = REG.services["agent-kundenagent-demo"]
    return WalletContext(
        holder_key=holder.private,
        holder_kid=f"holder-{pid}",
        holder_did=holder.did,
        instance_key=instance.private,
        instance_kid="agent-kundenagent-demo",
        provider_domain=PROVIDER,
        agent_id="agent:kundenagent-demo",
        agent_provider="Anthropic Claude (Demo)",
        card_fingerprint=provider_fingerprint(),
        persona=persona(pid),
    )


def _happy_calls() -> list[tuple[str, dict[str, Any]]]:
    p = persona("lena")
    decl = declaration_for("lena")
    return [
        ("discovery.verify", {"url": "http://localhost:8080"}),
        ("ask_human", {"purpose": "mandate", "question_de": "Mandat erteilen?"}),
        ("wallet.create_mandate", {"scope": p["mandate_scope"]}),
        ("onboarding.start", {}),
        ("wallet.present_pid", {"requested_claims": PRESENT_CLAIMS}),
        ("onboarding.identify", {"reference_account_iban": p["reference_account"]["iban"]}),
        ("ask_human", {"purpose": "tax", "question_de": "Steuererklärung bestätigen?"}),
        ("wallet.sign_tax", {"declaration": decl}),
        ("onboarding.tax_declaration", {"declaration": decl}),
        (
            "onboarding.appropriateness",
            {
                "profile": {
                    "experience": p["experience"],
                    "education": "Abitur",
                    "occupation": "Angestellte",
                    "requested_classes": ["fonds", "etf"],
                    "advice_requested": False,
                }
            },
        ),
        (
            "onboarding.get_documents",
            {
                "plan": {
                    "monthly_amount": {"value": 150, "currency": "EUR"},
                    "product_isin": "DE000MOCK0001",
                }
            },
        ),
        ("ask_human", {"purpose": "contract", "question_de": "Vertrag signieren?"}),
        ("wallet.sign_contract", {}),
        ("onboarding.sign_contract", {"idempotency_key": "k1"}),
        ("onboarding.status", {}),
    ]


def _orchestrator(approve: bool = True) -> tuple[Orchestrator, list[dict[str, Any]]]:
    service = make_service()
    seen: list[dict[str, Any]] = []

    def ask_human(question_de: str, payload: dict[str, Any] | None) -> dict[str, Any]:
        seen.append({"q": question_de})
        return {"approved": approve, "answer": "ja" if approve else "nein"}

    orch = Orchestrator(
        ScriptedProvider.from_calls(_happy_calls()),
        InProcessGatewayClient(service),
        _wallet("lena"),
        ask_human,
        discover=lambda _url: verify_card_against_directory(signed_card()),
    )
    return orch, seen


def test_orchestrator_reaches_depot_opened() -> None:
    orch, asks = _orchestrator()
    result = orch.run("Eröffne mir ein ETF-Sparplan-Depot, max. 200 Euro im Monat.")
    assert result.state == "DEPOT_OPENED"
    assert result.session_id is not None
    # Three human confirmations: mandate, tax, contract.
    assert len(asks) == 3
    depot_env = next(e for e in result.envelopes if e.get("data", {}).get("depot"))
    assert len(depot_env["data"]["depot"]["depot_number"]) == 10


def test_signing_blocked_without_human_approval() -> None:
    orch, _ = _orchestrator(approve=False)
    result = orch.run("Eröffne mir ein Depot.")
    # ask_human is declined, so wallet.create_mandate refuses and start never
    # gets a mandate -> onboarding.start fails, no Depot.
    assert result.state != "DEPOT_OPENED"
