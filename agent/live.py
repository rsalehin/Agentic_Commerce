"""Drive the orchestrator LIVE with the real Anthropic API against a running gateway.

    uv run python -m agent.live                  # lena against http://localhost:8080
    uv run python -m agent.live marco            # marco
    uv run python -m agent.live lena http://localhost:8080
    uv run python -m agent.live lena --auto      # auto-approve the customer prompts

Unlike `agent.replay`, the model makes the tool-call decisions live: this is
non-deterministic and consumes Anthropic tokens. `replay` stays the interview
fallback. Requires ANTHROPIC_API_KEY (and optionally AGENT_MODEL) in the
environment or the repo `.env`.

Start the stack first (`.\\run.ps1`), keep the UI on http://localhost:5174 with
the header on "Live"; it follows the new session as the audit events stream in.
The recorded run file supplies only the German intent text and the staff review
decisions (applied out of band, as in the Ops console); the LLM drives the rest.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import httpx
from dotenv import load_dotenv

from agent.llm.anthropic_provider import AnthropicProvider
from agent.orchestrator import Orchestrator
from agent.replay.runner import RUNS_DIR, build_http_harness, load_run


def _console_ask_human(question_de: str, payload: dict[str, Any] | None) -> dict[str, Any]:
    print(f"\n[Agent fragt] {question_de}")
    if payload:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    reply = input("Bestätigen/Signieren? [J/n] ").strip().lower()
    approved = reply in ("", "j", "ja", "y", "yes")
    return {"approved": approved, "answer": "ja" if approved else "nein"}


def main(persona: str, base_url: str, *, auto: bool) -> int:
    load_dotenv()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set. Put it in .env or the environment and retry.")
        return 2

    run = load_run(RUNS_DIR / f"{persona}.json")
    reviews = iter(run.reviews)

    with httpx.Client(base_url=base_url, timeout=30.0) as http:
        gateway, wallet, discover = build_http_harness(run.persona, http)

        def on_review(session_id: str) -> None:
            # Apply the recorded staff decisions in order (one per review), the
            # same as replay. Omit this to instead decide from the UI.
            decision = next(reviews, None)
            if decision is None:
                return
            open_reviews = gateway.list_open_reviews(session_id)
            if open_reviews:
                gateway.decide(
                    open_reviews[-1]["id"],
                    decision["decision"],
                    decision.get("actor", "adviser"),
                )

        def ask_human(question_de: str, payload: dict[str, Any] | None) -> dict[str, Any]:
            if auto:
                return dict(run.ask_human_default)
            return _console_ask_human(question_de, payload)

        orchestrator = Orchestrator(
            AnthropicProvider(),
            gateway,
            wallet,
            ask_human,
            discover=discover,
            on_review=on_review,
        )
        result = orchestrator.run(run.intent_de)

    print(f"\n[live] {persona}: session {result.session_id} -> {result.state}")
    if result.final_text:
        print(result.final_text)
    print(f"[live] expected final state: {run.expected_final_state}")
    return 0 if result.state == run.expected_final_state else 1


if __name__ == "__main__":
    argv = sys.argv[1:]
    auto = "--auto" in argv
    positional = [a for a in argv if not a.startswith("--")]
    persona = positional[0] if positional else "lena"
    base_url = (
        positional[1]
        if len(positional) > 1
        else os.environ.get("GATEWAY_URL", "http://localhost:8080")
    )
    raise SystemExit(main(persona, base_url, auto=auto))
