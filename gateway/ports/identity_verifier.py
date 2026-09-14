"""IdentityVerifier port: verify a wallet PID presentation into KYC data.

Adapters: `wallet_sdjwt` (default) and `eid_stub` (P3-02); selected by the
`IDENTITY_VERIFIER` env var. `cnf_did` is returned so the gateway can enforce
R-ID-05 (`cnf_did == mandate.iss`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class VerifiedIdentity:
    ok: bool
    claims: dict[str, Any] | None = None
    cnf_did: str | None = None
    assurance_level: str | None = None
    issuer: str | None = None
    error_code: str | None = None  # PRESENTATION_INVALID | SIGNATURE_INVALID
    detail: str | None = None


class IdentityVerifier(Protocol):
    def verify(
        self, presentation: str, *, nonce: str, aud: str, now: int
    ) -> VerifiedIdentity: ...
