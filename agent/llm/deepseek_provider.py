"""DeepSeek (OpenAI-compatible) provider — interview fallback (ADR-09).

Lazily imports `openai`; kept minimal and not exercised in tests. Present to show
the provider abstraction is real (swap `AGENT_LLM_PROVIDER=deepseek`).
"""

from __future__ import annotations

import json
import os
from typing import Any

from agent.llm.base import LLMResponse, ToolSpec, ToolUse


class DeepSeekProvider:
    def __init__(self, model: str | None = None, client: Any = None) -> None:
        self._model = model or os.environ.get("AGENT_MODEL", "deepseek-chat")
        if client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:  # pragma: no cover
                raise RuntimeError("deepseek provider needs the `openai` package") from exc
            client = OpenAI(
                base_url="https://api.deepseek.com",
                api_key=os.environ.get("DEEPSEEK_API_KEY", ""),
            )
        self._client = client

    def complete(
        self, *, system: str, messages: list[dict[str, Any]], tools: list[ToolSpec]
    ) -> LLMResponse:  # pragma: no cover - untested integration
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "system", "content": system}, *_to_openai(messages)],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.input_schema,
                    },
                }
                for t in tools
            ],
        )
        choice = resp.choices[0].message
        tool_uses = [
            ToolUse(
                id=tc.id, name=tc.function.name, input=json.loads(tc.function.arguments or "{}")
            )
            for tc in (choice.tool_calls or [])
        ]
        return LLMResponse(tool_uses=tool_uses, text=choice.content)


def _to_openai(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:  # pragma: no cover
    # Minimal passthrough; a full mapping is out of scope for the MVP fallback.
    return [{"role": m["role"], "content": json.dumps(m["content"])} for m in messages]
