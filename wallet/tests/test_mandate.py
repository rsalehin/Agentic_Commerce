"""P1-03 tests: wallet mandate build + sign, verified by the gateway adapter."""

from __future__ import annotations

from gateway.adapters.mandate_jws import JwsMandateVerifier
from wallet.keys import ensure_keys
from wallet.mandate import DEFAULT_DATA_RELEASE, build_mandate, sign_mandate

PROVIDER_DOMAIN = "https://fonds-ag.example"
FP = "sha256:deadbeef"
AGENT_ID = "agent:kundenagent-demo"
NOW = 1_800_000_000
SCOPE = {
    "product_classes": ["fonds", "etf"],
    "monthly_amount_max": 200,
    "one_off_amount_max": 0,
    "advice_allowed": False,
}


def _mandate_jws() -> str:
    lena = ensure_keys().holders["lena"]
    payload = build_mandate(
        holder_did=lena.did,
        provider_domain=PROVIDER_DOMAIN,
        card_fingerprint=FP,
        agent_id=AGENT_ID,
        agent_provider="Anthropic Claude (Demo)",
        mandate_scope=SCOPE,
        revocation_url="http://localhost:8081/revocations",
        now=NOW,
        ttl_seconds=3600,
    )
    return sign_mandate(payload, lena.private, "holder-lena")


def test_build_wraps_scalars_and_fills_data_release() -> None:
    lena = ensure_keys().holders["lena"]
    payload = build_mandate(
        holder_did=lena.did,
        provider_domain=PROVIDER_DOMAIN,
        card_fingerprint=FP,
        agent_id=AGENT_ID,
        agent_provider="Anthropic Claude (Demo)",
        mandate_scope=SCOPE,
        revocation_url="http://localhost:8081/revocations",
        now=NOW,
    )
    assert payload["scope"]["monthly_amount_max"] == {"value": 200, "currency": "EUR"}
    assert payload["scope"]["data_release"] == DEFAULT_DATA_RELEASE
    assert payload["iss"] == payload["sub"] == lena.did
    assert payload["exp"] == NOW + 86_400


def test_signed_mandate_verifies() -> None:
    res = JwsMandateVerifier().verify(_mandate_jws(), expected_aud=PROVIDER_DOMAIN, now=NOW + 10)
    assert res.ok is True
    assert res.mandate is not None
    assert res.mandate.scope.product_classes == ["fonds", "etf"]
    assert res.mandate.agent.id == AGENT_ID
