"""JWS MandateVerifier adapter (EdDSA).

Verifies the compact mandate JWS: signature against the holder key (the `iss`
`did:key` before identification, or a supplied key after), audience, expiry
(guard → MANDATE_EXPIRED) and one-time `jti`. Schema validity comes from the
`Mandate` pydantic model. `check_agent_binding` implements the R-MND-04 checks.
"""

from __future__ import annotations

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import ValidationError

from gateway.adapters.jti_store import JtiStore
from gateway.jws import JwsError, unverified_payload, verify_compact
from gateway.models.mandate import Mandate
from gateway.ports.mandate_verifier import MandateVerification
from wallet.keys import raw_public_from_did_key


class JwsMandateVerifier:
    def __init__(self, jti_store: JtiStore | None = None) -> None:
        self._jti_store = jti_store or JtiStore()

    def verify(
        self,
        mandate_jws: str,
        *,
        expected_aud: str,
        now: int,
        holder_public_key: Ed25519PublicKey | None = None,
        consume_jti: bool = False,
    ) -> MandateVerification:
        # 1. Determine the verification key: supplied, else the iss did:key.
        try:
            claims = unverified_payload(mandate_jws)
        except JwsError as exc:
            return MandateVerification(False, error_code="MANDATE_INVALID", detail=str(exc))

        key = holder_public_key
        if key is None:
            iss = claims.get("iss")
            if not isinstance(iss, str) or not iss.startswith("did:key:z"):
                return MandateVerification(
                    False, error_code="MANDATE_INVALID", detail="missing/invalid iss did:key"
                )
            try:
                key = Ed25519PublicKey.from_public_bytes(raw_public_from_did_key(iss))
            except ValueError as exc:
                return MandateVerification(False, error_code="MANDATE_INVALID", detail=str(exc))

        # 2. Verify the signature (only).
        try:
            payload = verify_compact(mandate_jws, key)
        except JwsError as exc:
            return MandateVerification(False, error_code="SIGNATURE_INVALID", detail=str(exc))

        # 3. Schema.
        try:
            mandate = Mandate.model_validate(payload)
        except ValidationError as exc:
            return MandateVerification(False, error_code="MANDATE_INVALID", detail=str(exc))

        # 4. Audience.
        if mandate.aud != expected_aud:
            return MandateVerification(
                False, error_code="MANDATE_INVALID", detail="audience mismatch", mandate=mandate
            )

        # 5. Expiry (guard).
        if mandate.exp < now:
            return MandateVerification(
                False, error_code="MANDATE_EXPIRED", detail="mandate expired", mandate=mandate
            )

        # 6. One-time jti (consume-once for onboarding.start).
        if consume_jti and not self._jti_store.consume(mandate.jti):
            return MandateVerification(
                False, error_code="MANDATE_INVALID", detail="jti already consumed", mandate=mandate
            )

        return MandateVerification(True, mandate=mandate)


def check_agent_binding(
    mandate: Mandate,
    *,
    call_card_fingerprint: str,
    provider_card_fingerprint: str,
    call_agent_id: str,
) -> str | None:
    """R-MND-04: bind the call and the human-signed mandate to the provider card
    and the calling agent. Returns `AGENT_UNVERIFIED` on failure, else None."""
    if not call_agent_id:
        return "AGENT_UNVERIFIED"
    if call_card_fingerprint != provider_card_fingerprint:
        return "AGENT_UNVERIFIED"
    if mandate.agent.card_fingerprint != provider_card_fingerprint:
        return "AGENT_UNVERIFIED"
    if mandate.agent.id != call_agent_id:
        return "AGENT_UNVERIFIED"
    return None
