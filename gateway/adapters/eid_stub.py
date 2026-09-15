"""IdentityVerifier adapter for a mock eID / Online-Ausweis flow (ADR-03/ADR-10).

The deprecation demo: set `IDENTITY_VERIFIER=eid_stub` to swap the wallet SD-JWT
adapter for this one — same port, no gateway code change. An eID presentation is
a compact JWS signed by the holder key over `{claims, nonce, aud,
assurance_level, cnf}`; verification is real (the signature is checked against the
holder key carried in `cnf`), never a returned True. `cnf_did` still binds to the
mandate signer via R-ID-05.
"""

from __future__ import annotations

from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from gateway.jws import JwsError, unverified_payload, verify_compact
from gateway.ports.identity_verifier import VerifiedIdentity
from gateway.signing import b64url_decode
from wallet.keys import did_key_from_public


class EidStubVerifier:
    def verify(self, presentation: str, *, nonce: str, aud: str, now: int) -> VerifiedIdentity:
        try:
            unverified = unverified_payload(presentation)
        except JwsError as exc:
            return VerifiedIdentity(False, error_code="PRESENTATION_INVALID", detail=str(exc))

        cnf_jwk = (unverified.get("cnf") or {}).get("jwk")
        if not isinstance(cnf_jwk, dict) or "x" not in cnf_jwk:
            return VerifiedIdentity(False, error_code="PRESENTATION_INVALID", detail="missing cnf")
        key = Ed25519PublicKey.from_public_bytes(b64url_decode(cnf_jwk["x"]))

        try:
            payload = verify_compact(presentation, key)  # real: sig must match the eID holder key
        except JwsError as exc:
            return VerifiedIdentity(False, error_code="SIGNATURE_INVALID", detail=str(exc))

        if payload.get("nonce") != nonce or payload.get("aud") != aud:
            return VerifiedIdentity(False, error_code="PRESENTATION_INVALID", detail="nonce/aud")

        claims: dict[str, Any] = payload.get("claims") or {}
        return VerifiedIdentity(
            True,
            claims=claims,
            cnf_did=did_key_from_public(key),
            assurance_level=payload.get("assurance_level"),
            issuer=str(payload.get("issuer", "mock-eid")),
        )
