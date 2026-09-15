"""P1-07 tests: state machine transitions, blocking/resume, guard audit, chain."""

from __future__ import annotations

import itertools

import pytest

from gateway import state as S
from gateway.audit import verify_chain
from gateway.state import Session, WrongStateError


def _session() -> Session:
    # Deterministic monotonic clock so events are stable.
    ticks = itertools.count(1)
    return Session("ses_1", mandate_id="mnd_1", clock=lambda: f"t{next(ticks)}")


def _run_happy(sess: Session) -> None:
    sess.advance(S.MANDATE_VALID, tool="onboarding.start")
    sess.advance(S.IDENTIFIED, tool="onboarding.identify")
    sess.advance(S.SCREENED)
    sess.advance(S.TAX_CONFIRMED, tool="onboarding.tax_declaration")
    sess.advance(S.APPROPRIATENESS_DONE, tool="onboarding.appropriateness")
    sess.advance(S.INFORMED, tool="onboarding.get_documents")
    sess.advance(S.CUSTOMER_CONFIRMED, tool="onboarding.sign_contract")
    sess.advance(S.BANK_ACCEPTED)
    sess.advance(S.PROVISIONING)
    sess.advance(S.DEPOT_OPENED)


def test_happy_path_reaches_depot_opened_with_valid_chain() -> None:
    sess = _session()
    _run_happy(sess)
    assert sess.state == S.DEPOT_OPENED
    assert sess.audit_chain_ok()
    # INIT event + 10 transitions.
    assert len(sess.events) == 11
    assert sess.events[0].from_state == "INIT"
    assert sess.events[-1].to_state == S.DEPOT_OPENED


def test_illegal_transition_is_wrong_state() -> None:
    sess = _session()
    sess.advance(S.MANDATE_VALID)
    with pytest.raises(WrongStateError):
        sess.advance(S.DEPOT_OPENED)  # cannot skip


def test_block_sets_blocked_from_and_resume_returns_there() -> None:
    sess = _session()
    sess.advance(S.MANDATE_VALID)
    sess.advance(S.IDENTIFIED)
    sess.advance(S.SCREENED)
    sess.block(
        "REQUIRE_REVIEW", reason_codes=["TAX_FOREIGN_RESIDENCY"], tool="onboarding.tax_declaration"
    )
    assert sess.state == S.REVIEW_REQUIRED
    assert sess.blocked_from == S.SCREENED
    sess.resume(actor="adviser")
    assert sess.state == S.SCREENED
    assert sess.blocked_from is None
    assert sess.audit_chain_ok()


def test_customer_required_block_and_resume() -> None:
    sess = _session()
    for to in (S.MANDATE_VALID, S.IDENTIFIED, S.SCREENED, S.TAX_CONFIRMED):
        sess.advance(to)
    sess.block("REQUIRE_CUSTOMER", reason_codes=["PRODUCT_OUTSIDE_UNLOCKED"])
    assert sess.state == S.CUSTOMER_REQUIRED and sess.blocked_from == S.TAX_CONFIRMED
    sess.resume(actor="agent")
    assert sess.state == S.TAX_CONFIRMED


def test_identify_customer_required_resumes_to_mandate_valid() -> None:
    # Regression: a REQUIRE_CUSTOMER from identify blocks at MANDATE_VALID, and
    # the customer re-run must resume there (CUSTOMER_REQUIRED -> MANDATE_VALID).
    sess = _session()
    sess.advance(S.MANDATE_VALID)
    sess.block(
        "REQUIRE_CUSTOMER", reason_codes=["ID_VERIFICATION_FAILED"], tool="onboarding.identify"
    )
    assert sess.state == S.CUSTOMER_REQUIRED and sess.blocked_from == S.MANDATE_VALID
    sess.resume(actor="agent")
    assert sess.state == S.MANDATE_VALID
    assert sess.blocked_from is None
    assert sess.audit_chain_ok()


def test_guard_rejection_is_audited_from_equals_to() -> None:
    sess = _session()
    sess.advance(S.MANDATE_VALID)
    sess.advance(S.IDENTIFIED)
    before = sess.state
    event = sess.guard_reject(
        tool="onboarding.tax_declaration", reason_codes=["MANDATE_SCOPE_EXCEEDED"]
    )
    assert sess.state == before  # no state change
    assert event.from_state == event.to_state == S.IDENTIFIED
    assert event.actor == "agent"
    assert event.reason_codes == ["MANDATE_SCOPE_EXCEEDED"]
    assert sess.audit_chain_ok()


def test_reconciling_then_depot_opened() -> None:
    sess = _session()
    for to in (S.MANDATE_VALID, S.IDENTIFIED, S.SCREENED, S.TAX_CONFIRMED,
               S.APPROPRIATENESS_DONE, S.INFORMED, S.CUSTOMER_CONFIRMED, S.BANK_ACCEPTED,
               S.PROVISIONING, S.RECONCILING, S.DEPOT_OPENED):
        sess.advance(to)
    assert sess.state == S.DEPOT_OPENED
    assert sess.audit_chain_ok()


def test_review_reject_and_handoff_paths() -> None:
    reject = _session()
    reject.advance(S.MANDATE_VALID)
    reject.advance(S.IDENTIFIED)
    reject.block("REQUIRE_REVIEW", reason_codes=["AML_SANCTIONS_HIT"], tool="onboarding.identify")
    reject.to_rejected(actor="compliance", reason_codes=["REVIEW_REJECTED"])
    assert reject.state == S.REJECTED

    handoff = _session()
    for to in (S.MANDATE_VALID, S.IDENTIFIED, S.SCREENED, S.TAX_CONFIRMED):
        handoff.advance(to)
    handoff.block(
        "REQUIRE_REVIEW", reason_codes=["COMPLEX_PRODUCT"], tool="onboarding.appropriateness"
    )
    handoff.handoff(actor="adviser")
    assert handoff.state == S.ADVISED_HANDOFF
    assert reject.audit_chain_ok() and handoff.audit_chain_ok()


def test_cancel_and_expire() -> None:
    cancel = _session()
    cancel.advance(S.MANDATE_VALID)
    cancel.cancel(actor="human")
    assert cancel.state == S.CANCELLED

    expire = _session()
    expire.advance(S.MANDATE_VALID)
    expire.advance(S.IDENTIFIED)
    expire.expire()
    assert expire.state == S.EXPIRED


def test_tampering_breaks_chain() -> None:
    sess = _session()
    _run_happy(sess)
    assert sess.verify_chain() is None
    # Tamper a middle event's to_state without recomputing hashes.
    sess.events[5].to_state = S.DEPOT_OPENED
    broken = sess.verify_chain()
    assert broken == 5


def test_reordering_breaks_chain() -> None:
    sess = _session()
    _run_happy(sess)
    events = list(sess.events)
    events[3], events[4] = events[4], events[3]
    assert verify_chain(events) is not None


def test_evidence_and_policy_fields_recorded() -> None:
    sess = _session()
    sess.advance(S.MANDATE_VALID, tool="onboarding.start")
    ev = sess.advance(
        S.IDENTIFIED,
        tool="onboarding.identify",
        rules=[{"id": "R-ID-01", "outcome": "ALLOW", "law": "GwG §12"}],
        policy_version="1.1.0",
        evidence={"presentation": "abc"},
    )
    assert ev.policy_version == "1.1.0"
    assert ev.rules_version == "1.1.0"
    assert ev.evidence_hash is not None and ev.evidence_hash.startswith("sha256:")
    assert ev.mandate_id == "mnd_1"
