"""Consume-once store for mandate/proof `jti`s (in-memory MVP).

Replaced by a SQLite-backed store when the state machine lands (P1-07); the
interface (`seen`/`consume`) stays identical.
"""

from __future__ import annotations


class JtiStore:
    def __init__(self) -> None:
        self._seen: set[str] = set()

    def seen(self, jti: str) -> bool:
        return jti in self._seen

    def consume(self, jti: str) -> bool:
        """Record `jti`; return False if it was already consumed (replay)."""
        if jti in self._seen:
            return False
        self._seen.add(jti)
        return True
