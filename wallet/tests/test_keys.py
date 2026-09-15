"""P0-03 tests for wallet.keys: generation, idempotency, JWKS, did:key."""

from __future__ import annotations

import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from wallet.keys import (
    ISSUER_KID,
    PROVIDER_KID,
    KeyRegistry,
    did_key_from_public,
    ensure_keys,
    raw_public_from_did_key,
)

PERSONAS = ["lena", "marco", "sanction_test"]
SERVICE_KIDS = {"volksbank-leipzig", "agent-kundenagent-demo"}


def _fresh(fixtures_dir: Path) -> KeyRegistry:
    return ensure_keys(fixtures_dir=fixtures_dir, persona_ids=PERSONAS)


def _expected_kids() -> set[str]:
    return {ISSUER_KID, PROVIDER_KID, *(f"holder-{p}" for p in PERSONAS), *SERVICE_KIDS}


def test_first_run_creates_private_keys_and_jwks(tmp_path: Path) -> None:
    reg = _fresh(tmp_path)
    keys_dir = tmp_path / "keys"
    stems = {p.stem.removesuffix(".private") for p in keys_dir.glob("*.private.pem")}
    assert stems == _expected_kids()
    assert (tmp_path / "jwks.public.json").exists()
    assert set(reg.holders) == set(PERSONAS)
    assert set(reg.services) == SERVICE_KIDS


def test_idempotent_no_overwrite(tmp_path: Path) -> None:
    _fresh(tmp_path)
    keys_dir = tmp_path / "keys"
    before = {p.name: p.read_bytes() for p in keys_dir.glob("*.pem")}
    jwks_before = (tmp_path / "jwks.public.json").read_bytes()

    _fresh(tmp_path)  # second run
    after = {p.name: p.read_bytes() for p in keys_dir.glob("*.pem")}
    assert after == before  # private keys byte-identical
    assert (tmp_path / "jwks.public.json").read_bytes() == jwks_before


def test_jwks_has_expected_kids_and_is_valid_okp(tmp_path: Path) -> None:
    _fresh(tmp_path)
    jwks = json.loads((tmp_path / "jwks.public.json").read_text(encoding="utf-8"))
    kids = {k["kid"] for k in jwks["keys"]}
    assert kids == _expected_kids()
    for k in jwks["keys"]:
        assert k["kty"] == "OKP"
        assert k["crv"] == "Ed25519"
        assert k["alg"] == "EdDSA"
        assert k["x"]


def test_no_private_material_in_jwks(tmp_path: Path) -> None:
    _fresh(tmp_path)
    text = (tmp_path / "jwks.public.json").read_text(encoding="utf-8")
    jwks = json.loads(text)
    assert "PRIVATE" not in text
    assert all("d" not in key for key in jwks["keys"])  # no RFC 8037 private "d"


def test_holder_did_key_roundtrips(tmp_path: Path) -> None:
    reg = _fresh(tmp_path)
    for holder in reg.holders.values():
        did = holder.did
        assert did.startswith("did:key:z")
        raw = holder.public.public_bytes_raw()
        assert raw_public_from_did_key(did) == raw
    # holder JWKs carry their did and persona
    jwks = json.loads((tmp_path / "jwks.public.json").read_text(encoding="utf-8"))
    holder_jwks = [k for k in jwks["keys"] if k.get("role") == "holder"]
    assert len(holder_jwks) == len(PERSONAS)
    assert all(k["did"].startswith("did:key:z") for k in holder_jwks)


def test_did_key_matches_generated_public() -> None:
    key = Ed25519PrivateKey.generate()
    did = did_key_from_public(key.public_key())
    assert raw_public_from_did_key(did) == key.public_key().public_bytes_raw()


def test_default_reads_personas_from_fixtures() -> None:
    # Uses the repo's real fixtures/personas.json (no persona_ids passed).
    reg = ensure_keys()
    assert set(reg.holders) == {"lena", "marco", "sanction_test"}
