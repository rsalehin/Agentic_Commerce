# ADR-01: Agent-facing interface of the provider

**Status:** proposed · **Date:** 2026-09-14 · **Deciders:** Abir (author), reviewed with Claude Code

## Entscheidung (what had to be decided)
How does a customer's agent discover and talk to the fund company's onboarding capability?

## Betrachtete Optionen
- (a) MCP tools behind a JWS-signed A2A-style Agent Card
- (b) Full A2A task server (tasks with input-required state)
- (c) Plain REST + OpenAPI + llms.txt
- (d) ACP / UCP checkout protocols

## Entscheidungskriterien
Regulatorik · Vertrauen/Sicherheit · Deprecation-Risiko · Kosten/Aufwand im MVP · Client-Kompatibilität (welche Agenten können es heute nutzen)

## Gewählte Option
(a). MCP is the broadest tool standard today (OAuth 2.1 on HTTP since 01/2026), consumable by Claude/ChatGPT/Gemini; the signed Agent Card gives discovery and domain-bound identity without a central registry. ACP/UCP are shopping-cart protocols, wrong shape for a KYC flow.

## Bewusst verworfene Optionen und was die Wahl kippen kann
(b) rejected for MVP effort; flips if A2A task semantics (long-running, input-required) become the norm for regulated onboarding. (c) rejected: no identity/discovery story. (d) rejected: no onboarding semantics.

## Konsequenzen / Umsetzung
Implement `gateway/adapters/discovery_a2a_card.py` and FastMCP tools per docs/05. Keep `AgentDiscovery` port so (b) can be added.
