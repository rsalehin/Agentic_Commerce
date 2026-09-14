"""P1-04 tests: in-house SD-JWT VC issue/present/verify and holder binding."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from wallet import sdjwt
from wallet.holder import present_pid
from wallet.issuer import issue_pid_for_persona
from wallet.keys import ensure_keys

REPO_ROOT = Path(__file__).resolve().parents[2]
REG = ensure_keys()
NOW = 1_800_000_000
AUD = "https://fonds-ag.example"
NONCE = "nonce-abc"
REQUESTED = ["given_name", "family_name", "birth_date", "nationalities", "assurance_level"]


def _persona(pid: str) -> dict:
    data = json.loads((REPO_ROOT / "fixtures" / "personas.json").read_text(encoding="utf-8"))
    return next(p for p in data["personas"] if p["id"] == pid)


def _present(persona_id: str, *, holder_id: str | None = None, **over: object) -> str:
    holder_id = holder_id or persona_id
    vc = issue_pid_for_persona(_persona(persona_id), REG, now=NOW)
    kwargs = dict(
        requested_claims=REQUESTED,
        holder_key=REG.holders[holder_id].private,
        holder_kid=f"holder-{holder_id}",
        nonce=NONCE,
        aud=AUD,
        now=NOW,
    )
    kwargs.update(over)
    return present_pid(vc, **kwargs)  # type: ignore[arg-type]


def _verify(presentation: str, **over: object) -> sdjwt.VerifiedPid:
    kwargs = dict(
        issuer_public_key=REG.issuer.public,
        expected_nonce=NONCE,
        expected_aud=AUD,
        now=NOW,
    )
    kwargs.update(over)
    return sdjwt.verify(presentation, **kwargs)  # type: ignore[arg-type]


def test_happy_only_requested_claims_and_binding() -> None:
    pid = _verify(_present("lena"))
    assert set(pid.claims) == set(REQUESTED)  # only requested claims disclosed
    assert pid.claims["given_name"] == "Lena"
    assert "tax_id" not in pid.claims  # not requested -> not revealed
    assert pid.assurance_level == "high"
    assert pid.issuer == "mock-bundesdruckerei"
    # R-ID-05: cnf key binds to the persona's holder key (== mandate iss).
    assert pid.cnf_did == REG.holders["lena"].did


def test_selective_disclosure_subset() -> None:
    pid = _verify(_present("lena", requested_claims=["given_name"]))
    assert set(pid.claims) == {"given_name"}


def test_wrong_nonce_fails() -> None:
    with pytest.raises(sdjwt.SdJwtError) as exc:
        _verify(_present("lena"), expected_nonce="other")
    assert exc.value.code == "PRESENTATION_INVALID"


def test_wrong_audience_fails() -> None:
    with pytest.raises(sdjwt.SdJwtError) as exc:
        _verify(_present("lena"), expected_aud="https://evil.example")
    assert exc.value.code == "PRESENTATION_INVALID"


def test_issuer_key_mismatch_fails() -> None:
    with pytest.raises(sdjwt.SdJwtError) as exc:
        _verify(_present("lena"), issuer_public_key=REG.holders["lena"].public)
    assert exc.value.code == "SIGNATURE_INVALID"


def test_wrong_holder_key_breaks_binding() -> None:
    # lena's VC (cnf = lena) presented with marco's holder key -> KB fails.
    pres = _present("lena", holder_id="marco")
    with pytest.raises(sdjwt.SdJwtError) as exc:
        _verify(pres)
    assert exc.value.code == "SIGNATURE_INVALID"


def test_tampered_disclosure_fails() -> None:
    pres = _present("lena")
    parts = pres.split("~")
    # Flip a character in the first disclosure.
    disclosure = parts[1]
    parts[1] = ("A" if disclosure[0] != "A" else "B") + disclosure[1:]
    with pytest.raises(sdjwt.SdJwtError) as exc:
        _verify("~".join(parts))
    assert exc.value.code == "PRESENTATION_INVALID"


def test_holder_mandate_mismatch_is_visible_via_cnf() -> None:
    # A presentation from marco's VC carries marco's cnf_did, which would not
    # equal a lena mandate's iss -> the gateway's R-ID-05 would DENY.
    pid = _verify(_present("marco"))
    assert pid.cnf_did == REG.holders["marco"].did
    assert pid.cnf_did != REG.holders["lena"].did
