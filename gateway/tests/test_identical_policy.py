"""P1-08 invariant: a raw HTTP request and an MCP call with the same payload
produce identical policy decisions and audit events (ADR-01)."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
from fastmcp import Client

from gateway.app import create_app
from gateway.mcp_app import build_mcp
from gateway.tests.onboarding_helpers import make_service, start_payload


def _normalise(env: dict[str, Any]) -> dict[str, Any]:
    """Drop per-session/random fields so two independent runs are comparable."""
    env = {k: v for k, v in env.items() if k != "state"}
    data = dict(env.get("data") or {})
    data.pop("session_id", None)
    rc = data.get("requested_credentials")
    if isinstance(rc, dict):
        rc = dict(rc)
        rc.pop("nonce", None)
        data["requested_credentials"] = rc
    env["data"] = data
    return env


def _transitions(service: Any, session_id: str) -> list[tuple[str, str, str, tuple[str, ...]]]:
    entry = service.sessions[session_id]
    return [
        (e.from_state, e.to_state, e.actor, tuple(e.reason_codes)) for e in entry.session.events
    ]


async def test_rest_and_mcp_produce_identical_decisions_and_audit() -> None:
    svc_rest = make_service()
    svc_mcp = make_service()
    # Independently minted, identical-shaped start payloads.
    payload_rest = start_payload("lena", svc_rest)
    payload_mcp = start_payload("lena", svc_mcp)

    rest_client = TestClient(create_app(svc_rest))
    rest_env = rest_client.post("/v1/onboarding/start", json=payload_rest).json()

    mcp = build_mcp(svc_mcp)
    async with Client(mcp) as client:
        result = await client.call_tool("onboarding.start", {"payload": payload_mcp})
    mcp_env = result.data

    # Same decision (ignoring random session_id/nonce).
    assert rest_env["ok"] is True and mcp_env["ok"] is True
    assert rest_env["state"] == mcp_env["state"] == "MANDATE_VALID"
    assert rest_env["outcome"] == mcp_env["outcome"]
    assert rest_env["rules"] == mcp_env["rules"]
    assert rest_env["policy_version"] == mcp_env["policy_version"]
    assert _normalise(rest_env) == _normalise(mcp_env)

    # Same audit transition sequence.
    sid_rest = rest_env["data"]["session_id"]
    sid_mcp = mcp_env["data"]["session_id"]
    assert _transitions(svc_rest, sid_rest) == _transitions(svc_mcp, sid_mcp)


async def test_rest_and_mcp_identical_on_guard_rejection() -> None:
    # An expired-style rejection: reuse a consumed mandate so the second call is
    # rejected identically on both transports.
    svc_rest = make_service()
    svc_mcp = make_service()
    payload = start_payload("lena", svc_rest)  # same signed mandate for both

    rest_client = TestClient(create_app(svc_rest))
    rest_client.post("/v1/onboarding/start", json=payload)  # consumes jti
    rest_env = rest_client.post("/v1/onboarding/start", json=payload).json()  # replay

    mcp = build_mcp(svc_mcp)
    async with Client(mcp) as client:
        await client.call_tool("onboarding.start", {"payload": payload})  # consumes jti
        result = await client.call_tool("onboarding.start", {"payload": payload})  # replay
    mcp_env = result.data

    assert rest_env["ok"] is False and mcp_env["ok"] is False
    assert rest_env["error"]["code"] == mcp_env["error"]["code"] == "MANDATE_INVALID"
