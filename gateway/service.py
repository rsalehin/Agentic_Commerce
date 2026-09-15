"""Gateway command handlers — the single policy path behind REST and MCP.

Both transports call `GatewayService.handle(tool, payload)`, so a raw HTTP request
and an MCP call with identical payloads produce identical decisions and audit
events (the P1-08 invariant, ADR-01). Signatures are verified by the P1-03/P1-04
adapters to populate the context truthfully; the rules engine (P1-06) makes every
policy decision; the state machine (P1-07) owns state and the audit chain.
"""

from __future__ import annotations

import hashlib
import secrets
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from core.db import make_engine
from core.depotbank import STATE_UNCERTAIN, DepotbankCore
from core.fixtures import provider as provider_fixture
from core.stubs import bzst_kistam, reference_account, sanctions
from gateway import appropriateness as appro
from gateway.adapters.client_registry import ClientRegistry
from gateway.adapters.mandate_jws import JwsMandateVerifier, check_agent_binding
from gateway.adapters.revocation import RevocationChecker
from gateway.adapters.wallet_sdjwt import WalletSdJwtVerifier
from gateway.canonical import jcs_canonicalize
from gateway.card import provider_fingerprint
from gateway.escalation import Escalation
from gateway.jws import JwsError, verify_compact
from gateway.models.mandate import Mandate
from gateway.rules.engine import PolicyDecision, RulesEngine
from gateway.state import (
    APPROPRIATENESS_DONE,
    BANK_ACCEPTED,
    CUSTOMER_CONFIRMED,
    DEPOT_OPENED,
    IDENTIFIED,
    INFORMED,
    MANDATE_VALID,
    PROVISIONING,
    RECONCILING,
    SCREENED,
    TAX_CONFIRMED,
    Session,
    new_session_id,
)
from wallet.keys import raw_public_from_did_key


