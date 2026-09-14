"""Build the x-sender-proof (agent instance key), docs/05 §2.2.

DPoP-shaped compact JWS over `{htm, htu, session_id, iat, jti}`, signed by the
agent instance key. The gateway verifies it via gateway/adapters/sender_proof.py.
"""

from __future__ import annotations

import time
import uuid

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from gateway.jws import sign_compact


def build_sender_proof(
    instance_key: Ed25519PrivateKey,
    kid: str,
    *,
    htm: str,
    htu: str,
    session_id: str,
    now: int | None = None,
    jti: str | None = None,
) -> str:
    payload = {
        "htm": htm,
        "htu": htu,
        "session_id": session_id,
        "iat": int(time.time()) if now is None else now,
        "jti": jti or f"prf_{uuid.uuid4().hex}",
    }
    return sign_compact(payload, instance_key, kid)
