"""LLM provider abstraction (ADR-09).

The orchestrator is provider-neutral: it builds Anthropic-shaped messages and
tool specs, and each provider translates. A ScriptedProvider replays recorded
turns for network-free tests and the interview replay mode.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class ToolUse:
    id: str
    name: str
    input: dict[str, Any]


@dataclass
class LLMResponse:
    tool_uses: list[ToolUse] = field(default_factory=list)
    text: str | None = None

    @property
    def stop(self) -> bool:
        return not self.tool_uses


class LLMProvider(Protocol):
    def complete(
        self, *, system: str, messages: list[dict[str, Any]], tools: list[ToolSpec]
    ) -> LLMResponse: ...
