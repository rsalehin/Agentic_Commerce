"""Compact JWS (EdDSA) helpers, built on PyJWT + cryptography.

Used for the mandate, the sender proof, and later the tax declaration, snapshot
signature and SD-JWT KB-JWT. The card uses a JWS-JSON-with-JCS-payload instead
(see gateway/signing.py); this module is the compact `header.payload.signature`
form with a base64url(JSON) payload.

Signature verification and claim checks are separated so the caller can map each
failure to the right code (SIGNATURE_INVALID vs MANDATE_EXPIRED vs ...).
"""

from __future__ import annotations

from typing import Any

import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


class JwsError(Exception):
    """Signature invalid, malformed token, or wrong algorithm."""


def sign_compact(payload: dict[str, Any], private_key: Ed25519PrivateKey, kid: str) -> str:
    return jwt.encode(payload, private_key, algorithm="EdDSA", headers={"kid": kid})


def unverified_header(token: str) -> dict[str, Any]:
    try:
        header: dict[str, Any] = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise JwsError(str(exc)) from exc
    return header


def unverified_payload(token: str) -> dict[str, Any]:
    """Decode claims WITHOUT verifying the signature (e.g. to read `iss`)."""
    try:
        payload: dict[str, Any] = jwt.decode(token, options={"verify_signature": False})
    except jwt.PyJWTError as exc:
        raise JwsError(str(exc)) from exc
    return payload


def verify_compact(token: str, public_key: Ed25519PublicKey) -> dict[str, Any]:
    """Verify the signature only; do NOT enforce exp/aud/iss (caller does).

    Raises JwsError on a bad signature or malformed token.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            public_key,
            algorithms=["EdDSA"],
            # Verify the signature only; the caller enforces exp/aud with an
            # injected `now`, so PyJWT must not consult the real clock (exp/iat/nbf).
            options={
                "verify_exp": False,
                "verify_iat": False,
                "verify_nbf": False,
                "verify_aud": False,
                "verify_iss": False,
            },
        )
    except jwt.PyJWTError as exc:
        raise JwsError(str(exc)) from exc
    return payload
