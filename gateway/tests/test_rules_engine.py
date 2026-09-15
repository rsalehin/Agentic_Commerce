"""P1-06 tests: rules engine — per-rule branches, aggregation, masking, coverage."""

from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any

from gateway.rules.engine import RulesEngine

ENGINE = RulesEngine()
NOW = 1000
FP = "sha256:card"
DID = "did:key:zLENA"
AGENT = "agent:kundenagent-demo"


def kyc(
    *,
    nationalities: list[str] | None = None,
    age: int = 34,
    country: str = "DE",
    birth_place_country: str = "DE",
) -> dict[str, Any]:
    return {
        "nationalities": nationalities or ["DE"],
        "age": age,
        "address": {"country": country},
        "birth_place_country": birth_place_country,
    }


def profile(classes: list[str], advice: bool = False) -> dict[str, Any]:
    return {"requested_classes": classes, "advice_requested": advice}


def declaration(
    *, tax_id: str = "123", residencies: list[str] | None = None, us: bool = False
) -> dict[str, Any]:
    return {
        "tax_id": tax_id,
        "residencies": [{"country": c} for c in (residencies or ["DE"])],
        "us_person": us,
    }


# A context in which every rule's `when` is False (a clean pass at any step).
BASE: dict[str, Any] = {
    "now": NOW,
    "call_within_scope": True,
    "revoked_mandates": [],
    "agent_id": AGENT,
    "card_fingerprint": FP,
    "provider_card_fingerprint": FP,
    "client_id": AGENT,
    "registered_clients": [AGENT],
    "client_status": "active",
    "sender_proof_valid": True,
    "sender_proof_jti": "prf_1",
    "sender_proof_iat": NOW,
    "used_jtis": [],
    "mandate": {
        "exp": NOW + 3600,
        "jti": "mnd_1",
        "iss": DID,
        "agent": {"id": AGENT, "card_fingerprint": FP},
        "scope": {"advice_allowed": False},
    },
    "presentation": {"valid": True, "assurance_level": "high", "issuer_trust": "eidas"},
    "kyc": kyc(),
    "eu_eea": ["DE", "IT", "FR"],
    "high_risk_countries": ["KP", "IR"],
    "screening": {"sanctions": "clear", "pep": "clear"},
    "reference_account": None,
    "pid_cnf_did": DID,
    "declaration": declaration(),
    "holder_signature_valid": True,
    "profile": profile(["fonds", "etf"]),
    "unlocked_classes": ["fonds", "etf"],
    "signed_snapshot_digest": "sha256:x",
    "current_snapshot_digest": "sha256:x",
}


def ctx(**overrides: Any) -> dict[str, Any]:
    c = copy.deepcopy(BASE)
    c.update(overrides)
    return c


def _codes(step: str, **over: Any) -> tuple[str, list[str]]:
    d = ENGINE.evaluate(step, ctx(**over))
    return d.outcome, d.reason_codes


# --- clean passes -------------------------------------------------------------

def test_clean_identify_allows() -> None:
    assert ENGINE.evaluate("identify", ctx()).outcome == "ALLOW"


def test_policy_version() -> None:
    assert ENGINE.evaluate("identify", ctx()).policy_version == "1.1.0"


# --- guards (ERROR) -----------------------------------------------------------

def test_r_mnd_01_scope_guard() -> None:
    assert _codes("identify", call_within_scope=False) == ("ERROR", ["MANDATE_SCOPE_EXCEEDED"])


def test_r_mnd_02_expired_guard() -> None:
    mandate = {**BASE["mandate"], "exp": NOW - 1}
    assert _codes("identify", mandate=mandate) == ("ERROR", ["MANDATE_EXPIRED"])


def test_r_mnd_05_client_unregistered_guard() -> None:
    assert _codes("identify", client_status="blocked") == ("ERROR", ["CLIENT_UNREGISTERED"])


def test_r_mnd_06_sender_binding_guard() -> None:
    assert _codes("identify", sender_proof_valid=False) == ("ERROR", ["SENDER_BINDING_INVALID"])


def test_guard_short_circuits_over_business_rule() -> None:
    outcome, codes = _codes(
        "appropriateness", call_within_scope=False, profile=profile(["zertifikate"])
    )
    assert outcome == "ERROR" and codes == ["MANDATE_SCOPE_EXCEEDED"]


# --- DENY ---------------------------------------------------------------------

def test_r_mnd_03_revoked() -> None:
    assert _codes("identify", revoked_mandates=["mnd_1"]) == ("DENY", ["MANDATE_REVOKED"])


def test_r_mnd_04_agent_unverified_at_start() -> None:
    assert _codes("start", agent_id="") == ("DENY", ["AGENT_UNVERIFIED"])


def test_r_id_05_holder_mandate_mismatch() -> None:
    assert _codes("identify", pid_cnf_did="did:key:zOTHER") == ("DENY", ["HOLDER_MANDATE_MISMATCH"])


# --- identify REQUIRE_* -------------------------------------------------------

def test_r_id_01_verification_failed() -> None:
    presentation = {"valid": False, "assurance_level": "high", "issuer_trust": "eidas"}
    assert _codes("identify", presentation=presentation) == (
        "REQUIRE_CUSTOMER",
        ["ID_VERIFICATION_FAILED"],
    )


def test_r_id_02_non_eu_document() -> None:
    presentation = {"valid": True, "assurance_level": "high", "issuer_trust": "other"}
    outcome, codes = _codes(
        "identify", presentation=presentation, kyc=kyc(nationalities=["US"], country="US")
    )
    assert outcome == "REQUIRE_REVIEW" and "ID_NON_EU_DOCUMENT" in codes


