"""Anthropic tool-use provider (real API; not exercised in tests)."""

from __future__ import annotations

import os
from typing import Any

from agent.llm.base import LLMResponse, ToolSpec, ToolUse


class AnthropicProvider:
    def __init__(
        self, model: str | None = None, client: Any = None, max_tokens: int = 1024
    ) -> None:
        self._model = model or os.environ.get("AGENT_MODEL", "claude-sonnet-5")
        self._max_tokens = max_tokens
        if client is None:
            from anthropic import Anthropic

            client = Anthropic()
        self._client = client

    def complete(
        self, *, system: str, messages: list[dict[str, Any]], tools: list[ToolSpec]
    ) -> LLMResponse:
        resp = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system,
            messages=messages,
            tools=[
                {"name": t.name, "description": t.description, "input_schema": t.input_schema}
                for t in tools
            ],
        )
        text: str | None = None
        tool_uses: list[ToolUse] = []
        for block in resp.content:
            if block.type == "text":
                text = block.text
            elif block.type == "tool_use":
                tool_uses.append(ToolUse(id=block.id, name=block.name, input=dict(block.input)))
        return LLMResponse(tool_uses=tool_uses, text=text)