def _sha256(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


# The tool expected next from a given (pre-step) state — the structured next-step
# handed back to the agent after a resume (P2-02).
NEXT_TOOL: dict[str, str] = {
    "MANDATE_VALID": "onboarding.identify",
    "SCREENED": "onboarding.tax_declaration",
    "TAX_CONFIRMED": "onboarding.appropriateness",
    "APPROPRIATENESS_DONE": "onboarding.get_documents",
    "INFORMED": "onboarding.sign_contract",
}


def canonical_htu(provider_domain: str, tool: str, session_id: str) -> str:
    """The canonical `htu` bound by x-sender-proof (agent and gateway must agree).

    Uses the tool's action name (e.g. `sign_contract`), independent of the REST
    path spelling (e.g. `/confirm`)."""
    if tool == "onboarding.start":
        return f"{provider_domain}/v1/onboarding/start"
    action = tool.split(".", 1)[1]
    return f"{provider_domain}/v1/onboarding/{session_id}/{action}"


@dataclass
class SessionEntry:
    session: Session
    mandate: Mandate
    holder_key: Ed25519PublicKey
    nonce: str
    kyc: dict[str, Any] | None = None
    service_mode: str | None = None
    snapshot: dict[str, Any] | None = None
    reason_codes: list[str] = field(default_factory=list)


class GatewayService:
    def __init__(
        self,
        *,
        provider_domain: str = "https://fonds-ag.example",
        rules_engine: RulesEngine | None = None,
        mandate_verifier: JwsMandateVerifier | None = None,
        client_registry: ClientRegistry | None = None,
        identity_verifier: WalletSdJwtVerifier | None = None,
        revocation: RevocationChecker | None = None,
        core: DepotbankCore | None = None,
        clock: Any = None,
    ) -> None:
        self.provider_domain = provider_domain
        self.provider_card_fingerprint = provider_fingerprint()
        self.engine = rules_engine or RulesEngine()
        self.mandate_verifier = mandate_verifier or JwsMandateVerifier()
        self.client_registry = client_registry or ClientRegistry()
        if identity_verifier is None:
            from wallet.app import issuer_jwks

            identity_verifier = WalletSdJwtVerifier(issuer_jwks())
        self.identity_verifier = identity_verifier
        self.revocation = revocation or RevocationChecker(registry=self.client_registry)
        self.core = core or DepotbankCore(make_engine())
        self._clock = clock
        self.sessions: dict[str, SessionEntry] = {}
        self.used_sender_jtis: set[str] = set()
        self._products = {p["isin"]: p for p in provider_fixture()["products"]}
        # Ops-console feed: serialized audit events across all sessions (P1-11).
        self.event_log: list[dict[str, Any]] = []
        self._published: dict[str, int] = {}
        # Escalation queues (P2-01).
        self.escalations: dict[str, Escalation] = {}

    # --- dispatch --------------------------------------------------------------

    def handle(self, tool: str, payload: dict[str, Any]) -> dict[str, Any]:
        handler = {
            "onboarding.start": self.start,
            "onboarding.identify": self.identify,
            "onboarding.tax_declaration": self.tax_declaration,
            "onboarding.appropriateness": self.appropriateness,
            "onboarding.get_documents": self.get_documents,
            "onboarding.sign_contract": self.sign_contract,
            "onboarding.status": self.status,
        }.get(tool)
        if handler is None:
            return _err("INTERNAL", detail=f"unknown tool {tool}")
        try:
            return handler(payload)
        finally:
            self._drain_events()

    # --- ops feed (P1-11) ------------------------------------------------------

    def _event_dict(self, session_id: str, event: Any) -> dict[str, Any]:
        return {
            "session_id": session_id,
            "seq": event.seq,
            "ts": event.ts,
            "actor": event.actor,
            "from_state": event.from_state,
            "to_state": event.to_state,
            "tool": event.tool,
            "reason_codes": event.reason_codes,  # real codes: Ops console (GwG §47 ok)
            "evidence_hash": event.evidence_hash,
            "hash": event.hash,
        }

    def _drain_events(self) -> None:
        for sid, entry in self.sessions.items():
            events = entry.session.events
            start = self._published.get(sid, 0)
            for event in events[start:]:
                self.event_log.append(self._event_dict(sid, event))
            self._published[sid] = len(events)

    def session_snapshot(self, session_id: str) -> dict[str, Any] | None:
        entry = self.sessions.get(session_id)
        if entry is None:
            return None
        sess = entry.session
        return {
            "session_id": session_id,
            "state": sess.state,
            "blocked_from": sess.blocked_from,
            "reason_codes": entry.reason_codes,
            "service_mode": entry.service_mode,
            "audit_chain_ok": sess.audit_chain_ok(),
            "events": [self._event_dict(session_id, e) for e in sess.events],
        }

    # --- helpers ---------------------------------------------------------------

    def _now(self) -> int:
        return int(self._clock()) if self._clock else int(time.time())

    def htu(self, tool: str, session_id: str) -> str:
        return canonical_htu(self.provider_domain, tool, session_id)

    def _mandate_ctx(self, mandate: Mandate) -> dict[str, Any]:
        return {
            "exp": mandate.exp,
            "jti": mandate.jti,
            "iss": mandate.iss,
            "agent": {"id": mandate.agent.id, "card_fingerprint": mandate.agent.card_fingerprint},
            "scope": {
                "advice_allowed": mandate.scope.advice_allowed,
                "product_classes": mandate.scope.product_classes,
            },
        }

    def _sender_ctx(
        self, tool: str, session_id: str, mandate: Mandate, proof: str | None
    ) -> dict[str, Any]:
        """Verify the sender-proof signature and return the ctx guard fields."""
        client_id = mandate.agent.id
        valid = False
        jti = ""
        iat = 0
        key = self.client_registry.instance_key(client_id)
        if proof and key is not None:
            try:
                claims = verify_compact(proof, key)
                jti = str(claims.get("jti", ""))
                iat = int(claims.get("iat", 0))
                valid = (
                    claims.get("htm") == "POST"
                    and claims.get("htu") == self.htu(tool, session_id)
                    and claims.get("session_id") == session_id
                )
            except JwsError:
                valid = False
        return {
            "client_id": client_id,
            "registered_clients": list(self.client_registry._clients),  # noqa: SLF001
            "client_status": "active" if self.client_registry.is_active(client_id) else "blocked",
            "sender_proof_valid": valid,
            "sender_proof_jti": jti,
            "sender_proof_iat": iat,
            "used_jtis": list(self.used_sender_jtis),
        }

    def _base_ctx(
        self, tool: str, session_id: str, mandate: Mandate, proof: str | None, *, within_scope: bool
    ) -> dict[str, Any]:
        now = self._now()
        ctx: dict[str, Any] = {
            "now": now,
            "call_within_scope": within_scope,
            "revoked_mandates": ["__revoked__"]
            if self.revocation.is_revoked(jti=mandate.jti)
            else [],
            "agent_id": mandate.agent.id,
            "card_fingerprint": self.provider_card_fingerprint,
            "provider_card_fingerprint": self.provider_card_fingerprint,
            "mandate": self._mandate_ctx(mandate),
        }
        ctx.update(self._sender_ctx(tool, session_id, mandate, proof))
        return ctx

    def _rules_json(self, decision: PolicyDecision) -> list[dict[str, str]]:
        return [{"id": r.id, "outcome": r.outcome, "law": r.law} for r in decision.rules]

    def _apply_non_allow(
        self, entry: SessionEntry, tool: str, decision: PolicyDecision
    ) -> dict[str, Any] | None:
        """Map a non-ALLOW decision to a transition + envelope; None if ALLOW."""
        sess = entry.session
        rules = self._rules_json(decision)
        if decision.outcome == "ERROR":
            sess.guard_reject(tool=tool, reason_codes=decision.reason_codes)
            return _err(decision.reason_codes[0], decision.message_de, state=sess.state)
        if decision.outcome == "DENY":
            sess.to_rejected(
                reason_codes=decision.reason_codes,
                tool=tool,
                rules=rules,
                policy_version=decision.policy_version,
            )
            return _err(decision.reason_codes[0], decision.message_de, state=sess.state)
        if decision.outcome in ("REQUIRE_CUSTOMER", "REQUIRE_REVIEW"):
            entry.reason_codes = decision.agent_reason_codes()
            sess.block(
                decision.outcome,
                reason_codes=decision.reason_codes,
                tool=tool,
                rules=rules,
                policy_version=decision.policy_version,
            )
            self._create_escalation(entry, decision, tool)
            return _human(sess.state, decision)
        return None

    # --- escalation queues (P2-01/P2-02) ---------------------------------------

    def _create_escalation(
        self, entry: SessionEntry, decision: PolicyDecision, tool: str
    ) -> Escalation:
        sess = entry.session
        if decision.outcome == "REQUIRE_CUSTOMER":
            queue, role = "customer", "customer"
        else:
            role = "compliance" if decision.confidential else "adviser"
            queue = "review"
        evidence = [e.evidence_hash for e in sess.events if e.evidence_hash]
        esc = Escalation(
            id=f"esc_{len(self.escalations) + 1:04d}",
            session_id=sess.session_id,
            queue=queue,
            actor_role=role,
            reasons=list(decision.reason_codes),
            blocked_from=sess.blocked_from,
            blocked_tool=tool,
            created_at=datetime.now(UTC).isoformat(),
            confidential=decision.confidential,
            evidence_hashes=evidence,
        )
        self.escalations[esc.id] = esc
        return esc

    def _next_tool_for(self, sess: Session) -> str | None:
        if sess.state == "CUSTOMER_REQUIRED" and sess.blocked_from:
            return NEXT_TOOL.get(sess.blocked_from)
        return NEXT_TOOL.get(sess.state)

    def _open_escalation(self, session_id: str) -> dict[str, Any] | None:
        for esc in self.escalations.values():
            if esc.session_id == session_id and esc.status == "open":
                return esc.to_dict()
        return None

    def list_escalations(self, queue: str | None = None) -> list[dict[str, Any]]:
        items = list(self.escalations.values())
        if queue is not None:
            items = [e for e in items if e.queue == queue]
        return [e.to_dict() for e in items]

    def get_escalation(self, escalation_id: str) -> dict[str, Any] | None:
        esc = self.escalations.get(escalation_id)
        return esc.to_dict() if esc else None

    def decide_escalation(
        self, escalation_id: str, decision: str, *, note: str | None = None, actor: str = "adviser"
    ) -> dict[str, Any]:
        esc = self.escalations.get(escalation_id)
        if esc is None:
            return _err("NOT_FOUND", detail=f"unknown escalation {escalation_id}")
        if esc.status != "open":
            return _err("WRONG_STATE", detail=f"escalation already {esc.status}")
        entry = self.sessions.get(esc.session_id)
        if entry is None:
            return _err("WRONG_STATE", detail="session gone")
        sess = entry.session
        try:
            if decision == "approve":
                sess.resume(actor=actor)
                esc.status = "approved"
            elif decision == "request_appointment":
                if esc.queue != "review":
                    return _err("WRONG_STATE", detail="appointment only for review queue")
                sess.handoff(actor=actor)
                esc.status = "appointment"
            elif decision == "reject":
                if esc.queue != "review":
                    return _err("WRONG_STATE", detail="reject only for review queue")
                sess.to_rejected(reason_codes=["REVIEW_REJECTED"], actor=actor, tool=None)
                esc.status = "rejected"
            else:
                return _err("INTERNAL", detail=f"unknown decision {decision}")
        except Exception as exc:  # noqa: BLE001 - map state errors to envelope
            return _err("WRONG_STATE", detail=str(exc))
        finally:
            self._drain_events()
        esc.note = note
        esc.decided_by = actor
        if decision == "approve":
            entry.reason_codes = []
            next_tool = self._next_tool_for(sess)
            message = "Freigabe erteilt. Bitte wiederholen Sie den Schritt."
        elif decision == "request_appointment":
            next_tool = None
            message = "Ein Termin mit Ihrer Partnerbank-Beraterin wurde vereinbart."
        else:  # reject
            next_tool = None
            message = "Der Antrag wurde nach Prüfung abgelehnt."
        return {
            "ok": True,
            "escalation": esc.to_dict(),
            "state": sess.state,
            "next_tool": next_tool,
            "message_de": message,
        }

    def _consume_sender(self, ctx: dict[str, Any]) -> None:
        jti = ctx.get("sender_proof_jti")
        if jti:
            self.used_sender_jtis.add(jti)

    def _require_session(
        self, payload: dict[str, Any]
    ) -> tuple[SessionEntry | None, dict[str, Any] | None]:
        sid = payload.get("session_id")
        entry = self.sessions.get(sid) if isinstance(sid, str) else None
        if entry is None:
            return None, _err("WRONG_STATE", detail="unknown session_id")
        return entry, None

    # --- tools -----------------------------------------------------------------

    def start(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = self._now()
        result = self.mandate_verifier.verify(
            payload.get("mandate", ""), expected_aud=self.provider_domain, now=now, consume_jti=True
        )
        if not result.ok or result.mandate is None:
            return _err(result.error_code or "MANDATE_INVALID", detail=result.detail)
        mandate = result.mandate

        holder_key = Ed25519PublicKey.from_public_bytes(raw_public_from_did_key(mandate.iss))
        sid = new_session_id()
        sess = Session(
            sid,
            mandate_id=mandate.jti,
            rules_version=self.engine.version,
            clock=self._clock and (lambda: str(self._clock())),
        )
        entry = SessionEntry(
            session=sess, mandate=mandate, holder_key=holder_key, nonce=secrets.token_urlsafe(16)
        )
        self.sessions[sid] = entry

        # R-MND-04 binding (card fingerprint + agent id).
        binding = check_agent_binding(
            mandate,
            call_card_fingerprint=payload.get("card_fingerprint", ""),
            provider_card_fingerprint=self.provider_card_fingerprint,
            call_agent_id=payload.get("agent_id", ""),
        )
        # The agent cannot know the new session_id yet, so the start proof binds "".
        ctx = self._base_ctx(
            "onboarding.start", "", mandate, payload.get("sender_proof"), within_scope=True
        )
        if binding is not None:  # override agent_id to force the engine's R-MND-04
            ctx["agent_id"] = ""
        decision = self.engine.evaluate("start", ctx)
        non_allow = self._apply_non_allow(entry, "onboarding.start", decision)
        if non_allow is not None:
            return non_allow

        self._consume_sender(ctx)
        sess.advance(
            MANDATE_VALID,
            tool="onboarding.start",
            rules=self._rules_json(decision),
            policy_version=decision.policy_version,
        )
        pid_claims = [
            c.removeprefix("pid.") for c in mandate.scope.data_release if c.startswith("pid.")
        ]
        data = {
            "session_id": sid,
            "requested_credentials": {
                "pid": pid_claims,
                "nonce": entry.nonce,
                "aud": self.provider_domain,
            },
            "terms_manifest_hash": _sha256(b"terms-manifest/v1"),
        }
        return _ok(sess.state, data, decision, next_tool="onboarding.identify")

    def identify(self, payload: dict[str, Any]) -> dict[str, Any]:
        entry, err = self._require_session(payload)
        if err:
            return err
        assert entry is not None
        sess = entry.session
        if sess.state != MANDATE_VALID:
            return _err("WRONG_STATE", detail=f"identify not allowed in {sess.state}")

        verified = self.identity_verifier.verify(
            payload.get("presentation", ""),
            nonce=entry.nonce,
            aud=self.provider_domain,
            now=self._now(),
        )
        ctx = self._base_ctx(
            "onboarding.identify",
            sess.session_id,
            entry.mandate,
            payload.get("sender_proof"),
            within_scope=True,
        )
        claims = verified.claims or {}
        screening = {"sanctions": "clear", "pep": "clear"}
        ref_ctx = None
        if verified.ok:
            screening = sanctions.screen(
                claims.get("given_name", ""),
                claims.get("family_name", ""),
                claims.get("birth_date", ""),
            )
            iban = payload.get("reference_account_iban")
            if iban:
                name = f"{claims.get('given_name', '')} {claims.get('family_name', '')}"
                ref_ctx = {"name_match": reference_account.check(iban, name)["name_match"]}
        ctx.update(
            {
                "presentation": {
                    "valid": verified.ok,
                    "assurance_level": verified.assurance_level or "none",
                    "issuer_trust": "eidas" if verified.ok else "none",
                },
                "kyc": {
                    "nationalities": claims.get("nationalities", []),
                    "age": _age(claims.get("birth_date"), self._now()),
                    "address": {"country": (claims.get("address") or {}).get("country", "")},
                    "birth_place_country": claims.get("birth_place_country", ""),
                },
                "eu_eea": provider_fixture().get("eu_eea", []) or _EU_EEA,
                "high_risk_countries": _high_risk(),
                "screening": screening,
                "reference_account": ref_ctx,
                "pid_cnf_did": verified.cnf_did or "",
            }
        )
        decision = self.engine.evaluate("identify", ctx)
        non_allow = self._apply_non_allow(entry, "onboarding.identify", decision)
        if non_allow is not None:
            return non_allow

        self._consume_sender(ctx)
        entry.kyc = claims
        rules = self._rules_json(decision)
        sess.advance(
            IDENTIFIED,
            tool="onboarding.identify",
            rules=rules,
            policy_version=decision.policy_version,
            evidence={"kyc": claims},
        )
        sess.advance(SCREENED, actor="gateway")
        return _ok(
            sess.state,
            {"kyc": claims, "screening": screening},
            decision,
            next_tool="onboarding.tax_declaration",
        )

    def tax_declaration(self, payload: dict[str, Any]) -> dict[str, Any]:
        entry, err = self._require_session(payload)
        if err:
            return err
        assert entry is not None
        sess = entry.session
        if sess.state != SCREENED:
            return _err("WRONG_STATE", detail=f"tax not allowed in {sess.state}")

        declaration = payload.get("declaration") or {}
        holder_ok = self._verify_holder_signature(
            entry,
            payload.get("holder_signature"),
            {"declaration": declaration, "session_id": sess.session_id},
        )
        ctx = self._base_ctx(
            "onboarding.tax_declaration",
            sess.session_id,
            entry.mandate,
            payload.get("sender_proof"),
            within_scope=True,
        )
        ctx.update(
            {
                "declaration": {
                    "tax_id": declaration.get("tax_id", ""),
                    "residencies": declaration.get("residencies", []),
                    "us_person": declaration.get("us_person", False),
                },
                "kyc": {
                    "nationalities": (entry.kyc or {}).get("nationalities", []),
                    "birth_place_country": (entry.kyc or {}).get("birth_place_country", ""),
                },
                "holder_signature_valid": holder_ok,
            }
        )
        decision = self.engine.evaluate("tax_declaration", ctx)
        non_allow = self._apply_non_allow(entry, "onboarding.tax_declaration", decision)
        if non_allow is not None:
            return non_allow

        self._consume_sender(ctx)
        result = bzst_kistam.lookup(declaration.get("tax_id", ""))
        sess.advance(
            TAX_CONFIRMED,
            tool="onboarding.tax_declaration",
            rules=self._rules_json(decision),
            policy_version=decision.policy_version,
            evidence={"declaration": declaration},
        )
        data = {"kistam": {"status": "queried", "result": result}, "residency_status": "DE_ONLY"}
        return _ok(sess.state, data, decision, next_tool="onboarding.appropriateness")

    def appropriateness(self, payload: dict[str, Any]) -> dict[str, Any]:
        entry, err = self._require_session(payload)
        if err:
            return err
        assert entry is not None
        sess = entry.session
        if sess.state != TAX_CONFIRMED:
            return _err("WRONG_STATE", detail=f"appropriateness not allowed in {sess.state}")

        profile = payload.get("profile") or {}
        requested = profile.get("requested_classes", [])
        unlocked = appro.unlocked_classes(profile.get("experience", {}))
        mode = appro.service_mode(requested, profile.get("advice_requested", False))
        within = all(c in entry.mandate.scope.product_classes for c in requested)
        ctx = self._base_ctx(
            "onboarding.appropriateness",
            sess.session_id,
            entry.mandate,
            payload.get("sender_proof"),
            within_scope=within,
        )
        ctx.update(
            {
                "profile": {
                    "requested_classes": requested,
                    "advice_requested": profile.get("advice_requested", False),
                },
                "unlocked_classes": unlocked,
            }
        )
        decision = self.engine.evaluate("appropriateness", ctx)
        non_allow = self._apply_non_allow(entry, "onboarding.appropriateness", decision)
        if non_allow is not None:
            entry.service_mode = mode
            return non_allow

        self._consume_sender(ctx)
        entry.service_mode = mode
        blocked = sorted(set(appro.COMPLEX) - set(unlocked))
        sess.advance(
            APPROPRIATENESS_DONE,
            tool="onboarding.appropriateness",
            rules=self._rules_json(decision),
            policy_version=decision.policy_version,
        )
        data = {
            "service_mode": mode,
            "unlocked_classes": unlocked,
            "blocked_classes": blocked,
            "warnings_de": [],
            "execution_only_notice_de": (
                "Ausführung ohne Angemessenheitsprüfung nur auf Ihre Veranlassung."
            ),
        }
        return _ok(sess.state, data, decision, next_tool="onboarding.get_documents")

    def get_documents(self, payload: dict[str, Any]) -> dict[str, Any]:
        entry, err = self._require_session(payload)
        if err:
            return err
        assert entry is not None
        sess = entry.session
        if sess.state != APPROPRIATENESS_DONE:
            return _err("WRONG_STATE", detail=f"get_documents not allowed in {sess.state}")

        plan = payload.get("plan") or {}
        isin = plan.get("product_isin", "")
        product = self._products.get(isin)
        monthly = (plan.get("monthly_amount") or {}).get("value", 0)
        within = (
            product is not None
            and product["class"] in entry.mandate.scope.product_classes
            and monthly <= entry.mandate.scope.monthly_amount_max.value
        )
        ctx = self._base_ctx(
            "onboarding.get_documents",
            sess.session_id,
            entry.mandate,
            payload.get("sender_proof"),
            within_scope=within,
        )
        decision = self.engine.evaluate("get_documents", ctx)
        non_allow = self._apply_non_allow(entry, "onboarding.get_documents", decision)
        if non_allow is not None:
            return non_allow

        self._consume_sender(ctx)
        assert product is not None
        pricing_version = product["default_pricing_version"]
        doc_types = [
            "agb",
            "basisinformationen",
            "kosteninformation_ex_ante",
            "basisinformationsblatt",
            "widerrufsbelehrung",
            "datenschutz",
        ]
        documents = [{"type": t, "hash": _sha256(f"{isin}:{t}".encode())} for t in doc_types]
        snapshot_core = {
            "session_id": sess.session_id,
            "revision": sess.revision,
            "product_id": isin,
            "product_version": product["product_version"],
            "pricing_version": pricing_version,
            "document_hashes": [d["hash"] for d in documents],
            "plan": {"monthly_amount": monthly, "product_isin": isin},
        }
        digest = _sha256(jcs_canonicalize(snapshot_core))
        entry.snapshot = {"digest": digest, **snapshot_core}
        sess.advance(
            INFORMED,
            tool="onboarding.get_documents",
            rules=self._rules_json(decision),
            policy_version=decision.policy_version,
            evidence=snapshot_core,
        )
        data = {
            "bundle_id": f"bnd_{sess.session_id}",
            "revision": sess.revision,
            "product_version": product["product_version"],
            "pricing_version": pricing_version,
            "snapshot_digest": digest,
            "documents": documents,
            "contract": {"summary_de": "Depotvertrag Fonds AG (Mock)."},
        }
        return _ok(sess.state, data, decision, next_tool="onboarding.sign_contract")

    def sign_contract(self, payload: dict[str, Any]) -> dict[str, Any]:
        entry, err = self._require_session(payload)
        if err:
            return err
        assert entry is not None
        sess = entry.session
        if sess.state != INFORMED:
            return _err("WRONG_STATE", detail=f"sign_contract not allowed in {sess.state}")
        assert entry.snapshot is not None

        signed_digest = payload.get("snapshot_digest", "")
        holder_ok = self._verify_holder_signature(
            entry,
            payload.get("holder_signature"),
            {"snapshot_digest": signed_digest, "session_id": sess.session_id},
        )
        ctx = self._base_ctx(
            "onboarding.sign_contract",
            sess.session_id,
            entry.mandate,
            payload.get("sender_proof"),
            within_scope=True,
        )
        ctx.update(
            {
                "holder_signature_valid": holder_ok,
                "signed_snapshot_digest": signed_digest,
                "current_snapshot_digest": entry.snapshot["digest"],
            }
        )
        decision = self.engine.evaluate("sign_contract", ctx)
        non_allow = self._apply_non_allow(entry, "onboarding.sign_contract", decision)
        if non_allow is not None:
            return non_allow

        self._consume_sender(ctx)
        sess.advance(
            CUSTOMER_CONFIRMED,
            tool="onboarding.sign_contract",
            rules=self._rules_json(decision),
            policy_version=decision.policy_version,
            evidence={"snapshot_digest": signed_digest},
        )
        sess.advance(BANK_ACCEPTED, actor="gateway")
        sess.advance(PROVISIONING, actor="gateway")
        operation_id = f"{sess.session_id}:create_depot"
        opening = self.core.create_depot(operation_id=operation_id, application_id=sess.session_id)
        if opening.state == STATE_UNCERTAIN or opening.depot is None:
            sess.advance(RECONCILING, actor="core")
            return _ok(
                sess.state,
                {"operation_id": operation_id},
                decision,
                next_tool="onboarding.get_opening_status",
            )
        depot = opening.depot
        sess.advance(DEPOT_OPENED, actor="core", evidence={"operation_id": operation_id})
        data = {
            "depot": {
                "depot_number": depot.depot_number,
                "verrechnungskonto_iban": depot.verrechnungskonto_iban,
                "opened_at": depot.opened_at,
                "custodian": depot.custodian,
            },
            "operation_id": operation_id,
            "withdrawal_deadline": "2026-09-29",
        }
        return _ok(sess.state, data, decision)

    def status(self, payload: dict[str, Any]) -> dict[str, Any]:
        entry, err = self._require_session(payload)
        if err:
            return err
        assert entry is not None
        sess = entry.session
        return _ok(
            sess.state,
            {
                "state": sess.state,
                "blocked_from": sess.blocked_from,
                "reason_codes": entry.reason_codes,
                "service_mode": entry.service_mode,
                "escalation": self._open_escalation(sess.session_id),
                "next_tool": self._next_tool_for(sess),
                "audit_chain_ok": sess.audit_chain_ok(),
            },
        )

    # --- holder signature (human-only steps) -----------------------------------

    def _verify_holder_signature(
        self, entry: SessionEntry, holder_signature: str | None, expected: dict[str, Any]
    ) -> bool:
        if not holder_signature:
            return False
        try:
            payload = verify_compact(holder_signature, entry.holder_key)
        except JwsError:
            return False
        if (
            payload.get("aud") != self.provider_domain
            or payload.get("session_id") != entry.session.session_id
        ):
            return False
        for key, value in expected.items():
            if payload.get(key) != value:
                return False
        return True


# --- module helpers -----------------------------------------------------------

_EU_EEA = ["DE", "IT", "FR", "AT", "NL", "ES", "PL", "BE", "SE", "IE"]


def _high_risk() -> list[str]:
    return provider_fixture().get("high_risk_countries", []) or ["KP", "IR", "MM"]


def _age(birth_date: str | None, now: int) -> int:
    if not birth_date:
        return 0
    year = int(birth_date[:4])
    return time.gmtime(now).tm_year - year


def _ok(
    state: str,
    data: dict[str, Any],
    decision: PolicyDecision | None = None,
    *,
    next_tool: str | None = None,
) -> dict[str, Any]:
    env: dict[str, Any] = {"ok": True, "state": state, "data": data, "human_required": False}
    if decision is not None:
        env["rules"] = [{"id": r.id, "outcome": r.outcome, "law": r.law} for r in decision.rules]
        env["policy_version"] = decision.policy_version
        env["outcome"] = decision.outcome
    env.setdefault("outcome", "ALLOW")
    env["reason_codes"] = []
    if next_tool:
        env["next_tool"] = next_tool
    return env


def _human(state: str, decision: PolicyDecision) -> dict[str, Any]:
    return {
        "ok": True,
        "state": state,
        "human_required": True,
        "outcome": decision.outcome,
        "reason_codes": decision.agent_reason_codes(),
        "message_de": decision.agent_message_de(),
        "policy_version": decision.policy_version,
        "rules": [{"id": r.id, "outcome": r.outcome, "law": r.law} for r in decision.rules],
    }


def _err(
    code: str, message_de: str | None = None, detail: str | None = None, *, state: str | None = None
) -> dict[str, Any]:
    env: dict[str, Any] = {
        "ok": False,
        "error": {"code": code, "message_de": message_de, "detail": detail},
    }
    if state:
        env["state"] = state
    return env
