"""Sender-binding verification (x-sender-proof), R-MND-05 / R-MND-06.

A DPoP-shaped compact JWS signed by the agent instance key over
`{htm, htu, session_id, iat, jti}`. Guards:
- R-MND-05 CLIENT_UNREGISTERED: client registered and active.
- R-MND-06 SENDER_BINDING_INVALID: signature valid against the client's
  instance key; `jti` unused; `iat` within 60 s; htm/htu/session_id match the
  actual request; and `mandate.agent.id == client_id`.
"""

from __future__ import annotations

from dataclasses import dataclass

from gateway.adapters.client_registry import ClientRegistry
from gateway.adapters.jti_store import JtiStore
from gateway.jws import JwsError, verify_compact

IAT_SKEW_SECONDS = 60


@dataclass(frozen=True)
class SenderCheck:
    ok: bool
    error_code: str | None = None  # CLIENT_UNREGISTERED | SENDER_BINDING_INVALID
    detail: str | None = None


def verify_sender_proof(
    proof_jws: str,
    *,
    client_id: str,
    mandate_agent_id: str,
    htm: str,
    htu: str,
    session_id: str,
    now: int,
    registry: ClientRegistry,
    jti_store: JtiStore,
) -> SenderCheck:
    # R-MND-05: registered & active.
    if not registry.is_active(client_id):
        return SenderCheck(False, "CLIENT_UNREGISTERED", "client not registered or blocked")
    key = registry.instance_key(client_id)
    if key is None:
        return SenderCheck(False, "CLIENT_UNREGISTERED", "no instance key registered")

    # R-MND-06: mandate must name this client.
    if mandate_agent_id != client_id:
        return SenderCheck(False, "SENDER_BINDING_INVALID", "mandate.agent.id != client_id")

    # Signature.
    try:
        proof = verify_compact(proof_jws, key)
    except JwsError as exc:
        return SenderCheck(False, "SENDER_BINDING_INVALID", f"bad signature: {exc}")

    # Bound to this exact request.
    if proof.get("htm") != htm or proof.get("htu") != htu or proof.get("session_id") != session_id:
        return SenderCheck(False, "SENDER_BINDING_INVALID", "proof does not match request")

    # Freshness.
    iat = proof.get("iat")
    if not isinstance(iat, int) or abs(now - iat) > IAT_SKEW_SECONDS:
        return SenderCheck(False, "SENDER_BINDING_INVALID", "iat missing or stale")

    # Replay.
    jti = proof.get("jti")
    if not isinstance(jti, str) or not jti_store.consume(jti):
        return SenderCheck(False, "SENDER_BINDING_INVALID", "jti missing or replayed")

    return SenderCheck(True)
