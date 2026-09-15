"""Deterministic provider that replays recorded turns (no network, no LLM).

Drives tests and the interview replay mode. Each `complete()` returns the next
recorded turn; the conversation `messages` are ignored.
"""

from __future__ import annotations

from typing import Any

from agent.llm.base import LLMResponse, ToolSpec, ToolUse


class ScriptedProvider:
    def __init__(self, turns: list[LLMResponse]) -> None:
        self._turns = list(turns)
        self._index = 0

    @classmethod
    def from_calls(cls, calls: list[tuple[str, dict[str, Any]]]) -> ScriptedProvider:
        """Build from a list of (tool_name, input) pairs, one tool call per turn."""
        turns = [
            LLMResponse(tool_uses=[ToolUse(id=f"tu_{i}", name=name, input=inp)])
            for i, (name, inp) in enumerate(calls)
        ]
        return cls(turns)

    def complete(
        self, *, system: str, messages: list[dict[str, Any]], tools: list[ToolSpec]
    ) -> LLMResponse:
        if self._index >= len(self._turns):
            return LLMResponse(text="Vorgang abgeschlossen.")
        turn = self._turns[self._index]
        self._index += 1
        return turn
