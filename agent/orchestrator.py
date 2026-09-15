"""Kundenagent orchestrator: a plain-Python tool-use loop (ADR-04/05/09).

The LLM extracts arguments and talks to the human; it never decides compliance
(the gateway does). Local tools produce the crypto artifacts (mandate, PID
presentation, holder signatures); the orchestrator threads them and the
mechanical transport fields (session_id, x-sender-proof, nonce, snapshot_digest)
so the model only supplies human-facing data. Signing is gated behind
`ask_human` approval (ADR-05).
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from agent import discovery
from agent.gateway_client import GatewayClient
from agent.llm.base import LLMProvider, ToolUse
from agent.sender import build_sender_proof
from agent.tool_specs import TOOL_SPECS
from wallet.holder import present_pid
from wallet.issuer import issue_pid_for_persona
from wallet.mandate import build_mandate, sign_mandate

PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "kundenagent.de.md"

GATEWAY_TOOLS = {
    "onboarding.start",
    "onboarding.identify",
    "onboarding.tax_declaration",
    "onboarding.appropriateness",
    "onboarding.get_documents",
    "onboarding.sign_contract",
    "onboarding.status",
}
TERMINAL_STATES = {"DEPOT_OPENED", "ADVISED_HANDOFF", "REJECTED", "EXPIRED", "CANCELLED"}

# ask_human callback: (question_de, payload_to_confirm) -> {"approved": bool, "answer": str}
AskHuman = Callable[[str, dict[str, Any] | None], dict[str, Any]]


@dataclass
class WalletContext:
    holder_key: Ed25519PrivateKey
    holder_kid: str
    holder_did: str
    instance_key: Ed25519PrivateKey
    instance_kid: str
    provider_domain: str
    agent_id: str
    agent_provider: str
    card_fingerprint: str
    persona: dict[str, Any]  # for PID issuance in the mock wallet


@dataclass
class RunResult:
    session_id: str | None
    state: str | None
    envelopes: list[dict[str, Any]] = field(default_factory=list)
    final_text: str | None = None


class Orchestrator:
    def __init__(
        self,
        provider: LLMProvider,
        gateway: GatewayClient,
        wallet: WalletContext,
        ask_human: AskHuman,
        *,
        max_steps: int = 40,
        now: Callable[[], int] | None = None,
        discover: Callable[[str], Any] | None = None,
        on_review: Callable[[str], None] | None = None,
    ) -> None:
        self.provider = provider
        self.gateway = gateway
        self.wallet = wallet
        self.ask_human = ask_human
        self.max_steps = max_steps
        self._now = now or (lambda: int(time.time()))
        self._discover = discover or discovery.verify
        # Called when a call lands in REVIEW_REQUIRED: staff decide out of band
        # (the Ops panel). In tests/replay this applies the adviser decision.
        self._on_review = on_review
        self.system = PROMPT_PATH.read_text(encoding="utf-8")
        # run state
        self._artifacts: dict[str, str] = {}
        self._approvals: set[str] = set()
        self._sid: str | None = None
        self._nonce: str | None = None
        self._snapshot_digest: str | None = None
        self._state: str | None = None
        self._vc: str | None = None
        # The exact tax declaration that was holder-signed, reused verbatim for the
        # gateway submit so the signature covers the submitted payload.
        self._tax_declaration: dict[str, Any] | None = None

    def run(self, intent_de: str) -> RunResult:
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": [{"type": "text", "text": intent_de}]}
        ]
        result = RunResult(session_id=None, state=None)
        for _ in range(self.max_steps):
            response = self.provider.complete(
                system=self.system, messages=messages, tools=TOOL_SPECS
            )
            if response.stop:
                result.final_text = response.text
                break
            messages.append(
                {
                    "role": "assistant",
                    "content": [
                        {"type": "tool_use", "id": tu.id, "name": tu.name, "input": tu.input}
                        for tu in response.tool_uses
                    ],
                }
            )
            tool_results = []
            for tu in response.tool_uses:
                out = self._exec(tu)
                if isinstance(out, dict) and out.get("ok") is not None:
                    result.envelopes.append(out)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tu.id,
                        "content": _as_text(out),
                    }
                )
            messages.append({"role": "user", "content": tool_results})
            if self._state in TERMINAL_STATES:
                break
        result.session_id = self._sid
        result.state = self._state
        return result

    # --- tool dispatch ---------------------------------------------------------

    def _exec(self, tu: ToolUse) -> dict[str, Any]:
        name, inp = tu.name, tu.input
        if name in GATEWAY_TOOLS:
            return self._call_gateway(name, inp)
        handler = {
            "discovery.verify": self._discovery_verify,
            "ask_human": self._ask_human,
            "wallet.create_mandate": self._create_mandate,
            "wallet.present_pid": self._present_pid,
            "wallet.sign_tax": self._sign_tax,
            "wallet.sign_contract": self._sign_contract,
        }.get(name)
        if handler is None:
            return {"error": f"unknown tool {name}"}
        return handler(inp)

    # --- customer-factual data (from the persona, like present_pid) ------------
    # The model orchestrates the sequence and handles the human approvals; the
    # customer's own facts (mandate scope, tax data, profile, plan, IBAN) come
    # from the persona the wallet holds, not from the model. Model-provided
    # values, when present, override the persona defaults.

    # Standard PID claims presented at identify (docs/05 §2); not customer secrets.
    _DEFAULT_CLAIMS = [
        "given_name",
        "family_name",
        "birth_date",
        "nationalities",
        "address",
        "birth_place_country",
        "assurance_level",
    ]

    def _persona_scope(self) -> dict[str, Any]:
        return dict(self.wallet.persona.get("mandate_scope") or {})

    def _persona_declaration(self) -> dict[str, Any]:
        persona = self.wallet.persona
        declaration = dict(persona.get("tax") or {})
        declaration.setdefault("tax_id", (persona.get("pid") or {}).get("tax_id", ""))
        return declaration

    def _persona_profile(self) -> dict[str, Any]:
        persona = self.wallet.persona
        scope = persona.get("mandate_scope") or {}
        return {
            "experience": persona.get("experience") or {},
            "education": persona.get("education", ""),
            "occupation": persona.get("occupation", ""),
            "requested_classes": list(scope.get("product_classes") or []),
            "advice_requested": bool(scope.get("advice_allowed")),
        }

    def _persona_plan(self) -> dict[str, Any]:
        plan = dict(self.wallet.persona.get("plan") or {})
        amount = plan.get("monthly_amount")
        if isinstance(amount, int | float):
            plan["monthly_amount"] = {"value": amount, "currency": "EUR"}
        return plan

    def _persona_iban(self) -> str:
        return str((self.wallet.persona.get("reference_account") or {}).get("iban", ""))

    # --- local tools -----------------------------------------------------------

    def _discovery_verify(self, inp: dict[str, Any]) -> dict[str, Any]:
        res = self._discover(inp.get("url", ""))
        return {"verified": res.verified, "reason": res.reason, "fingerprint": res.fingerprint}

    def _ask_human(self, inp: dict[str, Any]) -> dict[str, Any]:
        answer = self.ask_human(inp.get("question_de", ""), inp.get("payload"))
        if answer.get("approved") and inp.get("purpose"):
            self._approvals.add(str(inp["purpose"]))
        return answer

    def _create_mandate(self, inp: dict[str, Any]) -> dict[str, Any]:
        if "mandate" not in self._approvals:
            return {"error": "mandate not approved by the customer"}
        # Scope is the customer's authorization (persona-authoritative), not a
        # model paraphrase — the model tends to alter class tokens (e.g. "ETF").
        scope = self._persona_scope()
        payload = build_mandate(
            holder_did=self.wallet.holder_did,
            provider_domain=self.wallet.provider_domain,
            card_fingerprint=self.wallet.card_fingerprint,
            agent_id=self.wallet.agent_id,
            agent_provider=self.wallet.agent_provider,
            mandate_scope=scope,
            revocation_url="http://localhost:8081/revocations",
            now=self._now(),
        )
        self._artifacts["mandate"] = sign_mandate(
            payload, self.wallet.holder_key, self.wallet.holder_kid
        )
        return {"stored": "mandate"}

    def _present_pid(self, inp: dict[str, Any]) -> dict[str, Any]:
        if self._vc is None:
            from wallet.keys import ensure_keys

            self._vc = issue_pid_for_persona(self.wallet.persona, ensure_keys(), now=self._now())
        presentation = present_pid(
            self._vc,
            requested_claims=inp.get("requested_claims") or self._DEFAULT_CLAIMS,
            holder_key=self.wallet.holder_key,
            holder_kid=self.wallet.holder_kid,
            nonce=self._nonce or "",
            aud=self.wallet.provider_domain,
            now=self._now(),
        )
        self._artifacts["presentation"] = presentation
        return {"stored": "presentation"}

    def _sign_tax(self, inp: dict[str, Any]) -> dict[str, Any]:
        if "tax" not in self._approvals:
            return {"error": "tax declaration not approved by the customer"}
        # Sign the persona's declaration (customer fact, not model-invented) and
        # keep the exact object so the gateway submit matches what was signed.
        self._tax_declaration = self._persona_declaration()
        self._artifacts["tax_sig"] = self._holder_sign({"declaration": self._tax_declaration})
        return {"stored": "tax_sig"}

    def _sign_contract(self, inp: dict[str, Any]) -> dict[str, Any]:
        if "contract" not in self._approvals:
            return {"error": "contract not approved by the customer"}
        if not self._snapshot_digest:
            return {"error": "no snapshot to sign"}
        self._artifacts["contract_sig"] = self._holder_sign(
            {"snapshot_digest": self._snapshot_digest}
        )
        return {"stored": "contract_sig"}

    def _holder_sign(self, extra: dict[str, Any]) -> str:
        from gateway.jws import sign_compact

        payload = {"session_id": self._sid, "aud": self.wallet.provider_domain, **extra}
        return sign_compact(payload, self.wallet.holder_key, self.wallet.holder_kid)

    # --- gateway calls ---------------------------------------------------------

    def _call_gateway(self, tool: str, inp: dict[str, Any]) -> dict[str, Any]:
        payload = {k: self._resolve(v) for k, v in inp.items()}
        if tool == "onboarding.start":
            payload.setdefault("card_fingerprint", self.wallet.card_fingerprint)
            payload.setdefault("agent_id", self.wallet.agent_id)
            payload["mandate"] = self._artifacts.get("mandate", "")
            sid_for_proof = ""
        else:
            payload["session_id"] = self._sid
            sid_for_proof = self._sid or ""
            if tool == "onboarding.identify":
                # present_pid is a mechanical wallet step. Always (re)present here
                # with the live post-start nonce, so it is correct whether or not
                # the model called present_pid (and even if it called it too early).
                self._present_pid({})
                payload["presentation"] = self._artifacts.get("presentation", "")
                # Customer facts are authoritative from the persona, never the
                # model (it must not invent the customer's IBAN/tax/profile/plan).
                payload["reference_account_iban"] = self._persona_iban()
            if tool == "onboarding.tax_declaration":
                # Submit the exact declaration that was signed (persona-sourced).
                payload["declaration"] = self._tax_declaration or self._persona_declaration()
                payload["holder_signature"] = self._artifacts.get("tax_sig", "")
            if tool == "onboarding.appropriateness":
                payload["profile"] = self._persona_profile()
            if tool == "onboarding.get_documents":
                payload["plan"] = self._persona_plan()
            if tool == "onboarding.sign_contract":
                payload["holder_signature"] = self._artifacts.get("contract_sig", "")
                payload["snapshot_digest"] = self._snapshot_digest
                if not payload.get("idempotency_key"):
                    payload["idempotency_key"] = f"{self.wallet.persona['id']}-open-1"
        if tool != "onboarding.status":
            payload["sender_proof"] = build_sender_proof(
                self.wallet.instance_key,
                self.wallet.instance_kid,
                htm="POST",
                htu=self.gateway.htu(tool, sid_for_proof),
                session_id=sid_for_proof,
                now=self._now(),
                jti=f"prf_{uuid.uuid4().hex}",
            )
        env = self.gateway.call(tool, payload)
        self._absorb(tool, env)
        # Human-in-the-loop: staff review. The agent hands off and waits; the
        # adviser/compliance decision arrives out of band, then we read the new
        # state and let the loop continue from there.
        in_review = env.get("human_required") and self._state == "REVIEW_REQUIRED"
        if in_review and self._on_review and self._sid:
            self._on_review(self._sid)
            status = self.gateway.call("onboarding.status", {"session_id": self._sid})
            self._absorb("onboarding.status", status)
            # If the staff decision already resolved the review out of band, hand
            # the model the resolved status (with the next step) so it continues
            # rather than waiting; otherwise it stays blocked on the review env.
            if status.get("state") != "REVIEW_REQUIRED":
                return status
        return env

    def _absorb(self, tool: str, env: dict[str, Any]) -> None:
        data = env.get("data") or {}
        if env.get("state"):
            self._state = env["state"]
        if tool == "onboarding.start" and env.get("ok"):
            self._sid = data.get("session_id")
            self._nonce = (data.get("requested_credentials") or {}).get("nonce")
        if tool == "onboarding.get_documents" and env.get("ok"):
            self._snapshot_digest = data.get("snapshot_digest")

    def _resolve(self, value: Any) -> Any:
        if isinstance(value, str) and value.startswith("$art:"):
            return self._artifacts.get(value[len("$art:") :], "")
        return value


def _as_text(value: Any) -> str:
    import json

    return json.dumps(value, ensure_ascii=False, default=str)
