# ADR-09: LLM provider and interview fallback

**Status:** accepted · **Date:** 2026-09-14 (impl. P1-09) · **Deciders:** Abir (author), reviewed with Claude Code

## Entscheidung (what had to be decided)
Which model drives the Kundenagent and what if it fails live?

## Betrachtete Optionen
- (a) Claude tool use + DeepSeek adapter + recorded replay mode
- (b) Single provider, live only

## Entscheidungskriterien
Regulatorik · Vertrauen/Sicherheit · Deprecation-Risiko · Kosten/Aufwand im MVP · Client-Kompatibilität (welche Agenten können es heute nutzen)

## Gewählte Option
(a). Tool-use quality plus a network-independent replay for the demo.

## Bewusst verworfene Optionen und was die Wahl kippen kann
(b) rejected: single point of failure in the interview.

## Konsequenzen / Umsetzung
`agent/llm/` abstraction; `agent/replay/`; P1-13, P3-03.
