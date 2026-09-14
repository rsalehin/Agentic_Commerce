"""P1-03 tests: mandate JWS verifier and R-MND-04 agent binding."""

from __future__ import annotations

import base64
import json
from typing import Any

from gateway.adapters.jti_store import JtiStore
from gateway.adapters.mandate_jws import JwsMandateVerifier, check_agent_binding
from wallet.keys import ensure_keys
from wallet.mandate import build_mandate, sign_mandate

PROVIDER_DOMAIN = "https://fonds-ag.example"
FP = "sha256:card-fingerprint"
AGENT_ID = "agent:kundenagent-demo"
NOW = 1_800_000_000
SCOPE = {
    "product_classes": ["fonds", "etf"],
    "monthly_amount_max": 200,
    "one_off_amount_max": 0,
    "advice_allowed": False,
}
REG = ensure_keys()


def _payload(holder_did: str, *, ttl: int = 3600) -> dict[str, Any]:
    return build_mandate(
        holder_did=holder_did,
        provider_domain=PROVIDER_DOMAIN,
        card_fingerprint=FP,
        agent_id=AGENT_ID,
        agent_provider="Anthropic Claude (Demo)",
        mandate_scope=SCOPE,
        revocation_url="http://localhost:8081/revocations",
        now=NOW,
        ttl_seconds=ttl,
    )


def _lena_jws(**kw: int) -> str:
    lena = REG.holders["lena"]
    return sign_mandate(_payload(lena.did, **kw), lena.private, "holder-lena")


def test_valid_mandate_verifies() -> None:
    res = JwsMandateVerifier().verify(_lena_jws(), expected_aud=PROVIDER_DOMAIN, now=NOW + 5)
    assert res.ok and res.error_code is None


def test_expired_is_guard_error() -> None:
    token = _lena_jws(ttl=100)
    res = JwsMandateVerifier().verify(token, expected_aud=PROVIDER_DOMAIN, now=NOW + 200)
    assert res.ok is False
    assert res.error_code == "MANDATE_EXPIRED"  # ERROR guard, retryable
    assert res.mandate is not None  # parsed, so the guard can be audited


def test_wrong_audience_is_invalid() -> None:
    res = JwsMandateVerifier().verify(_lena_jws(), expected_aud="https://evil.example", now=NOW + 5)
    assert res.ok is False
    assert res.error_code == "MANDATE_INVALID"


def test_scope_tampering_breaks_signature() -> None:
    token = _lena_jws()
    header, payload_b64, sig = token.split(".")
    payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "=="))
    payload["scope"]["monthly_amount_max"]["value"] = 1_000_000
    tampered_payload = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    tampered = f"{header}.{tampered_payload}.{sig}"
    res = JwsMandateVerifier().verify(tampered, expected_aud=PROVIDER_DOMAIN, now=NOW + 5)
    assert res.ok is False
    assert res.error_code == "SIGNATURE_INVALID"


def test_foreign_key_signature_fails() -> None:
    # iss = lena's did:key, but signed with marco's key -> verify against iss fails.
    lena, marco = REG.holders["lena"], REG.holders["marco"]
    forged = sign_mandate(_payload(lena.did), marco.private, "holder-marco")
    res = JwsMandateVerifier().verify(forged, expected_aud=PROVIDER_DOMAIN, now=NOW + 5)
    assert res.ok is False
    assert res.error_code == "SIGNATURE_INVALID"


def test_jti_replay_is_rejected() -> None:
    verifier = JwsMandateVerifier(JtiStore())
    token = _lena_jws()
    first = verifier.verify(token, expected_aud=PROVIDER_DOMAIN, now=NOW + 5, consume_jti=True)
    second = verifier.verify(token, expected_aud=PROVIDER_DOMAIN, now=NOW + 5, consume_jti=True)
    assert first.ok is True
    assert second.ok is False and second.error_code == "MANDATE_INVALID"


def test_agent_binding_ok_and_failures() -> None:
    res = JwsMandateVerifier().verify(_lena_jws(), expected_aud=PROVIDER_DOMAIN, now=NOW + 5)
    assert res.mandate is not None
    m = res.mandate
    ok = check_agent_binding(
        m, call_card_fingerprint=FP, provider_card_fingerprint=FP, call_agent_id=AGENT_ID
    )
    assert ok is None
    # provider card fingerprint mismatch
    bad_card = check_agent_binding(
        m,
        call_card_fingerprint=FP,
        provider_card_fingerprint="sha256:other",
        call_agent_id=AGENT_ID,
    )
    assert bad_card == "AGENT_UNVERIFIED"
    # calling agent id != mandate.agent.id
    bad_agent = check_agent_binding(
        m, call_card_fingerprint=FP, provider_card_fingerprint=FP, call_agent_id="agent:evil"
    )
    assert bad_agent == "AGENT_UNVERIFIED"
