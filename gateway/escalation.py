"""Escalation queues (ADR-07, docs/05 §6).

Two queues: `customer` (from CUSTOMER_REQUIRED — the agent resolves it via
ask_human and re-submits) and `review` (from REVIEW_REQUIRED — staff decide).
Review splits into `adviser` and, for confidential AML cases, `compliance`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Escalation:
    id: str
    session_id: str
    queue: str  # customer | review
    actor_role: str  # customer | adviser | compliance
    reasons: list[str]  # real reason codes (Ops/compliance may see them, GwG §47)
    blocked_from: str | None
    blocked_tool: str | None
    created_at: str
    confidential: bool = False
    status: str = "open"  # open | approved | appointment | rejected
    note: str | None = None
    decided_by: str | None = None
    evidence_hashes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "queue": self.queue,
            "actor_role": self.actor_role,
            "reasons": self.reasons,
            "blocked_from": self.blocked_from,
            "blocked_tool": self.blocked_tool,
            "created_at": self.created_at,
            "confidential": self.confidential,
            "status": self.status,
            "note": self.note,
            "decided_by": self.decided_by,
            "evidence_hashes": self.evidence_hashes,
        }
