"""Serve the provider's signed Agent Card and the provider-only JWKS.

The card is signed with the provider key (`fonds-ag-2026`). The gateway's
`/.well-known/jwks.json` exposes ONLY the provider key — the credential issuer
key lives at the wallet's origin and customer holder keys are `did:key`
(docs/05 §1). Key material is shared via `wallet.keys` (the demo key module).
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from gateway.signing import card_fingerprint, sign_card
from wallet.keys import PROVIDER_KID, ensure_keys, public_jwk

REPO_ROOT = Path(__file__).resolve().parents[1]
CARD_TEMPLATE_PATH = REPO_ROOT / "fixtures" / "agent-card.example.json"


def _jwks_url() -> str:
    port = os.environ.get("GATEWAY_PORT", "8080")
    return f"http://localhost:{port}/.well-known/jwks.json"


def load_card_template() -> dict[str, Any]:
    """The unsigned card template (any `signatures` field is dropped)."""
    card: dict[str, Any] = json.loads(CARD_TEMPLATE_PATH.read_text(encoding="utf-8"))
    card.pop("signatures", None)
    return card


@lru_cache(maxsize=1)
def signed_card() -> dict[str, Any]:
    """The Agent Card signed with the provider key."""
    registry = ensure_keys()
    return sign_card(load_card_template(), registry.provider.private, PROVIDER_KID, _jwks_url())


def provider_fingerprint() -> str:
    """`card_fingerprint` of the served card (excludes `signatures`)."""
    return card_fingerprint(load_card_template())


@lru_cache(maxsize=1)
def provider_jwks() -> dict[str, list[dict[str, str]]]:
    """Provider-only JWK Set (never the issuer or holder keys)."""
    registry = ensure_keys()
    return {"keys": [public_jwk(registry.provider.public, PROVIDER_KID)]}
