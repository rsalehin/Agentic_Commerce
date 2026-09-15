"""P1-02 tests: discovery via verified directory + pinned card key."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import httpx

from agent.discovery import verify, verify_card_against_directory
from gateway import card as gateway_card
from gateway.signing import sign_card
from wallet.keys import PROVIDER_KID, ensure_keys

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ensure_keys()
JKU = "http://localhost:8080/.well-known/jwks.json"


def _lookalike_template() -> dict:
    data = json.loads(
        (REPO_ROOT / "fixtures" / "attacks" / "lookalike-card.json").read_text(encoding="utf-8")
    )
    data.pop("_comment", None)
    data.pop("signatures", None)
    return data


def test_valid_provider_card_verifies() -> None:
    result = verify_card_against_directory(gateway_card.signed_card())
    assert result.verified is True
    assert result.reason is None
    assert result.fingerprint == gateway_card.provider_fingerprint()


def test_tampered_card_is_signature_invalid() -> None:
    signed = copy.deepcopy(gateway_card.signed_card())
    signed["name"] = "Boese AG"
    result = verify_card_against_directory(signed)
    assert result.verified is False
    assert result.reason == "CARD_SIGNATURE_INVALID"


def test_validly_signed_lookalike_domain_is_refused() -> None:
    # Signed with its own (attacker) key + own kid, self-consistent, but the
    # domain fonds-ag.example.co is not in the directory.
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    attacker = Ed25519PrivateKey.generate()
    lookalike = sign_card(_lookalike_template(), attacker, "attacker-2026", JKU)
    result = verify_card_against_directory(lookalike)
    assert result.verified is False
    assert result.reason == "PROVIDER_UNVERIFIED"


def test_same_domain_key_substitution_is_refused() -> None:
    # Real domain, but signed by a foreign key while claiming the pinned kid.
    # The pinned key material (local keystore) does not match -> refused.
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    attacker = Ed25519PrivateKey.generate()
    forged = sign_card(gateway_card.load_card_template(), attacker, PROVIDER_KID, JKU)
    result = verify_card_against_directory(forged)
    assert result.verified is False
    assert result.reason == "CARD_SIGNATURE_INVALID"


def test_wrong_kid_is_refused() -> None:
    # Signed by the real provider key but labelled with a non-pinned kid.
    forged = sign_card(gateway_card.load_card_template(), REGISTRY.provider.private, "other", JKU)
    result = verify_card_against_directory(forged)
    assert result.verified is False
    assert result.reason == "CARD_SIGNATURE_INVALID"


def test_missing_onboarding_capability_is_refused() -> None:
    template = gateway_card.load_card_template()
    template["capabilities"] = {"documents": "v1"}
    template["skills"] = []
    resigned = sign_card(template, REGISTRY.provider.private, PROVIDER_KID, JKU)
    result = verify_card_against_directory(resigned)
    assert result.verified is False
    assert result.reason == "ONBOARDING_UNSUPPORTED"


def _card_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/.well-known/agent-card.json":
        return httpx.Response(200, json=gateway_card.signed_card())
    return httpx.Response(404)


def test_verify_over_http_against_gateway() -> None:
    with httpx.Client(transport=httpx.MockTransport(_card_handler)) as client:
        result = verify("http://localhost:8080", client=client)
    assert result.verified is True
    assert result.fingerprint == gateway_card.provider_fingerprint()


def test_unreachable_provider_is_unverified() -> None:
    with httpx.Client(transport=httpx.MockTransport(_card_handler)) as client:
        result = verify("http://localhost:8080/nope", client=client)  # 404 -> HTTP error
    assert result.verified is False
    assert result.reason == "PROVIDER_UNVERIFIED"
