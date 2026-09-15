"""FastMCP transport: onboarding tools that delegate to the same GatewayService.

Every tool is a thin adapter over `service.handle(tool, payload)` — identical to
the REST layer — so both surfaces hit the same policy (ADR-01, P1-08 invariant).
"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from gateway.service import GatewayService

TOOLS = [
    "onboarding.start",
    "onboarding.identify",
    "onboarding.tax_declaration",
    "onboarding.appropriateness",
    "onboarding.get_documents",
    "onboarding.sign_contract",
    "onboarding.status",
]


def build_mcp(service: GatewayService) -> FastMCP:
    mcp: FastMCP = FastMCP("Fonds AG Agent Gateway")

    def register(tool_name: str) -> None:
        def handler(payload: dict[str, Any]) -> dict[str, Any]:
            return service.handle(tool_name, payload)

        handler.__name__ = tool_name.replace(".", "_")
        mcp.tool(name=tool_name)(handler)

    for tool in TOOLS:
        register(tool)
    return mcp
