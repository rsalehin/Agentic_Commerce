# ADR-01: Agent-facing interface of the provider

**Status:** accepted · **Date:** 2026-09-14 (rev. P1-00) · **Deciders:** Abir (author), reviewed with Claude Code

## Entscheidung (what had to be decided)
How does a customer's agent discover and talk to the fund company's onboarding capability?

## Betrachtete Optionen
- (a) **API-first**: a versioned REST/OpenAPI surface is the canonical contract; MCP (and later A2A) are 1:1 adapters over the same command handlers
- (b) MCP tools as the *only* provider surface
- (c) Full A2A task server
- (d) ACP/UCP checkout protocols

## Entscheidungskriterien
Regulatorik · Vertrauen/Sicherheit · Deprecation-Risiko · Kosten/Aufwand im MVP · Client-Kompatibilität

## Gewählte Option
(a). The canonical contract is REST/OpenAPI (`/v1/onboarding/...`); FastMCP mounts the same domain command handlers as tools. Protocol is an *adapter*, policy is not: a raw HTTP request and an MCP call with identical payloads produce identical policy decisions and audit events (invariant tested in P1-08). This scores directly on the *Deprecation* criterion — a new agent protocol is one more adapter, never a policy rewrite.

## Bewusst verworfene Optionen und was die Wahl kippen kann
(b) rejected (was the earlier choice): tying policy to one transport is a deprecation risk and hides the "direct API hits the same policy" proof. (c) rejected for MVP effort; revisit if A2A task semantics become the norm. (d) rejected: shopping-cart protocols, wrong shape for KYC.

## Konsequenzen / Umsetzung
`gateway/` exposes command handlers once; REST via FastAPI and MCP via FastMCP side by side. `docs/05 §0` lists the REST↔MCP mapping. Keep the `AgentDiscovery` port for A2A later. Identical-policy test in P1-08.
