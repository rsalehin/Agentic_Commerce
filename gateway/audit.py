"""Hash-chained audit events (docs/03).

Each event's `hash` = `sha256:` + hex(sha256(JCS(event without `hash`))), and
`prev_hash` links to the previous event, so any tampering breaks the chain.
`verify_chain` recomputes every hash and link and returns the first broken index.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from typing import Any

from gateway.canonical import jcs_canonicalize

GENESIS_PREV_HASH = "sha256:genesis"


def _sha256_hex(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def evidence_hash(evidence: dict[str, Any] | None) -> str | None:
    """Hash of the payload that satisfied a step (None if no evidence)."""
    if evidence is None:
        return None
    return _sha256_hex(jcs_canonicalize(evidence))


@dataclass
class AuditEvent:
    seq: int
    ts: str
    session_id: str
    actor: str  # human | agent | gateway | adviser | compliance | core
    from_state: str
    to_state: str
    tool: str | None
    revision: int
    reason_codes: list[str]
    rules: list[dict[str, str]]
    policy_version: str | None
    rules_version: str | None
    evidence_hash: str | None
    mandate_id: str | None
    prev_hash: str
    hash: str = ""

    def body(self) -> dict[str, Any]:
        """All fields except `hash` — the pre-image of the hash."""
        return {k: v for k, v in asdict(self).items() if k != "hash"}

    def compute_hash(self) -> str:
        return _sha256_hex(jcs_canonicalize(self.body()))


@dataclass
class AuditChain:
    events: list[AuditEvent] = field(default_factory=list)

    def append(
        self,
        *,
        session_id: str,
        ts: str,
        actor: str,
        from_state: str,
        to_state: str,
        tool: str | None,
        revision: int,
        reason_codes: list[str] | None = None,
        rules: list[dict[str, str]] | None = None,
        policy_version: str | None = None,
        rules_version: str | None = None,
        evidence: dict[str, Any] | None = None,
        mandate_id: str | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            seq=len(self.events),
            ts=ts,
            session_id=session_id,
            actor=actor,
            from_state=from_state,
            to_state=to_state,
            tool=tool,
            revision=revision,
            reason_codes=list(reason_codes or []),
            rules=list(rules or []),
            policy_version=policy_version,
            rules_version=rules_version,
            evidence_hash=evidence_hash(evidence),
            mandate_id=mandate_id,
            prev_hash=self.events[-1].hash if self.events else GENESIS_PREV_HASH,
        )
        event.hash = event.compute_hash()
        self.events.append(event)
        return event


def verify_chain(events: list[AuditEvent]) -> int | None:
    """Return the index of the first broken link, or None if the chain verifies."""
    for i, event in enumerate(events):
        expected_prev = events[i - 1].hash if i > 0 else GENESIS_PREV_HASH
        if event.prev_hash != expected_prev:
            return i
        if event.hash != event.compute_hash():
            return i
    return None
