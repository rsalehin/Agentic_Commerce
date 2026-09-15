"""Tool specs advertised to the LLM (docs/05 §3-4).

Local tools (discovery, wallet.*, ask_human) plus the gateway onboarding tools.
The orchestrator injects the mechanical transport fields (session_id,
x-sender-proof) and the crypto artifacts, so the model supplies only
human-facing data.
"""

from __future__ import annotations

from agent.llm.base import ToolSpec

_OBJ = {"type": "object"}


def _schema(**props: dict) -> dict:
    return {"type": "object", "properties": props}


TOOL_SPECS: list[ToolSpec] = [
    ToolSpec(
        "discovery.verify",
        "Verify a provider (directory + pinned key) before sending any data.",
        _schema(url={"type": "string"}),
    ),
    ToolSpec(
        "ask_human",
        "Ask the customer to decide/confirm. Set purpose=mandate|tax|contract before a signature.",
        _schema(
            question_de={"type": "string"},
            purpose={"type": "string"},
            payload=_OBJ,
        ),
    ),
    ToolSpec(
        "wallet.create_mandate",
        "Build and sign the Intent Mandate (only after the customer approved via ask_human).",
        _schema(scope=_OBJ),
    ),
    ToolSpec(
        "wallet.present_pid",
        "Create a selective PID presentation for the requested claims (nonce/aud handled).",
        _schema(requested_claims={"type": "array", "items": {"type": "string"}}),
    ),
    ToolSpec(
        "wallet.sign_tax",
        "Holder-sign the tax self-certification (after ask_human purpose=tax).",
        _schema(declaration=_OBJ),
    ),
    ToolSpec(
        "wallet.sign_contract",
        "Holder-sign the current contract snapshot (after ask_human purpose=contract).",
        _schema(),
    ),
    ToolSpec(
        "onboarding.start",
        "Start onboarding with the signed mandate.",
        _schema(mandate={"type": "string"}),
    ),
    ToolSpec(
        "onboarding.identify",
        "Submit the PID presentation and optional reference IBAN.",
        _schema(reference_account_iban={"type": "string"}),
    ),
    ToolSpec(
        "onboarding.tax_declaration",
        "Submit the signed tax self-certification.",
        _schema(declaration=_OBJ),
    ),
    ToolSpec(
        "onboarding.appropriateness",
        "Submit the knowledge & experience profile.",
        _schema(profile=_OBJ),
    ),
    ToolSpec(
        "onboarding.get_documents",
        "Request the document bundle + snapshot for the chosen plan.",
        _schema(plan=_OBJ),
    ),
    ToolSpec(
        "onboarding.sign_contract",
        "Confirm the signed snapshot to open the Depot.",
        _schema(idempotency_key={"type": "string"}),
    ),
    ToolSpec("onboarding.status", "Read the current session state.", _schema()),
]
