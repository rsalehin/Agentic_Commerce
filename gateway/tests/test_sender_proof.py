"""P1-03 tests: sender binding (R-MND-05/06) and revocation (R-MND-03)."""

from __future__ import annotations

from typing import Any

from agent.sender import build_sender_proof
from gateway.adapters.client_registry import ClientRegistry
from gateway.adapters.jti_store import JtiStore
from gateway.adapters.revocation import RevocationChecker
from gateway.adapters.sender_proof import verify_sender_proof
from wallet.keys import ensure_keys, public_jwk

CLIENT_ID = "agent:kundenagent-demo"
KID = "agent-kundenagent-demo"
HTM = "POST"
HTU = "http://localhost:8080/v1/onboarding/start"
SID = "ses_1"
NOW = 1_800_000_000

REG = ensure_keys()
INSTANCE = REG.services[KID]


def _registry(status: str = "active", with_key: bool = True) -> ClientRegistry:
    # Inject the CURRENT instance public key (committed instance_jwk goes stale).
    jwk: dict[str, Any] | None = public_jwk(INSTANCE.public, KID) if with_key else None
    return ClientRegistry(clients=[{"client_id": CLIENT_ID, "status": status, "instance_jwk": jwk}])


def _proof(**kw: Any) -> str:
    kw.setdefault("htm", HTM)
    kw.setdefault("htu", HTU)
    kw.setdefault("session_id", SID)
    kw.setdefault("now", NOW)
    return build_sender_proof(INSTANCE.private, KID, **kw)


def _verify(proof: str, **over: Any) -> Any:
    args: dict[str, Any] = dict(
        client_id=CLIENT_ID,
        mandate_agent_id=CLIENT_ID,
        htm=HTM,
        htu=HTU,
        session_id=SID,
        now=NOW,
        registry=_registry(),
        jti_store=JtiStore(),
    )
    args.update(over)
    return verify_sender_proof(proof, **args)


def test_valid_sender_proof() -> None:
    assert _verify(_proof()).ok is True


def test_unregistered_or_blocked_client() -> None:
    res = _verify(_proof(), registry=_registry(status="blocked"))
    assert res.ok is False and res.error_code == "CLIENT_UNREGISTERED"


def test_foreign_key_signature_invalid() -> None:
    # Proof signed by a holder key, not the registered instance key.
    holder = REG.holders["lena"]
    proof = build_sender_proof(holder.private, KID, htm=HTM, htu=HTU, session_id=SID, now=NOW)
    res = _verify(proof)
    assert res.ok is False and res.error_code == "SENDER_BINDING_INVALID"


def test_request_mismatch() -> None:
    res = _verify(_proof(htu="http://localhost:8080/v1/onboarding/ses_1/confirm"))
    assert res.ok is False and res.error_code == "SENDER_BINDING_INVALID"


def test_stale_iat() -> None:
    res = _verify(_proof(now=NOW - 3600))
    assert res.ok is False and res.error_code == "SENDER_BINDING_INVALID"


def test_jti_replay() -> None:
    store = JtiStore()
    proof = _proof(jti="prf_fixed")
    first = _verify(proof, jti_store=store)
    second = _verify(proof, jti_store=store)
    assert first.ok is True
    assert second.ok is False and second.error_code == "SENDER_BINDING_INVALID"


def test_mandate_agent_id_must_equal_client_id() -> None:
    res = _verify(_proof(), mandate_agent_id="agent:someone-else")
    assert res.ok is False and res.error_code == "SENDER_BINDING_INVALID"


def test_revocation_checker() -> None:
    checker = RevocationChecker(revoked_jtis={"mnd_bad"}, registry=_registry())
    assert checker.is_revoked(jti="mnd_bad") is True
    assert checker.is_revoked(jti="mnd_ok") is False
    checker.revoke("mnd_ok")
    assert checker.is_revoked(jti="mnd_ok") is True
    # A blocked client is treated as revoked on writes.
    blocked = RevocationChecker(registry=_registry(status="blocked"))
    assert blocked.is_revoked(jti="mnd_ok", client_id=CLIENT_ID) is True
