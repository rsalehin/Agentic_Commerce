"""HTTP gateway client: drive a running gateway over the REST surface.

Implements the same GatewayClient Protocol as the in-process client, so the
orchestrator is unchanged. `http` is any httpx.Client-compatible object (a real
client with a base_url, or a FastAPI TestClient for loopback-free tests).
"""

from __future__ import annotations

from typing import Any

from gateway.service import canonical_htu

# tool -> REST path segment (docs/05 §0). Note the sign_contract path is /confirm.
_REST_ACTION = {
    "onboarding.identify": "identify",
    "onboarding.tax_declaration": "tax",
    "onboarding.appropriateness": "appropriateness",
    "onboarding.get_documents": "documents",
    "onboarding.sign_contract": "confirm",
}


class HttpGatewayClient:
    def __init__(self, http: Any, provider_domain: str = "https://fonds-ag.example") -> None:
        self._http = http
        self._domain = provider_domain

    def htu(self, tool: str, session_id: str) -> str:
        return canonical_htu(self._domain, tool, session_id)

    def call(self, tool: str, payload: dict[str, Any]) -> dict[str, Any]:
        if tool == "onboarding.start":
            resp = self._http.post("/v1/onboarding/start", json=payload)
            return resp.json()
        sid = payload["session_id"]
        body = {k: v for k, v in payload.items() if k != "session_id"}
        if tool == "onboarding.status":
            return self._http.get(f"/v1/onboarding/{sid}").json()
        action = _REST_ACTION[tool]
        return self._http.post(f"/v1/onboarding/{sid}/{action}", json=body).json()

    def list_open_reviews(self, session_id: str) -> list[dict[str, Any]]:
        escs = self._http.get("/escalations?queue=review").json()["escalations"]
        return [e for e in escs if e["session_id"] == session_id and e["status"] == "open"]

    def decide(self, escalation_id: str, decision: str, actor: str) -> dict[str, Any]:
        resp = self._http.post(
            f"/escalations/{escalation_id}/decision", json={"decision": decision, "actor": actor}
        )
        return resp.json()

    def cancel(self, session_id: str, sender_proof: str) -> dict[str, Any]:
        resp = self._http.post(
            f"/v1/onboarding/{session_id}/cancel", json={"sender_proof": sender_proof}
        )
        return resp.json()
