"""P3-02: deprecation swap — IDENTITY_VERIFIER=eid_stub, same port, no code change."""

from __future__ import annotations

import pytest

from gateway.adapters.eid_stub import EidStubVerifier
from gateway.service import GatewayService, build_identity_verifier
from gateway.tests.onboarding_helpers import make_service, persona, sender, start_payload
from wallet.eid import present_eid
from wallet.keys import ensure_keys

REG = ensure_keys()
AUD = "https://fonds-ag.example"
NONCE = "nonce-eid"
CLAIMS = {
    "given_name": "Lena",
    "family_name": "Schmidt",
    "birth_date": "1992-03-14",
    "nationalities": ["DE"],
    "address": {"country": "DE"},
    "birth_place_country": "DE",
    "assurance_level": "high",
}


def _eid(pid: str = "lena", *, nonce: str = NONCE, aud: str = AUD) -> str:
    holder = REG.holders[pid]
    return present_eid(
        CLAIMS, holder_key=holder.private, holder_kid=f"holder-{pid}", nonce=nonce, aud=aud, now=1
    )


def test_factory_selects_adapter_by_config() -> None:
    assert isinstance(build_identity_verifier("eid_stub"), EidStubVerifier)
    with pytest.raises(ValueError):
        build_identity_verifier("nope")


def test_eid_stub_verifies_and_binds_holder() -> None:
    res = EidStubVerifier().verify(_eid(), nonce=NONCE, aud=AUD, now=1)
    assert res.ok is True
    assert res.claims is not None and res.claims["given_name"] == "Lena"
    assert res.assurance_level == "high"
    assert res.issuer == "mock-eid"
    assert res.cnf_did == REG.holders["lena"].did  # R-ID-05 binding still works


def test_eid_stub_rejects_wrong_nonce_and_bad_signature() -> None:
    v = EidStubVerifier()
    wrong_nonce = v.verify(_eid(nonce="other"), nonce=NONCE, aud=AUD, now=1)
    assert wrong_nonce.error_code == "PRESENTATION_INVALID"
    # A tampered signature fails the (real) verification against the cnf key.
    tampered = _eid().rsplit(".", 1)[0] + ".AAAA"
    assert v.verify(tampered, nonce=NONCE, aud=AUD, now=1).error_code == "SIGNATURE_INVALID"


def test_identify_works_with_eid_stub_swapped_in() -> None:
    # Same gateway, no code change — only the injected IdentityVerifier differs.
    svc: GatewayService = make_service()
    svc.identity_verifier = EidStubVerifier()

    env = svc.handle("onboarding.start", start_payload("lena", svc))
    sid = env["data"]["session_id"]
    nonce = env["data"]["requested_credentials"]["nonce"]
    ident = svc.handle(
        "onboarding.identify",
        {
            "session_id": sid,
            "presentation": present_eid(
                CLAIMS, holder_key=REG.holders["lena"].private, holder_kid="holder-lena",
                nonce=nonce, aud=AUD, now=1,
            ),
            "reference_account_iban": persona("lena")["reference_account"]["iban"],
            "sender_proof": sender(svc, "onboarding.identify", sid),
        },
    )
    assert ident["ok"] is True and ident["state"] == "SCREENED"
