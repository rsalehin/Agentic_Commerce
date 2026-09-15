"""P1-08 tests: end-to-end happy path, human-only enforcement, scope guard."""

from __future__ import annotations

from gateway.service import GatewayService
from gateway.tests.onboarding_helpers import (
    declaration_for,
    holder_sign,
    make_service,
    persona,
    presentation,
    run_to_informed,
    sender,
    start_payload,
)


def _to_appropriateness_done(svc: GatewayService) -> str:
    env = svc.handle("onboarding.start", start_payload("lena", svc))
    sid = env["data"]["session_id"]
    nonce = env["data"]["requested_credentials"]["nonce"]
    svc.handle(
        "onboarding.identify",
        {
            "session_id": sid,
            "presentation": presentation("lena", nonce),
            "reference_account_iban": persona("lena")["reference_account"]["iban"],
            "sender_proof": sender(svc, "onboarding.identify", sid),
        },
    )
    decl = declaration_for("lena")
    svc.handle(
        "onboarding.tax_declaration",
        {
            "session_id": sid,
            "declaration": decl,
            "holder_signature": holder_sign("lena", sid, {"declaration": decl}),
            "sender_proof": sender(svc, "onboarding.tax_declaration", sid),
        },
    )
    svc.handle(
        "onboarding.appropriateness",
        {
            "session_id": sid,
            "profile": {
                "experience": persona("lena")["experience"],
                "education": "Abitur",
                "occupation": "Angestellte",
                "requested_classes": ["fonds", "etf"],
                "advice_requested": False,
            },
            "sender_proof": sender(svc, "onboarding.appropriateness", sid),
        },
    )
    return str(sid)


def test_happy_path_lena_reaches_depot_opened() -> None:
    svc = make_service()
    sid, digest = run_to_informed(svc, "lena")
    env = svc.handle(
        "onboarding.sign_contract",
        {
            "session_id": sid,
            "snapshot_digest": digest,
            "holder_signature": holder_sign("lena", sid, {"snapshot_digest": digest}),
            "idempotency_key": "k1",
            "qes_mock": True,
            "sender_proof": sender(svc, "onboarding.sign_contract", sid),
        },
    )
    assert env["ok"] is True
    assert env["state"] == "DEPOT_OPENED"
    assert len(env["data"]["depot"]["depot_number"]) == 10

    status = svc.handle("onboarding.status", {"session_id": sid})
    assert status["data"]["audit_chain_ok"] is True
    assert status["data"]["service_mode"] == "non_advised"


def test_sign_contract_without_holder_signature_is_customer_required() -> None:
    svc = make_service()
    sid, digest = run_to_informed(svc, "lena")
    env = svc.handle(
        "onboarding.sign_contract",
        {
            "session_id": sid,
            "snapshot_digest": digest,
            "holder_signature": None,
            "qes_mock": True,
            "sender_proof": sender(svc, "onboarding.sign_contract", sid),
        },
    )
    assert env["human_required"] is True
    assert env["state"] == "CUSTOMER_REQUIRED"
    assert env["reason_codes"] == ["CONTRACT_UNSIGNED"]


def test_tax_without_holder_signature_is_customer_required() -> None:
    svc = make_service()
    sid = _start_and_identify(svc)
    decl = declaration_for("lena")
    env = svc.handle(
        "onboarding.tax_declaration",
        {
            "session_id": sid,
            "declaration": decl,
            "holder_signature": None,
            "sender_proof": sender(svc, "onboarding.tax_declaration", sid),
        },
    )
    assert env["human_required"] is True
    assert env["reason_codes"] == ["TAX_DECLARATION_UNSIGNED"]


def test_over_limit_plan_is_scope_guard_error_state_unchanged() -> None:
    svc = make_service()
    sid = _to_appropriateness_done(svc)
    env = svc.handle(
        "onboarding.get_documents",
        {
            "session_id": sid,
            "plan": {
                "monthly_amount": {"value": 1000, "currency": "EUR"},
                "product_isin": "DE000MOCK0001",
            },
            "sender_proof": sender(svc, "onboarding.get_documents", sid),
        },
    )
    assert env["ok"] is False
    assert env["error"]["code"] == "MANDATE_SCOPE_EXCEEDED"
    assert env["state"] == "APPROPRIATENESS_DONE"  # unchanged (guard)
    status = svc.handle("onboarding.status", {"session_id": sid})
    assert status["data"]["audit_chain_ok"] is True


def _start_and_identify(svc: GatewayService) -> str:
    env = svc.handle("onboarding.start", start_payload("lena", svc))
    sid = env["data"]["session_id"]
    nonce = env["data"]["requested_credentials"]["nonce"]
    svc.handle(
        "onboarding.identify",
        {
            "session_id": sid,
            "presentation": presentation("lena", nonce),
            "reference_account_iban": persona("lena")["reference_account"]["iban"],
            "sender_proof": sender(svc, "onboarding.identify", sid),
        },
    )
    return str(sid)
