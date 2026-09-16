# ADR-10: Deprecation strategy for fast-moving standards

**Status:** accepted · **Date:** 2026-09-14 (demo P3-02) · **Deciders:** Abir (author), reviewed with Claude Code

## Entscheidung (what had to be decided)
How does the architecture survive changes in MCP/A2A/AP2/EUDI specs?

## Betrachtete Optionen
- (a) Ports & adapters + versioned capability manifest + deprecation register
- (b) Hard-code the current versions

## Entscheidungskriterien
Regulatorik · Vertrauen/Sicherheit · Deprecation-Risiko · Kosten/Aufwand im MVP · Client-Kompatibilität (welche Agenten können es heute nutzen)

## Gewählte Option
(a). One adapter file per standard; version negotiated from the card; register lists known end-of-life dates (VideoIdent 07/2027 etc.).

## Bewusst verworfene Optionen und was die Wahl kippen kann
(b) rejected.

## Konsequenzen / Umsetzung
`gateway/ports/`, `docs/deprecation-register.md`. **Demonstrated (P3-02):** the
`IdentityVerifier` port has two adapters — `gateway/adapters/wallet_sdjwt.py`
(EUDI SD-JWT VC) and `gateway/adapters/eid_stub.py` (eID/Online-Ausweis) — and
`IDENTITY_VERIFIER=eid_stub` swaps them via `build_identity_verifier()` with **no
gateway code change**; identify still verifies real signatures and binds the
holder to the mandate (R-ID-05). Same pattern for discovery (`AgentDiscovery`)
and the mandate/wallet standards.
