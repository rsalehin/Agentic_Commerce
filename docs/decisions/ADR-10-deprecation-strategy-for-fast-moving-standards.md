# ADR-10: Deprecation strategy for fast-moving standards

**Status:** proposed · **Date:** 2026-09-14 · **Deciders:** Abir (author), reviewed with Claude Code

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
`gateway/ports/`, `docs/deprecation-register.md`, P3-02 demo.
