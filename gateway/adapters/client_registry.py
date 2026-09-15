"""Agent client registry (fixtures/agent-clients.json).

The gateway-side registry of agent operator clients: which `client_id`s are
registered/active and their instance public keys (to verify `x-sender-proof`).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from gateway.signing import b64url_decode

REPO_ROOT = Path(__file__).resolve().parents[2]
CLIENTS_PATH = REPO_ROOT / "fixtures" / "agent-clients.json"


class ClientRegistry:
    def __init__(
        self,
        clients: list[dict[str, Any]] | None = None,
        clients_path: Path = CLIENTS_PATH,
    ) -> None:
        # `clients` may be injected (tests use the current instance key, since the
        # committed instance_jwk goes stale on a fresh clone like jwks.public.json).
        if clients is None:
            clients = json.loads(clients_path.read_text(encoding="utf-8"))["clients"]
        self._clients = {c["client_id"]: c for c in clients}

    def is_active(self, client_id: str) -> bool:
        client = self._clients.get(client_id)
        return bool(client and client.get("status") == "active")

    def instance_key(self, client_id: str) -> Ed25519PublicKey | None:
        client = self._clients.get(client_id)
        if not client or not client.get("instance_jwk"):
            return None
        return Ed25519PublicKey.from_public_bytes(b64url_decode(client["instance_jwk"]["x"]))
