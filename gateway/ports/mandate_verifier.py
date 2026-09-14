"""MandateVerifier port: verify a mandate JWS into a schema-valid Mandate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from gateway.models.mandate import Mandate


@dataclass(frozen=True)
class MandateVerification:
    ok: bool
    mandate: Mandate | None = None
    # One of docs/05 §5 codes: MANDATE_INVALID | SIGNATURE_INVALID | MANDATE_EXPIRED
    error_code: str | None = None
    detail: str | None = None


class MandateVerifier(Protocol):
    def verify(
        self,
        mandate_jws: str,
        *,
        expected_aud: str,
        now: int,
        holder_public_key: Ed25519PublicKey | None = None,
        consume_jti: bool = False,
    ) -> MandateVerification:
        """Verify signature (against `holder_public_key`, or the `iss` did:key if
        None), audience, expiry and — when `consume_jti` — one-time `jti` use."""
        ...
