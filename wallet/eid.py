"""Mock eID / Online-Ausweis holder attestation (deprecation-swap counterpart).

Produces the presentation the `eid_stub` IdentityVerifier expects: a compact JWS
signed by the holder key, carrying the claims + nonce/aud + the holder key in
`cnf`. Stands in for AusweisApp/eID when `IDENTITY_VERIFIER=eid_stub`.
"""

from __future__ import annotations

import time
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from gateway.jws import sign_compact
from wallet.keys import public_jwk


def present_eid(
    claims: dict[str, Any],
    *,
    holder_key: Ed25519PrivateKey,
    holder_kid: str,
    nonce: str,
    aud: str,
    now: int | None = None,
    assurance_level: str = "high",
) -> str:
    payload = {
        "claims": claims,
        "nonce": nonce,
        "aud": aud,
        "assurance_level": assurance_level,
        "issuer": "mock-eid",
        "iat": int(time.time()) if now is None else now,
        "cnf": {"jwk": public_jwk(holder_key.public_key(), holder_kid)},
    }
    return sign_compact(payload, holder_key, holder_kid)
