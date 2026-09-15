"""P1-01 tests: signed Agent Card, JCS fingerprint, provider-only JWKS."""

from __future__ import annotations

import copy

from fastapi.testclient import TestClient

from gateway import card
from gateway.app import create_app
from gateway.canonical import jcs_canonicalize
from gateway.signing import (
    b64url_decode,
    b64url_encode,
    card_fingerprint,
    sign_card,
    verify_card,
)
from wallet.keys import PROVIDER_KID, ensure_keys

REGISTRY = ensure_keys()
PROVIDER_PUB = REGISTRY.provider.public
HOLDER_PUB = REGISTRY.holders["lena"].public
ISSUER_PUB = REGISTRY.issuer.public


def test_signed_card_verifies_with_provider_key() -> None:
    signed = card.signed_card()
    assert signed["signatures"]
    assert verify_card(signed, PROVIDER_PUB) is True


def test_tampered_card_fails() -> None:
    signed = copy.deepcopy(card.signed_card())
    signed["name"] = "Boese AG"
    assert verify_card(signed, PROVIDER_PUB) is False


def test_card_signed_with_foreign_key_fails() -> None:
    # A card validly signed by a non-provider key must not verify as the provider.
    forged = sign_card(
        card.load_card_template(), REGISTRY.holders["lena"].private, "holder-lena", "x"
    )
    assert verify_card(forged, PROVIDER_PUB) is False
    # And the real card does not verify against foreign public keys.
    signed = card.signed_card()
    assert verify_card(signed, HOLDER_PUB) is False
    assert verify_card(signed, ISSUER_PUB) is False


def test_fingerprint_ignores_signatures() -> None:
    template_fp = card_fingerprint(card.load_card_template())
    signed_fp = card_fingerprint(card.signed_card())
    assert template_fp == signed_fp == card.provider_fingerprint()
    assert template_fp.startswith("sha256:")


def test_provider_jwks_excludes_issuer_and_holder_kids() -> None:
    kids = {k["kid"] for k in card.provider_jwks()["keys"]}
    assert kids == {PROVIDER_KID}
    assert "mock-bundesdruckerei" not in kids
    assert not any(k.startswith("holder-") for k in kids)


def test_endpoints_serve_verifiable_card_and_jwks() -> None:
    client = TestClient(create_app())

    card_resp = client.get("/.well-known/agent-card.json")
    assert card_resp.status_code == 200
    # Verification re-canonicalizes the parsed JSON, so wire serialization is irrelevant.
    assert verify_card(card_resp.json(), PROVIDER_PUB) is True

    jwks_resp = client.get("/.well-known/jwks.json")
    assert jwks_resp.status_code == 200
    assert {k["kid"] for k in jwks_resp.json()["keys"]} == {PROVIDER_KID}


def test_signing_input_uses_stored_protected_header() -> None:
    # Verification must use the exact stored protected string, not a re-encode.
    signed = card.signed_card()
    sig = signed["signatures"][0]
    body = {k: v for k, v in signed.items() if k != "signatures"}
    signing_input = f"{sig['protected']}.{b64url_encode(jcs_canonicalize(body))}".encode("ascii")
    PROVIDER_PUB.verify(b64url_decode(sig["signature"]), signing_input)  # no raise == valid
