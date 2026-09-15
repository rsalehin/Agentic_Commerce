"""Gateway client seam for the orchestrator.

`InProcessGatewayClient` calls the gateway in-process (demo/tests); a real MCP
client can implement the same Protocol later without touching the orchestrator.
"""

from __future__ import annotations

from typing import Any, Protocol


class GatewayClient(Protocol):
    def call(self, tool: str, payload: dict[str, Any]) -> dict[str, Any]: ...

    def htu(self, tool: str, session_id: str) -> str: ...


class InProcessGatewayClient:
    def __init__(self, service: Any) -> None:
        self._service = service

    def call(self, tool: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._service.handle(tool, payload)

    def htu(self, tool: str, session_id: str) -> str:
        return self._service.htu(tool, session_id)
