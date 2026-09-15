"""Load and replay a recorded run through the real gateway (no LLM call).

The recorded turns are the model's tool-call decisions; the crypto artifacts are
regenerated live by the wallet tools during replay. `build_local_harness`
assembles the in-process demo (gateway service wired to the mock wallet/core with
the current keys) and a network-free discovery function.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent.discovery import verify_card_against_directory
from agent.gateway_client import GatewayClient, InProcessGatewayClient
from agent.http_gateway_client import HttpGatewayClient
from agent.llm import ScriptedProvider
from agent.orchestrator import Orchestrator, RunResult, WalletContext
from core.db import make_engine
from core.depotbank import DepotbankCore
from core.fixtures import personas_file
from gateway.adapters.client_registry import ClientRegistry
from gateway.adapters.wallet_sdjwt import WalletSdJwtVerifier
from gateway.card import provider_fingerprint, signed_card
from gateway.service import GatewayService
from wallet.app import issuer_jwks
from wallet.keys import ensure_keys, public_jwk

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = REPO_ROOT / "fixtures" / "recorded_runs"
PROVIDER_DOMAIN = "https://fonds-ag.example"
AGENT_ID = "agent:kundenagent-demo"
INSTANCE_KID = "agent-kundenagent-demo"


@dataclass
class RecordedRun:
    persona: str
    intent_de: str
    expected_final_state: str
    turns: list[dict[str, Any]]
    ask_human_default: dict[str, Any]
    reviews: list[dict[str, Any]]  # recorded adviser/compliance decisions, in order


def load_run(path: str | Path) -> RecordedRun:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return RecordedRun(
        persona=data["persona"],
        intent_de=data["intent_de"],
        expected_final_state=data["expected_final_state"],
        turns=data["turns"],
        ask_human_default=data.get("ask_human_default", {"approved": True, "answer": "ja"}),
        reviews=data.get("reviews", []),
    )


def _persona(persona_id: str) -> dict[str, Any]:
    return next(p for p in personas_file()["personas"] if p["id"] == persona_id)


def build_service() -> GatewayService:
    """A gateway service wired to the mock wallet/core with the current keys."""
    registry = ensure_keys()
    instance = registry.services[INSTANCE_KID]
    clients = ClientRegistry(
        clients=[
            {
                "client_id": AGENT_ID,
                "status": "active",
                "instance_jwk": public_jwk(instance.public, INSTANCE_KID),
            }
        ]
    )
    return GatewayService(
        client_registry=clients,
        identity_verifier=WalletSdJwtVerifier(issuer_jwks()),
        core=DepotbankCore(make_engine()),
    )


def build_wallet(persona_id: str) -> WalletContext:
    registry = ensure_keys()
    holder = registry.holders[persona_id]
    instance = registry.services[INSTANCE_KID]
    return WalletContext(
        holder_key=holder.private,
        holder_kid=f"holder-{persona_id}",
        holder_did=holder.did,
        instance_key=instance.private,
        instance_kid=INSTANCE_KID,
        provider_domain=PROVIDER_DOMAIN,
        agent_id=AGENT_ID,
        agent_provider="Anthropic Claude (Demo)",
        card_fingerprint=provider_fingerprint(),
        persona=_persona(persona_id),
    )


def offline_discover() -> Callable[[str], Any]:
    """Verify the gateway's own signed card via the directory (no network)."""
    return lambda _url: verify_card_against_directory(signed_card())


def build_local_harness(
    persona_id: str,
) -> tuple[InProcessGatewayClient, WalletContext, Callable[[str], Any]]:
    """Assemble the in-process demo (service + wallet context + offline discovery)."""
    return InProcessGatewayClient(build_service()), build_wallet(persona_id), offline_discover()


def build_http_harness(
    persona_id: str, http: Any, *, provider_domain: str = PROVIDER_DOMAIN
) -> tuple[HttpGatewayClient, WalletContext, Callable[[str], Any]]:
    """Assemble a harness that drives a *running* gateway over HTTP (`http` is an
    httpx.Client / FastAPI TestClient bound to that server)."""
    return HttpGatewayClient(http, provider_domain), build_wallet(persona_id), offline_discover()


def replay(
    run: RecordedRun,
    *,
    gateway: GatewayClient,
    wallet: WalletContext,
    discover: Callable[[str], Any],
    now: Callable[[], int] | None = None,
) -> RunResult:
    provider = ScriptedProvider.from_calls([(t["tool"], t["input"]) for t in run.turns])

    def ask_human(question_de: str, payload: dict[str, Any] | None) -> dict[str, Any]:
        return dict(run.ask_human_default)

    # Apply the recorded staff decisions in order, one per review escalation.
    decisions = iter(run.reviews)

    def on_review(session_id: str) -> None:
        decision = next(decisions, None)
        if decision is None:
            return
        open_reviews = gateway.list_open_reviews(session_id)
        if open_reviews:
            actor = decision.get("actor", "adviser")
            gateway.decide(open_reviews[-1]["id"], decision["decision"], actor)

    orchestrator = Orchestrator(
        provider, gateway, wallet, ask_human, discover=discover, now=now, on_review=on_review
    )
    return orchestrator.run(run.intent_de)
