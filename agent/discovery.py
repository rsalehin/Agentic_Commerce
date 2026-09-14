"""Provider discovery and Agent Card verification (agent side, P1-02 / ADR-06).

Trust anchor = the verified provider directory, not the card's own key:

1. The domain in the card's ``provider.url`` must be listed in
   ``fixtures/provider-directory.json`` (else ``PROVIDER_UNVERIFIED``).
2. The card signature must verify against the **pinned key** for that domain,
   taken from a trusted local keystore (``fixtures/jwks.public.json``) by
   ``pinned_kid`` — NOT from the JWKS the (possibly hostile) origin serves — and
   the signature's protected ``kid`` must equal ``pinned_kid``
   (else ``CARD_SIGNATURE_INVALID``). This defeats both a lookalike domain and a
   same-domain key substitution.
3. The now-trusted card must advertise the onboarding capability
   (else ``ONBOARDING_UNSUPPORTED``).

No PII is sent by the orchestrator before ``verify`` returns ``verified=True``.
(In production the pinned key material comes from the signed directory/register;
here the committed public keystore stands in for it.)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from gateway.signing import b64url_decode, card_fingerprint, protected_header, verify_card

REPO_ROOT = Path(__file__).resolve().parents[1]
DIRECTORY_PATH = REPO_ROOT / "fixtures" / "provider-directory.json"
KEYSTORE_PATH = REPO_ROOT / "fixtures" / "jwks.public.json"


@dataclass(frozen=True)
class DiscoveryResult:
    verified: bool
    reason: str | None = None
    card: dict[str, Any] | None = None
    fingerprint: str | None = None


def _load_directory() -> dict[str, dict[str, Any]]:
    data = json.loads(DIRECTORY_PATH.read_text(encoding="utf-8"))
    return {entry["domain"]: entry for entry in data["providers"]}


def _pinned_public_key(kid: str) -> Ed25519PublicKey | None:
    keystore = json.loads(KEYSTORE_PATH.read_text(encoding="utf-8"))
    for jwk in keystore["keys"]:
        if jwk["kid"] == kid:
            return Ed25519PublicKey.from_public_bytes(b64url_decode(jwk["x"]))
    return None


def _domain_of(card: dict[str, Any]) -> str | None:
    url = (card.get("provider") or {}).get("url")
    if not isinstance(url, str):
        return None
    return urlparse(url).netloc or None


def _has_onboarding(card: dict[str, Any]) -> bool:
    skills = card.get("skills") or []
    has_skill = any(s.get("id") == "onboarding.v1" for s in skills)
    capable = (card.get("capabilities") or {}).get("onboarding") == "v1"
    interfaces = card.get("supportedInterfaces") or []
    has_mcp = any(i.get("protocol") == "mcp" for i in interfaces)
    return has_skill and capable and has_mcp


def verify_card_against_directory(card: dict[str, Any]) -> DiscoveryResult:
    """Core (no network): directory + pinned-key + capability checks."""
    domain = _domain_of(card)
    directory = _load_directory()
    if domain is None or domain not in directory:
        return DiscoveryResult(False, reason="PROVIDER_UNVERIFIED", card=card)

    pinned_kid = directory[domain]["pinned_kid"]
    pinned_key = _pinned_public_key(pinned_kid)
    if pinned_key is None:
        return DiscoveryResult(False, reason="PROVIDER_UNVERIFIED", card=card)

    signatures = card.get("signatures") or []
    if not signatures or protected_header(signatures[0]).get("kid") != pinned_kid:
        return DiscoveryResult(False, reason="CARD_SIGNATURE_INVALID", card=card)
    if not verify_card(card, pinned_key):
        return DiscoveryResult(False, reason="CARD_SIGNATURE_INVALID", card=card)

    if not _has_onboarding(card):
        return DiscoveryResult(False, reason="ONBOARDING_UNSUPPORTED", card=card)

    return DiscoveryResult(True, card=card, fingerprint=card_fingerprint(card))


def verify(url: str, client: httpx.Client | None = None) -> DiscoveryResult:
    """Fetch the Agent Card from ``{url}/.well-known/agent-card.json`` and verify it."""
    owns_client = client is None
    client = client or httpx.Client(timeout=5.0)
    try:
        resp = client.get(f"{url.rstrip('/')}/.well-known/agent-card.json")
        resp.raise_for_status()
        card: dict[str, Any] = resp.json()
    except (httpx.HTTPError, json.JSONDecodeError):
        return DiscoveryResult(False, reason="PROVIDER_UNVERIFIED")
    finally:
        if owns_client:
            client.close()
    return verify_card_against_directory(card)
