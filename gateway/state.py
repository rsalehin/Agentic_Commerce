"""Onboarding state machine (docs/03). The gateway owns the state.

Guarded transitions (illegal edge → WRONG_STATE), blocking to
CUSTOMER_REQUIRED / REVIEW_REQUIRED with `blocked_from`, resume exactly at
`blocked_from`, and guard rejections recorded with `from_state == to_state`.
Every transition appends a hash-chained AuditEvent.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from gateway.audit import AuditChain, AuditEvent, verify_chain

# States
DISCOVERED = "DISCOVERED"
MANDATE_VALID = "MANDATE_VALID"
IDENTIFIED = "IDENTIFIED"
SCREENED = "SCREENED"
TAX_CONFIRMED = "TAX_CONFIRMED"
APPROPRIATENESS_DONE = "APPROPRIATENESS_DONE"
INFORMED = "INFORMED"
CUSTOMER_CONFIRMED = "CUSTOMER_CONFIRMED"
BANK_ACCEPTED = "BANK_ACCEPTED"
PROVISIONING = "PROVISIONING"
RECONCILING = "RECONCILING"
DEPOT_OPENED = "DEPOT_OPENED"
CUSTOMER_REQUIRED = "CUSTOMER_REQUIRED"
REVIEW_REQUIRED = "REVIEW_REQUIRED"
ADVISED_HANDOFF = "ADVISED_HANDOFF"
EXPIRED = "EXPIRED"
CANCELLED = "CANCELLED"
REJECTED = "REJECTED"

TERMINAL = frozenset({DEPOT_OPENED, ADVISED_HANDOFF, REJECTED, EXPIRED, CANCELLED})
BLOCK_STATE = {"REQUIRE_CUSTOMER": CUSTOMER_REQUIRED, "REQUIRE_REVIEW": REVIEW_REQUIRED}

# Allowed directed edges (docs/03 mermaid). CANCELLED/EXPIRED reachable from any
# pre-CUSTOMER_CONFIRMED business state.
_PRE_CONFIRM = {
    MANDATE_VALID, IDENTIFIED, SCREENED, TAX_CONFIRMED, APPROPRIATENESS_DONE,
    INFORMED, CUSTOMER_REQUIRED, REVIEW_REQUIRED,
}
ALLOWED: dict[str, set[str]] = {
    DISCOVERED: {MANDATE_VALID, REJECTED},
    MANDATE_VALID: {IDENTIFIED},
    IDENTIFIED: {SCREENED, CUSTOMER_REQUIRED, REVIEW_REQUIRED, REJECTED},
    SCREENED: {TAX_CONFIRMED, CUSTOMER_REQUIRED, REVIEW_REQUIRED},
    TAX_CONFIRMED: {APPROPRIATENESS_DONE, CUSTOMER_REQUIRED, REVIEW_REQUIRED},
    APPROPRIATENESS_DONE: {INFORMED, CUSTOMER_REQUIRED, REVIEW_REQUIRED},
    INFORMED: {CUSTOMER_CONFIRMED, CUSTOMER_REQUIRED},
    CUSTOMER_CONFIRMED: {BANK_ACCEPTED},
    BANK_ACCEPTED: {PROVISIONING},
    PROVISIONING: {DEPOT_OPENED, RECONCILING},
    RECONCILING: {DEPOT_OPENED, REVIEW_REQUIRED},
    CUSTOMER_REQUIRED: {IDENTIFIED, SCREENED, TAX_CONFIRMED, APPROPRIATENESS_DONE, INFORMED},
    REVIEW_REQUIRED: {SCREENED, TAX_CONFIRMED, APPROPRIATENESS_DONE, ADVISED_HANDOFF, REJECTED},
}
for _s in _PRE_CONFIRM:
    ALLOWED[_s] = ALLOWED[_s] | {CANCELLED, EXPIRED}


class WrongStateError(Exception):
    """An illegal transition was attempted (maps to ErrorCode.WRONG_STATE)."""


def _default_clock() -> str:
    return datetime.now(UTC).isoformat()


class Session:
    def __init__(
        self,
        session_id: str,
        *,
        mandate_id: str | None = None,
        rules_version: str = "1.1.0",
        initial_state: str = DISCOVERED,
        clock: Callable[[], str] | None = None,
    ) -> None:
        self.session_id = session_id
        self.mandate_id = mandate_id
        self.rules_version = rules_version
        self.state = initial_state
        self.blocked_from: str | None = None
        self.revision = 1
        self._clock = clock or _default_clock
        self.chain = AuditChain()
        self._record("gateway", "INIT", initial_state, tool=None)

    @property
    def events(self) -> list[AuditEvent]:
        return self.chain.events

    def _record(
        self,
        actor: str,
        from_state: str,
        to_state: str,
        *,
        tool: str | None,
        reason_codes: list[str] | None = None,
        rules: list[dict[str, str]] | None = None,
        policy_version: str | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> AuditEvent:
        return self.chain.append(
            session_id=self.session_id,
            ts=self._clock(),
            actor=actor,
            from_state=from_state,
            to_state=to_state,
            tool=tool,
            revision=self.revision,
            reason_codes=reason_codes,
            rules=rules,
            policy_version=policy_version,
            rules_version=self.rules_version,
            evidence=evidence,
            mandate_id=self.mandate_id,
        )

    def _transition(
        self, to_state: str, *, actor: str, tool: str | None, **audit: Any
    ) -> AuditEvent:
        if to_state not in ALLOWED.get(self.state, set()):
            raise WrongStateError(f"{self.state} -> {to_state} not allowed")
        event = self._record(actor, self.state, to_state, tool=tool, **audit)
        self.state = to_state
        return event

    # --- public transitions ---------------------------------------------------

    def advance(
        self,
        to_state: str,
        *,
        actor: str = "gateway",
        tool: str | None = None,
        rules: list[dict[str, str]] | None = None,
        policy_version: str | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> AuditEvent:
        return self._transition(
            to_state, actor=actor, tool=tool, rules=rules,
            policy_version=policy_version, evidence=evidence,
        )

    def block(
        self,
        outcome: str,
        *,
        reason_codes: list[str],
        tool: str | None = None,
        actor: str = "gateway",
        rules: list[dict[str, str]] | None = None,
        policy_version: str | None = None,
    ) -> AuditEvent:
        to_state = BLOCK_STATE[outcome]
        blocked_from = self.state
        event = self._transition(
            to_state, actor=actor, tool=tool, reason_codes=reason_codes,
            rules=rules, policy_version=policy_version,
        )
        self.blocked_from = blocked_from
        return event

    def resume(self, *, actor: str = "adviser", tool: str | None = None) -> AuditEvent:
        if self.state not in (CUSTOMER_REQUIRED, REVIEW_REQUIRED):
            raise WrongStateError(f"cannot resume from {self.state}")
        if self.blocked_from is None:
            raise WrongStateError("no blocked_from recorded")
        target = self.blocked_from
        event = self._transition(target, actor=actor, tool=tool)  # resumes exactly at blocked_from
        self.blocked_from = None
        return event

    def guard_reject(
        self, *, tool: str | None, reason_codes: list[str], actor: str = "agent"
    ) -> AuditEvent:
        """Record a guard rejection: state unchanged (from_state == to_state)."""
        return self._record(actor, self.state, self.state, tool=tool, reason_codes=reason_codes)

    def to_rejected(
        self, *, actor: str = "gateway", reason_codes: list[str], tool: str | None = None,
        rules: list[dict[str, str]] | None = None, policy_version: str | None = None,
    ) -> AuditEvent:
        return self._transition(
            REJECTED, actor=actor, tool=tool, reason_codes=reason_codes,
            rules=rules, policy_version=policy_version,
        )

    def handoff(self, *, actor: str = "adviser", note: str | None = None) -> AuditEvent:
        return self._transition(ADVISED_HANDOFF, actor=actor, tool=None)

    def cancel(self, *, actor: str = "human") -> AuditEvent:
        return self._transition(CANCELLED, actor=actor, tool=None)

    def expire(self, *, actor: str = "gateway") -> AuditEvent:
        return self._transition(EXPIRED, actor=actor, tool=None)

    # --- audit -----------------------------------------------------------------

    def verify_chain(self) -> int | None:
        return verify_chain(self.events)

    def audit_chain_ok(self) -> bool:
        return self.verify_chain() is None


_counter = itertools.count(1)


def new_session_id() -> str:
    return f"ses_{next(_counter):06d}"
