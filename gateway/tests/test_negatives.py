"""P3-01: the negative-case demo backbone (idempotency, snapshot-stale, scope, lookalike)."""

from __future__ import annotations

import copy
from typing import Any

from agent.discovery import verify_card_against_directory
from gateway.card import load_card_template
from gateway.service import GatewayService
from gateway.signing import sign_card
from gateway.tests.onboarding_helpers import (
    holder_sign,
    make_service,
    run_to_informed,
    sender,
)
from wallet.keys import ensure_keys

REG = ensure_keys()


def _confirm(svc: GatewayService, sid: str, digest: str, key: str) -> dict[str, Any]:
    return svc.handle(
        "onboarding.sign_contract",
        {
            "session_id": sid,
            "snapshot_digest": digest,
            "holder_signature": holder_sign("lena", sid, {"snapshot_digest": digest}),
            "idempotency_key": key,
            "sender_proof": sender(svc, "onboarding.sign_contract", sid),
        },
    )


def test_confirm_without_signature_blocks_no_depot() -> None:
    svc = make_service()
    sid, digest = run_to_informed(svc, "lena")
    env = svc.handle(
        "onboarding.sign_contract",
        {
            "session_id": sid,
            "snapshot_digest": digest,
            "holder_signature": None,
            "sender_proof": sender(svc, "onboarding.sign_contract", sid),
        },
    )
    assert env["state"] == "CUSTOMER_REQUIRED"
    assert env["reason_codes"] == ["CONTRACT_UNSIGNED"]
    assert svc.core.depot_count() == 0


def test_idempotent_confirm_retry_same_depot_count_one() -> None:
    svc = make_service()
    sid, digest = run_to_informed(svc, "lena")
    first = _confirm(svc, sid, digest, key="k-1")
    second = _confirm(svc, sid, digest, key="k-1")  # identical replay
    assert first["state"] == second["state"] == "DEPOT_OPENED"
    assert first["data"]["depot"]["depot_number"] == second["data"]["depot"]["depot_number"]
    assert svc.core.depot_count() == 1
    # A different key after confirmation is a conflict.
    conflict = _confirm(svc, sid, digest, key="k-2")
    assert conflict["ok"] is False and conflict["error"]["code"] == "CONFLICT"


def test_fee_change_after_confirmation_requires_reconfirm() -> None:
    svc = make_service()
    sid, digest = run_to_informed(svc, "lena")

    # Price changes (p-1 -> p-2) before the customer confirms the old snapshot.
    svc.set_pricing_version("DE000MOCK0001", "p-2")
    stale = _confirm(svc, sid, digest, key="k-1")
    assert stale["state"] == "CUSTOMER_REQUIRED"
    assert stale["reason_codes"] == ["SNAPSHOT_STALE"]
    assert svc.core.depot_count() == 0
    fresh_digest = stale["data"]["snapshot_digest"]
    assert fresh_digest != digest

    # Re-confirm the fresh (p-2) snapshot -> Depot opens.
    ok = _confirm(svc, sid, fresh_digest, key="k-2")
    assert ok["state"] == "DEPOT_OPENED"
    assert svc.core.depot_count() == 1
    assert svc.sessions[sid].session.audit_chain_ok() is True


def test_over_limit_plan_scope_exceeded_audited() -> None:
    svc = make_service()
    # Reach APPROPRIATENESS_DONE, then request 10x the mandated monthly amount.
    from gateway.tests.test_service import _to_appropriateness_done

    sid = _to_appropriateness_done(svc)
    env = svc.handle(
        "onboarding.get_documents",
        {
            "session_id": sid,
            "plan": {
                "monthly_amount": {"value": 2000, "currency": "EUR"},
                "product_isin": "DE000MOCK0001",
            },
            "sender_proof": sender(svc, "onboarding.get_documents", sid),
        },
    )
    assert env["ok"] is False and env["error"]["code"] == "MANDATE_SCOPE_EXCEEDED"
    # The blocked attempt is recorded (red event, from==to).
    guard_events = [
        e for e in svc.sessions[sid].session.events if "MANDATE_SCOPE_EXCEEDED" in e.reason_codes
    ]
    assert guard_events and guard_events[-1].from_state == guard_events[-1].to_state


def test_validly_signed_lookalike_card_refused() -> None:
    lookalike = copy.deepcopy(load_card_template())
    lookalike["provider"] = {**lookalike["provider"], "url": "https://fonds-ag.example.co"}
    signed = sign_card(
        lookalike, REG.holders["lena"].private, "attacker-2026", "http://x/jwks.json"
    )
    result = verify_card_against_directory(signed)
    assert result.verified is False and result.reason == "PROVIDER_UNVERIFIED"