def test_r_id_03_underage() -> None:
    assert _codes("identify", kyc=kyc(age=17)) == ("REQUIRE_REVIEW", ["ID_UNDERAGE"])


def test_r_id_04_name_mismatch() -> None:
    assert _codes("identify", reference_account={"name_match": False}) == (
        "REQUIRE_REVIEW",
        ["NAME_MISMATCH_REFERENCE_ACCOUNT"],
    )


# --- AML (confidential) -------------------------------------------------------

def test_r_aml_01_sanctions_confidential() -> None:
    d = ENGINE.evaluate("identify", ctx(screening={"sanctions": "hit", "pep": "clear"}))
    assert d.outcome == "REQUIRE_REVIEW"
    assert d.reason_codes == ["AML_SANCTIONS_HIT"]  # real, for audit
    assert d.confidential is True
    assert d.agent_reason_codes() == ["IN_REVIEW"]  # masked for the agent
    assert d.agent_message_de() == "Ihr Antrag wird geprüft."


def test_r_aml_02_pep() -> None:
    d = ENGINE.evaluate("identify", ctx(screening={"sanctions": "clear", "pep": "hit"}))
    assert d.reason_codes == ["AML_PEP_HIT"] and d.confidential is True


def test_r_aml_03_high_risk_country() -> None:
    d = ENGINE.evaluate("identify", ctx(kyc=kyc(country="KP")))
    assert d.reason_codes == ["AML_HIGH_RISK_COUNTRY"] and d.confidential is True


# --- tax ----------------------------------------------------------------------

def test_r_tax_01_missing_id() -> None:
    assert _codes("tax_declaration", declaration=declaration(tax_id="")) == (
        "REQUIRE_CUSTOMER",
        ["TAX_ID_MISSING"],
    )


def test_r_tax_02_foreign_residency() -> None:
    decl = declaration(residencies=["DE", "IT"])
    assert _codes("tax_declaration", declaration=decl) == (
        "REQUIRE_REVIEW",
        ["TAX_FOREIGN_RESIDENCY"],
    )


def test_r_tax_03_us_indicia() -> None:
    assert _codes("tax_declaration", declaration=declaration(us=True)) == (
        "REQUIRE_REVIEW",
        ["TAX_US_INDICIA"],
    )


def test_r_tax_04_unsigned() -> None:
    assert _codes("tax_declaration", holder_signature_valid=False) == (
        "REQUIRE_CUSTOMER",
        ["TAX_DECLARATION_UNSIGNED"],
    )


# --- appropriateness ----------------------------------------------------------

def test_r_svc_01_is_informational_allow() -> None:
    d = ENGINE.evaluate("appropriateness", ctx())
    assert d.outcome == "ALLOW"
    assert d.sets.get("R-SVC-01") is True


def test_r_wphg_01_product_outside_unlocked() -> None:
    assert _codes("appropriateness", profile=profile(["aktien"])) == (
        "REQUIRE_CUSTOMER",
        ["PRODUCT_OUTSIDE_UNLOCKED"],
    )


def test_r_wphg_02_advice_requested() -> None:
    assert _codes("appropriateness", profile=profile(["fonds"], advice=True)) == (
        "REQUIRE_REVIEW",
        ["ADVICE_REQUESTED"],
    )


def test_r_wphg_03_complex_product() -> None:
    outcome, codes = _codes(
        "appropriateness",
        profile=profile(["zertifikate"]),
        unlocked_classes=["fonds", "etf", "zertifikate"],
    )
    assert outcome == "REQUIRE_REVIEW" and codes == ["COMPLEX_PRODUCT"]


def test_marco_appropriateness_aggregates_to_review() -> None:
    # zertifikate not unlocked (REQUIRE_CUSTOMER) + complex (REQUIRE_REVIEW) -> REVIEW.
    d = ENGINE.evaluate("appropriateness", ctx(profile=profile(["zertifikate"])))
    assert d.outcome == "REQUIRE_REVIEW"
    assert set(d.reason_codes) == {"PRODUCT_OUTSIDE_UNLOCKED", "COMPLEX_PRODUCT"}


# --- sign_contract ------------------------------------------------------------

def test_r_ctr_01_contract_unsigned() -> None:
    assert _codes("sign_contract", holder_signature_valid=False) == (
        "REQUIRE_CUSTOMER",
        ["CONTRACT_UNSIGNED"],
    )


def test_r_ctr_02_snapshot_stale() -> None:
    assert _codes("sign_contract", signed_snapshot_digest="sha256:OLD") == (
        "REQUIRE_CUSTOMER",
        ["SNAPSHOT_STALE"],
    )


# --- acceptance ---------------------------------------------------------------

def test_reason_codes_subset_of_docs_03() -> None:
    doc = (Path(__file__).resolve().parents[2] / "docs" / "03_state-machine.md").read_text(
        encoding="utf-8"
    )
    documented = set(re.findall(r"`([A-Z][A-Z0-9_]+)`", doc))
    missing = ENGINE.reason_codes() - documented
    assert missing == set(), f"undocumented reason codes: {missing}"


def test_rule_count_and_codes() -> None:
    with_code = {r["id"] for r in ENGINE.rules if "reason_code" in r}
    assert len(ENGINE.rules) == 24
    assert len(with_code) == 23  # R-SVC-01 is informational (no reason_code)
