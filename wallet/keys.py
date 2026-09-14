"""P0-03 - Ed25519 key generation for the mock trust ecosystem.

On first run this generates Ed25519 key pairs into ``fixtures/keys/`` (gitignored)
for the credential issuer (``mock-bundesdruckerei``), the provider
(``fonds-ag-2026``) and one holder key per persona, then writes the public set to
``fixtures/jwks.public.json``.

Real crypto, mocked parties: private keys never enter the repository (only
``fixtures/keys/`` which is gitignored); the public JWKS is derived from whatever
private keys exist so signatures verify consistently within a run. Holder keys
also expose a ``did:key`` (Ed25519 multicodec + base58btc), used as the mandate
``iss``/``sub``.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = REPO_ROOT / "fixtures"

ISSUER_KID = "mock-bundesdruckerei"
PROVIDER_KID = "fonds-ag-2026"
HOLDER_KID_PREFIX = "holder-"

# Bitcoin/base58btc alphabet, used by did:key multibase 'z'.
_B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
# Multicodec prefix for an Ed25519 public key (0xed varint + 0x01).
_ED25519_MULTICODEC = b"\xed\x01"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b58encode(data: bytes) -> str:
    n = int.from_bytes(data, "big")
    out: list[str] = []
    while n > 0:
        n, rem = divmod(n, 58)
        out.append(_B58_ALPHABET[rem])
    pad = len(data) - len(data.lstrip(b"\x00"))
    return "1" * pad + "".join(reversed(out))


def _b58decode(text: str) -> bytes:
    n = 0
    for ch in text:
        n = n * 58 + _B58_ALPHABET.index(ch)
    body = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
    pad = len(text) - len(text.lstrip("1"))
    return b"\x00" * pad + body


def _raw_public(pub: Ed25519PublicKey) -> bytes:
    return pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def did_key_from_public(pub: Ed25519PublicKey) -> str:
    """Encode an Ed25519 public key as a ``did:key`` identifier."""
    return "did:key:z" + _b58encode(_ED25519_MULTICODEC + _raw_public(pub))


def raw_public_from_did_key(did: str) -> bytes:
    """Inverse of :func:`did_key_from_public`: recover the 32-byte public key."""
    if not did.startswith("did:key:z"):
        raise ValueError(f"not an Ed25519 did:key: {did!r}")
    decoded = _b58decode(did.removeprefix("did:key:z"))
    if not decoded.startswith(_ED25519_MULTICODEC):
        raise ValueError("did:key is not an Ed25519 multicodec key")
    return decoded[len(_ED25519_MULTICODEC) :]


def public_jwk(pub: Ed25519PublicKey, kid: str, **extra: str) -> dict[str, str]:
    """Build an RFC 8037 OKP/Ed25519 public JWK (no private ``d`` member)."""
    return {
        "kty": "OKP",
        "crv": "Ed25519",
        "x": _b64url(_raw_public(pub)),
        "use": "sig",
        "alg": "EdDSA",
        "kid": kid,
        **extra,
    }


@dataclass(frozen=True)
class ManagedKey:
    kid: str
    role: str  # "issuer" | "provider" | "holder"
    private: Ed25519PrivateKey
    persona: str | None = None

    @property
    def public(self) -> Ed25519PublicKey:
        return self.private.public_key()

    @property
    def did(self) -> str:
        return did_key_from_public(self.public)

    def to_jwk(self) -> dict[str, str]:
        extra: dict[str, str] = {"role": self.role}
        if self.role == "holder":
            extra["did"] = self.did
            if self.persona is not None:
                extra["persona"] = self.persona
        return public_jwk(self.public, self.kid, **extra)


@dataclass(frozen=True)
class KeyRegistry:
    issuer: ManagedKey
    provider: ManagedKey
    holders: dict[str, ManagedKey] = field(default_factory=dict)

    def all_keys(self) -> list[ManagedKey]:
        return [self.issuer, self.provider, *self.holders.values()]

    def jwks(self) -> dict[str, list[dict[str, str]]]:
        return {"keys": [k.to_jwk() for k in self.all_keys()]}


def _load_or_create(kid: str, keys_dir: Path) -> Ed25519PrivateKey:
    """Load an existing PKCS8 PEM private key or generate and persist one.

    Idempotent: an existing key is never overwritten, so repeated runs are
    byte-stable and signatures stay valid.
    """
    path = keys_dir / f"{kid}.private.pem"
    if path.exists():
        loaded = serialization.load_pem_private_key(path.read_bytes(), password=None)
        if not isinstance(loaded, Ed25519PrivateKey):
            raise TypeError(f"{path} is not an Ed25519 private key")
        return loaded
    key = Ed25519PrivateKey.generate()
    path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    return key


def _persona_ids(fixtures_dir: Path) -> list[str]:
    personas_path = fixtures_dir / "personas.json"
    data = json.loads(personas_path.read_text(encoding="utf-8"))
    return [p["id"] for p in data["personas"]]


def ensure_keys(
    fixtures_dir: Path = FIXTURES_DIR,
    persona_ids: list[str] | None = None,
) -> KeyRegistry:
    """Ensure all key pairs exist and (re)write ``jwks.public.json``.

    Private keys are generated on first run into ``<fixtures_dir>/keys/`` and
    reused thereafter. The public JWKS is derived from the current private keys.
    """
    keys_dir = fixtures_dir / "keys"
    keys_dir.mkdir(parents=True, exist_ok=True)

    if persona_ids is None:
        persona_ids = _persona_ids(fixtures_dir)

    registry = KeyRegistry(
        issuer=ManagedKey(ISSUER_KID, "issuer", _load_or_create(ISSUER_KID, keys_dir)),
        provider=ManagedKey(
            PROVIDER_KID, "provider", _load_or_create(PROVIDER_KID, keys_dir)
        ),
        holders={
            pid: ManagedKey(
                f"{HOLDER_KID_PREFIX}{pid}",
                "holder",
                _load_or_create(f"{HOLDER_KID_PREFIX}{pid}", keys_dir),
                persona=pid,
            )
            for pid in persona_ids
        },
    )

    jwks_path = fixtures_dir / "jwks.public.json"
    content = json.dumps(registry.jwks(), indent=2, ensure_ascii=False) + "\n"
    if not jwks_path.exists() or jwks_path.read_text(encoding="utf-8") != content:
        jwks_path.write_text(content, encoding="utf-8")
    return registry


def main() -> None:
    registry = ensure_keys()
    kids = ", ".join(k.kid for k in registry.all_keys())
    print(f"[wallet.keys] ensured {len(registry.all_keys())} key pairs: {kids}")
    print(f"[wallet.keys] public JWKS -> {FIXTURES_DIR / 'jwks.public.json'}")


if __name__ == "__main__":
    main()
