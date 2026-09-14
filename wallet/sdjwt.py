"""In-house SD-JWT VC (JWS issuer credential + `_sd` disclosures + KB-JWT).

Real EdDSA crypto (PyJWT + cryptography); the `IdentityVerifier` port stays
identical if the `sd-jwt` library is swapped in later (ADR-03). Format:

    issue:   <issuer-jws>~<disclosure>~...~
    present: <issuer-jws>~<selected-disclosure>~...~<kb-jwt>

A disclosure is `base64url(json([salt, name, value]))`; the issuer JWS carries
`_sd` = the sha-256 hashes of every disclosure. The exact disclosure string is
what is hashed, so no canonicalization is needed for reproducibility. The KB-JWT
binds the presentation to a nonce + audience and carries `sd_hash` over the
issuer JWS and the selected disclosures.
"""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass
from typing import Any

import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from gateway.jws import JwsError, unverified_header, verify_compact
from gateway.signing import b64url_decode, b64url_encode
from wallet.keys import did_key_from_public

DEFAULT_VCT = "urn:eudi:pid:de:1"
SD_ALG = "sha-256"


class SdJwtError(Exception):
    """SD-JWT verification failure. `code` is PRESENTATION_INVALID or SIGNATURE_INVALID."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class VerifiedPid:
    claims: dict[str, Any]
    cnf_jwk: dict[str, str]
    cnf_did: str
    issuer: str
    vct: str
    assurance_level: str | None


def _sd_hash(disclosure_b64: str) -> str:
    return b64url_encode(hashlib.sha256(disclosure_b64.encode("ascii")).digest())


def _make_disclosure(name: str, value: Any) -> str:
    salt = b64url_encode(secrets.token_bytes(16))
    payload = json.dumps([salt, name, value], ensure_ascii=False, separators=(",", ":"))
    return b64url_encode(payload.encode("utf-8"))


def _disclosure_name(disclosure_b64: str) -> str:
    name: str = json.loads(b64url_decode(disclosure_b64))[1]
    return name


def issue(
    claims: dict[str, Any],
    *,
    issuer_key: Ed25519PrivateKey,
    issuer_kid: str,
    holder_jwk: dict[str, str],
    vct: str = DEFAULT_VCT,
    now: int,
) -> str:
    """Issue an SD-JWT VC: every claim is selectively disclosable."""
    disclosures = [_make_disclosure(name, value) for name, value in claims.items()]
    payload = {
        "iss": issuer_kid,
        "iat": now,
        "vct": vct,
        "cnf": {"jwk": holder_jwk},
        "_sd": sorted(_sd_hash(d) for d in disclosures),
        "_sd_alg": SD_ALG,
    }
    issuer_jws = jwt.encode(
        payload, issuer_key, algorithm="EdDSA", headers={"kid": issuer_kid, "typ": "vc+sd-jwt"}
    )
    return "~".join([issuer_jws, *disclosures]) + "~"


def present(
    sd_jwt_vc: str,
    *,
    disclose: list[str],
    holder_key: Ed25519PrivateKey,
    holder_kid: str,
    nonce: str,
    aud: str,
    now: int,
) -> str:
    """Select the requested disclosures and append a KB-JWT bound to nonce+aud."""
    parts = [p for p in sd_jwt_vc.split("~") if p]
    issuer_jws, all_disclosures = parts[0], parts[1:]
    selected = [d for d in all_disclosures if _disclosure_name(d) in disclose]
    sd_part = "~".join([issuer_jws, *selected]) + "~"
    kb = jwt.encode(
        {"nonce": nonce, "aud": aud, "iat": now, "sd_hash": _sd_hash_of(sd_part)},
        holder_key,
        algorithm="EdDSA",
        headers={"kid": holder_kid, "typ": "kb+jwt"},
    )
    return sd_part + kb


def _sd_hash_of(sd_part: str) -> str:
    return b64url_encode(hashlib.sha256(sd_part.encode("ascii")).digest())


def verify(
    presentation: str,
    *,
    issuer_public_key: Ed25519PublicKey,
    expected_nonce: str,
    expected_aud: str,
    now: int,
) -> VerifiedPid:
    """Verify issuer signature, key binding, nonce/aud, sd_hash and disclosures."""
    parts = presentation.split("~")
    if len(parts) < 2:
        raise SdJwtError("PRESENTATION_INVALID", "malformed presentation")
    issuer_jws, disclosures, kb_jwt = parts[0], parts[1:-1], parts[-1]
    if not kb_jwt:
        raise SdJwtError("PRESENTATION_INVALID", "missing KB-JWT")

    # 1. Issuer signature.
    try:
        vc = verify_compact(issuer_jws, issuer_public_key)
    except JwsError as exc:
        raise SdJwtError("SIGNATURE_INVALID", f"issuer signature: {exc}") from exc

    # 2. Key binding: KB-JWT must be signed by the confirmation key (cnf).
    cnf_jwk = (vc.get("cnf") or {}).get("jwk")
    if not isinstance(cnf_jwk, dict) or "x" not in cnf_jwk:
        raise SdJwtError("PRESENTATION_INVALID", "missing cnf.jwk")
    cnf_key = Ed25519PublicKey.from_public_bytes(b64url_decode(cnf_jwk["x"]))
    try:
        kb = verify_compact(kb_jwt, cnf_key)
    except JwsError as exc:
        raise SdJwtError("SIGNATURE_INVALID", f"key binding: {exc}") from exc

    # 3. Nonce + audience.
    if kb.get("nonce") != expected_nonce or kb.get("aud") != expected_aud:
        raise SdJwtError("PRESENTATION_INVALID", "nonce/audience mismatch")

    # 4. sd_hash over the issuer JWS + selected disclosures.
    sd_part = "~".join([issuer_jws, *disclosures]) + "~"
    if kb.get("sd_hash") != _sd_hash_of(sd_part):
        raise SdJwtError("PRESENTATION_INVALID", "sd_hash mismatch")

    # 5. Each disclosure hash must be present in the issuer's _sd (no forgery).
    registered = set(vc.get("_sd") or [])
    claims: dict[str, Any] = {}
    for disclosure in disclosures:
        if _sd_hash(disclosure) not in registered:
            raise SdJwtError("PRESENTATION_INVALID", "undisclosed/forged disclosure")
        _salt, name, value = json.loads(b64url_decode(disclosure))
        claims[name] = value

    return VerifiedPid(
        claims=claims,
        cnf_jwk=cnf_jwk,
        cnf_did=did_key_from_public(cnf_key),
        issuer=str(vc.get("iss")),
        vct=str(vc.get("vct")),
        assurance_level=claims.get("assurance_level"),
    )


def issuer_kid_of(presentation_or_vc: str) -> str | None:
    """Read the issuer JWS `kid` header (to pick the issuer key from a JWKS)."""
    issuer_jws = presentation_or_vc.split("~", 1)[0]
    try:
        return unverified_header(issuer_jws).get("kid")
    except JwsError:
        return None
