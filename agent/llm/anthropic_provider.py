"""Anthropic tool-use provider (real API; not exercised in tests)."""

from __future__ import annotations

import os
from typing import Any

from agent.llm.base import LLMResponse, ToolSpec, ToolUse


def _api_name(name: str) -> str:
    """Map a dotted internal tool name to an API-safe one.

    The Anthropic API restricts tool names to ^[a-zA-Z0-9_-]{1,128}$, but our
    tool names are dotted (e.g. "onboarding.start"). "." -> "__" is reversible
    against our name set (no existing name contains a double underscore).
    """
    return name.replace(".", "__")


def _sanitize_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return a copy of the history with tool_use block names made API-safe.

    The orchestrator replays assistant tool_use blocks (with dotted names) into
    the history each turn; those names are validated by the API too, so they
    must match the sanitized tool declarations. tool_result blocks reference
    tool_use_id, not names, so they are left untouched. The caller's list and
    blocks are not mutated.
    """
    out: list[dict[str, Any]] = []
    for msg in messages:
        content = msg.get("content")
        if not isinstance(content, list):
            out.append(msg)
            continue
        new_content = [
            {**block, "name": _api_name(block["name"])}
            if isinstance(block, dict) and block.get("type") == "tool_use" and "name" in block
            else block
            for block in content
        ]
        out.append({**msg, "content": new_content})
    return out


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
        from_api = {_api_name(t.name): t.name for t in tools}
        resp = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system,
            messages=_sanitize_messages(messages),
            tools=[
                {
                    "name": _api_name(t.name),
                    "description": t.description,
                    "input_schema": t.input_schema,
                }
                for t in tools
            ],
        )
        text: str | None = None
        tool_uses: list[ToolUse] = []
        for block in resp.content:
            if block.type == "text":
                text = block.text
            elif block.type == "tool_use":
                # Map the model's (sanitized) tool name back to the dotted original.
                name = from_api.get(block.name, block.name)
                tool_uses.append(ToolUse(id=block.id, name=name, input=dict(block.input)))
        return LLMResponse(tool_uses=tool_uses, text=text)
