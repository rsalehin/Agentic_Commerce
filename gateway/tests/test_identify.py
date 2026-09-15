"""P1-04 tests: IdentityVerifier adapter and wallet issuer JWKS / revocations."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from gateway.adapters.wallet_sdjwt import WalletSdJwtVerifier
from wallet.app import create_app, issuer_jwks
from wallet.holder import present_pid
from wallet.issuer import issue_pid_for_persona
from wallet.keys import ISSUER_KID, ensure_keys

REPO_ROOT = Path(__file__).resolve().parents[2]
REG = ensure_keys()
NOW = 1_800_000_000
AUD = "https://fonds-ag.example"
NONCE = "nonce-xyz"


def _lena_presentation() -> str:
    data = json.loads((REPO_ROOT / "fixtures" / "personas.json").read_text(encoding="utf-8"))
    lena = next(p for p in data["personas"] if p["id"] == "lena")
    vc = issue_pid_for_persona(lena, REG, now=NOW)
    return present_pid(
        vc,
        requested_claims=["given_name", "family_name", "assurance_level", "nationalities"],
        holder_key=REG.holders["lena"].private,
        holder_kid="holder-lena",
        nonce=NONCE,
        aud=AUD,
        now=NOW,
    )


def test_adapter_verifies_presentation() -> None:
    verifier = WalletSdJwtVerifier(issuer_jwks())
    res = verifier.verify(_lena_presentation(), nonce=NONCE, aud=AUD, now=NOW)
    assert res.ok is True
    assert res.claims is not None and res.claims["given_name"] == "Lena"
    assert res.assurance_level == "high"
    assert res.cnf_did == REG.holders["lena"].did


def test_adapter_maps_presentation_invalid() -> None:
    verifier = WalletSdJwtVerifier(issuer_jwks())
    res = verifier.verify(_lena_presentation(), nonce="wrong", aud=AUD, now=NOW)
    assert res.ok is False
    assert res.error_code == "PRESENTATION_INVALID"


def test_adapter_unknown_issuer_kid() -> None:
    verifier = WalletSdJwtVerifier({"keys": []})
    res = verifier.verify(_lena_presentation(), nonce=NONCE, aud=AUD, now=NOW)
    assert res.ok is False
    assert res.error_code == "SIGNATURE_INVALID"


def test_wallet_serves_issuer_jwks_only() -> None:
    client = TestClient(create_app())
    kids = {k["kid"] for k in client.get("/.well-known/jwks.json").json()["keys"]}
    assert kids == {ISSUER_KID}


def test_wallet_serves_revocations() -> None:
    client = TestClient(create_app())
    assert client.get("/revocations").json() == {"revoked": []}
