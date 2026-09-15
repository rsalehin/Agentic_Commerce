"""IdentityVerifier adapter over the in-house SD-JWT VC verifier.

Resolves the issuer key from the wallet's issuer JWKS by the `kid` in the
credential header, then verifies the presentation. Real verification — never
returns True without checking the issuer signature, key binding, nonce, audience,
sd_hash and every disclosure.
"""

from __future__ import annotations

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from gateway.ports.identity_verifier import VerifiedIdentity
from gateway.signing import b64url_decode
from wallet import sdjwt


class WalletSdJwtVerifier:
    def __init__(self, issuer_jwks: dict[str, list[dict[str, str]]]) -> None:
        self._issuer_keys = {
            jwk["kid"]: Ed25519PublicKey.from_public_bytes(b64url_decode(jwk["x"]))
            for jwk in issuer_jwks["keys"]
        }

    def verify(self, presentation: str, *, nonce: str, aud: str, now: int) -> VerifiedIdentity:
        kid = sdjwt.issuer_kid_of(presentation)
        issuer_key = self._issuer_keys.get(kid) if kid else None
        if issuer_key is None:
            return VerifiedIdentity(
                False, error_code="SIGNATURE_INVALID", detail="unknown issuer kid"
            )
        try:
            pid = sdjwt.verify(
                presentation,
                issuer_public_key=issuer_key,
                expected_nonce=nonce,
                expected_aud=aud,
                now=now,
            )
        except sdjwt.SdJwtError as exc:
            return VerifiedIdentity(False, error_code=exc.code, detail=exc.detail)
        return VerifiedIdentity(
            True,
            claims=pid.claims,
            cnf_did=pid.cnf_did,
            assurance_level=pid.assurance_level,
            issuer=pid.issuer,
        )
