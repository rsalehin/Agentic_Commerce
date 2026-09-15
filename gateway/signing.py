"""Ed25519 JWS helpers for the Agent Card (JWS with a JCS-canonical payload).

The card signature is a JWS object `{protected, signature}` over
`b64url(protected) + "." + b64url(JCS(card without "signatures"))`. Verification
re-parses the card, drops `signatures`, re-canonicalizes, and checks the
signature against a public key — so the wire serialization of the served card
does not matter, only its JSON structure.
"""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from gateway.canonical import jcs_canonicalize


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def _without_signatures(card: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in card.items() if k != "signatures"}


def card_fingerprint(card: dict[str, Any]) -> str:
    """`sha256:<hex>` over the JCS-canonical card without its `signatures`."""
    digest = hashlib.sha256(jcs_canonicalize(_without_signatures(card))).hexdigest()
    return f"sha256:{digest}"


def sign_card(
    card: dict[str, Any],
    private_key: Ed25519PrivateKey,
    kid: str,
    jku: str,
) -> dict[str, Any]:
    """Return ``card`` with a single JWS signature object attached.

    Any existing `signatures` field is ignored when computing the payload.
    """
    protected = {"alg": "EdDSA", "kid": kid, "jku": jku}
    protected_b64 = b64url_encode(jcs_canonicalize(protected))
    payload_b64 = b64url_encode(jcs_canonicalize(_without_signatures(card)))
    signing_input = f"{protected_b64}.{payload_b64}".encode("ascii")
    signature = private_key.sign(signing_input)
    signed = _without_signatures(card)
    signed["signatures"] = [{"protected": protected_b64, "signature": b64url_encode(signature)}]
    return signed


def protected_header(signature_obj: dict[str, str]) -> dict[str, Any]:
    """Decode a signature object's protected header (for kid/jku inspection)."""
    header: dict[str, Any] = json.loads(b64url_decode(signature_obj["protected"]))
    return header


def verify_card(card: dict[str, Any], public_key: Ed25519PublicKey) -> bool:
    """Verify the card's first signature against ``public_key``."""
    signatures = card.get("signatures") or []
    if not signatures:
        return False
    sig = signatures[0]
    payload_b64 = b64url_encode(jcs_canonicalize(_without_signatures(card)))
    signing_input = f"{sig['protected']}.{payload_b64}".encode("ascii")
    try:
        public_key.verify(b64url_decode(sig["signature"]), signing_input)
        return True
    except (InvalidSignature, KeyError, ValueError):
        return False
