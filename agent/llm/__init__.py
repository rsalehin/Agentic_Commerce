"""LLM provider abstraction and factory (ADR-09)."""

from __future__ import annotations

import os
from typing import Any

from agent.llm.base import LLMProvider, LLMResponse, ToolSpec, ToolUse
from agent.llm.scripted import ScriptedProvider

__all__ = ["LLMProvider", "LLMResponse", "ToolSpec", "ToolUse", "ScriptedProvider", "get_provider"]


def get_provider(name: str | None = None, **kwargs: Any) -> LLMProvider:
    name = name or os.environ.get("AGENT_LLM_PROVIDER", "anthropic")
    if name == "anthropic":
        from agent.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider(**kwargs)
    if name == "scripted":
        return ScriptedProvider(kwargs.get("turns", []))
    if name == "deepseek":
        from agent.llm.deepseek_provider import DeepSeekProvider

        return DeepSeekProvider(**kwargs)
    raise ValueError(f"unknown LLM provider: {name}")
