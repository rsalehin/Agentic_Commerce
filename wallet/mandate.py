"""Build and sign an Intent Mandate on the customer's wallet (docs/05 §2).

The wallet wraps a persona's concise `mandate_scope` (scalar amounts) into the
mandate schema (dynamic iat/exp, EUR amounts, default data_release) and signs it
with the persona's holder key (header kid `holder-<persona>`, payload iss/sub =
the holder did:key).
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from gateway.jws import sign_compact

# The standard PID data-release set (docs/05 §2).
DEFAULT_DATA_RELEASE = [
    "pid.given_name",
    "pid.family_name",
    "pid.birth_date",
    "pid.birth_place",
    "pid.birth_place_country",
    "pid.nationalities",
    "pid.address",
    "pid.tax_id",
    "pid.national_id_number",
]


def build_mandate(
    *,
    holder_did: str,
    provider_domain: str,
    card_fingerprint: str,
    agent_id: str,
    agent_provider: str,
    mandate_scope: dict[str, Any],
    revocation_url: str,
    now: int | None = None,
    ttl_seconds: int = 86_400,
    data_release: list[str] | None = None,
) -> dict[str, Any]:
    """Assemble a mandate payload from a persona's `mandate_scope`."""
    issued = int(time.time()) if now is None else now
    return {
        "iss": holder_did,
        "sub": holder_did,
        "aud": provider_domain,
        "iat": issued,
        "exp": issued + ttl_seconds,
        "jti": f"mnd_{uuid.uuid4().hex}",
        "agent": {"id": agent_id, "provider": agent_provider, "card_fingerprint": card_fingerprint},
        "purpose": "depot_opening",
        "scope": {
            "product_classes": list(mandate_scope["product_classes"]),
            "monthly_amount_max": {"value": mandate_scope["monthly_amount_max"], "currency": "EUR"},
            "one_off_amount_max": {"value": mandate_scope["one_off_amount_max"], "currency": "EUR"},
            "advice_allowed": bool(mandate_scope["advice_allowed"]),
            "data_release": list(data_release or DEFAULT_DATA_RELEASE),
        },
        "human_only": ["tax_declaration", "sign_contract"],
        "revocation_url": revocation_url,
    }


def sign_mandate(payload: dict[str, Any], holder_key: Ed25519PrivateKey, kid: str) -> str:
    """Sign a mandate payload → compact JWS (header kid = `holder-<persona>`)."""
    return sign_compact(payload, holder_key, kid)
