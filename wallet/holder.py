"""Holder-side selective presentation of a PID (agent-local `wallet.present_pid`).

Discloses only the requested claims and binds the presentation to the gateway's
nonce + audience via a KB-JWT signed by the holder key.
"""

from __future__ import annotations

import time

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from wallet import sdjwt


def present_pid(
    sd_jwt_vc: str,
    *,
    requested_claims: list[str],
    holder_key: Ed25519PrivateKey,
    holder_kid: str,
    nonce: str,
    aud: str,
    now: int | None = None,
) -> str:
    return sdjwt.present(
        sd_jwt_vc,
        disclose=requested_claims,
        holder_key=holder_key,
        holder_kid=holder_kid,
        nonce=nonce,
        aud=aud,
        now=int(time.time()) if now is None else now,
    )
