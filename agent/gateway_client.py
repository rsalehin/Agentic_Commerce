"""Gateway client seam for the orchestrator.

`InProcessGatewayClient` calls the gateway in-process (demo/tests); a real MCP
client can implement the same Protocol later without touching the orchestrator.
"""

from __future__ import annotations

from typing import Any, Protocol


class GatewayClient(Protocol):
    def call(self, tool: str, payload: dict[str, Any]) -> dict[str, Any]: ...

    def htu(self, tool: str, session_id: str) -> str: ...

    def list_open_reviews(self, session_id: str) -> list[dict[str, Any]]: ...

    def decide(self, escalation_id: str, decision: str, actor: str) -> dict[str, Any]: ...

    def cancel(self, session_id: str, sender_proof: str) -> dict[str, Any]: ...


class InProcessGatewayClient:
    def __init__(self, service: Any) -> None:
        self._service = service

    @property
    def service(self) -> Any:
        return self._service

    def call(self, tool: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._service.handle(tool, payload)

    def htu(self, tool: str, session_id: str) -> str:
        return self._service.htu(tool, session_id)

    def list_open_reviews(self, session_id: str) -> list[dict[str, Any]]:
        return [
            e
            for e in self._service.list_escalations(queue="review")
            if e["session_id"] == session_id and e["status"] == "open"
        ]

    def decide(self, escalation_id: str, decision: str, actor: str) -> dict[str, Any]:
        return self._service.decide_escalation(escalation_id, decision, actor=actor)

    def cancel(self, session_id: str, sender_proof: str) -> dict[str, Any]:
        return self._service.handle(
            "onboarding.cancel", {"session_id": session_id, "sender_proof": sender_proof}
        )
