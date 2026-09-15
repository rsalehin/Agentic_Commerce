"""Shared helpers to mint signed onboarding artifacts for P1-08 tests."""

from __future__ import annotations

import time
from typing import Any

from agent.sender import build_sender_proof
from core.db import make_engine
from core.depotbank import DepotbankCore
from core.fixtures import personas_file
from gateway.adapters.client_registry import ClientRegistry
from gateway.adapters.wallet_sdjwt import WalletSdJwtVerifier
from gateway.card import provider_fingerprint
from gateway.jws import sign_compact
from gateway.service import GatewayService
from wallet.app import issuer_jwks
from wallet.holder import present_pid
from wallet.issuer import issue_pid_for_persona
from wallet.keys import ensure_keys, public_jwk
from wallet.mandate import build_mandate, sign_mandate

PROVIDER = "https://fonds-ag.example"
AGENT_ID = "agent:kundenagent-demo"
INSTANCE_KID = "agent-kundenagent-demo"
REG = ensure_keys()

PRESENT_CLAIMS = [
    "given_name",
    "family_name",
    "birth_date",
    "nationalities",
    "address",
    "birth_place_country",
    "assurance_level",
]


def persona(pid: str) -> dict[str, Any]:
    return next(p for p in personas_file()["personas"] if p["id"] == pid)


def make_service() -> GatewayService:
    registry = ClientRegistry(
        clients=[
            {
                "client_id": AGENT_ID,
                "status": "active",
                "instance_jwk": public_jwk(REG.services[INSTANCE_KID].public, INSTANCE_KID),
            }
        ]
    )
    return GatewayService(
        client_registry=registry,
        identity_verifier=WalletSdJwtVerifier(issuer_jwks()),
        core=DepotbankCore(make_engine()),
    )


def mandate_jws(pid: str, scope: dict[str, Any] | None = None) -> str:
    holder = REG.holders[pid]
    payload = build_mandate(
        holder_did=holder.did,
        provider_domain=PROVIDER,
        card_fingerprint=provider_fingerprint(),
        agent_id=AGENT_ID,
        agent_provider="Anthropic Claude (Demo)",
        mandate_scope=scope or persona(pid)["mandate_scope"],
        revocation_url="http://localhost:8081/revocations",
    )
    return sign_mandate(payload, holder.private, f"holder-{pid}")


def sender(service: GatewayService, tool: str, sid: str) -> str:
    return build_sender_proof(
        REG.services[INSTANCE_KID].private,
        INSTANCE_KID,
        htm="POST",
        htu=service.htu(tool, sid),
        session_id=sid,
        now=int(time.time()),
    )


def presentation(pid: str, nonce: str) -> str:
    vc = issue_pid_for_persona(persona(pid), REG)
    return present_pid(
        vc,
        requested_claims=PRESENT_CLAIMS,
        holder_key=REG.holders[pid].private,
        holder_kid=f"holder-{pid}",
        nonce=nonce,
        aud=PROVIDER,
        now=int(time.time()),
    )


def declaration_for(pid: str) -> dict[str, Any]:
    p = persona(pid)
    return {
        "tax_id": p["pid"]["tax_id"],
        "residencies": p["tax"]["residencies"],
        "us_person": p["tax"]["us_person"],
        "church_tax_query_consent": p["tax"]["church_tax_query_consent"],
        "freistellungsauftrag_eur": p["tax"]["freistellungsauftrag_eur"],
    }


def holder_sign(pid: str, sid: str, extra: dict[str, Any]) -> str:
    payload = {"session_id": sid, "aud": PROVIDER, **extra}
    return sign_compact(payload, REG.holders[pid].private, f"holder-{pid}")


def start_payload(
    pid: str, service: GatewayService, scope: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {
        "mandate": mandate_jws(pid, scope),
        "card_fingerprint": provider_fingerprint(),
        "agent_id": AGENT_ID,
        "sender_proof": sender(service, "onboarding.start", ""),
    }


def run_to_informed(service: GatewayService, pid: str = "lena") -> tuple[str, str]:
    """Drive the flow to INFORMED; return (session_id, snapshot_digest)."""
    env = service.handle("onboarding.start", start_payload(pid, service))
    sid = env["data"]["session_id"]
    nonce = env["data"]["requested_credentials"]["nonce"]
    service.handle(
        "onboarding.identify",
        {
            "session_id": sid,
            "presentation": presentation(pid, nonce),
            "reference_account_iban": persona(pid)["reference_account"]["iban"],
            "sender_proof": sender(service, "onboarding.identify", sid),
        },
    )
    decl = declaration_for(pid)
    service.handle(
        "onboarding.tax_declaration",
        {
            "session_id": sid,
            "declaration": decl,
            "holder_signature": holder_sign(pid, sid, {"declaration": decl}),
            "sender_proof": sender(service, "onboarding.tax_declaration", sid),
        },
    )
    service.handle(
        "onboarding.appropriateness",
        {
            "session_id": sid,
            "profile": {
                "experience": persona(pid)["experience"],
                "education": "Abitur",
                "occupation": "Angestellte",
                "requested_classes": ["fonds", "etf"],
                "advice_requested": False,
            },
            "sender_proof": sender(service, "onboarding.appropriateness", sid),
        },
    )
    env = service.handle(
        "onboarding.get_documents",
        {
            "session_id": sid,
            "plan": {
                "monthly_amount": {"value": 150, "currency": "EUR"},
                "product_isin": "DE000MOCK0001",
            },
            "sender_proof": sender(service, "onboarding.get_documents", sid),
        },
    )
    return sid, env["data"]["snapshot_digest"]
