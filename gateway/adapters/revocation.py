"""Revocation check on writes (R-MND-03).

Every state-changing call re-checks the mandate `revocation_url` and the client
status. In the MVP the revocation source is a set of revoked `jti`s; P1-04 wires
it to the wallet's `/revocations` endpoint (same interface). A revoked mandate or
a blocked client → `MANDATE_REVOKED` (DENY).
"""

from __future__ import annotations

from collections.abc import Iterable

from gateway.adapters.client_registry import ClientRegistry


class RevocationChecker:
    def __init__(
        self,
        revoked_jtis: Iterable[str] | None = None,
        registry: ClientRegistry | None = None,
    ) -> None:
        self._revoked: set[str] = set(revoked_jtis or ())
        self._registry = registry

    def revoke(self, jti: str) -> None:
        self._revoked.add(jti)

    def is_revoked(self, *, jti: str, client_id: str | None = None) -> bool:
        if jti in self._revoked:
            return True
        if client_id is not None and self._registry is not None:
            return not self._registry.is_active(client_id)
        return False
