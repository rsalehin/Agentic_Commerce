# ADR-07: Role of the cooperating branch bank (Kanalkonflikt)

**Status:** proposed · **Date:** 2026-09-14 · **Deciders:** Abir (author), reviewed with Claude Code

## Entscheidung (what had to be decided)
How does the agent channel coexist with partner banks?

## Betrachtete Optionen
- (a) All escalations and any advice request are routed to the partner-bank adviser
- (b) Direct-only agent channel
- (c) Agent channel only for existing partner-bank customers

## Entscheidungskriterien
Regulatorik · Vertrauen/Sicherheit · Deprecation-Risiko · Kosten/Aufwand im MVP · Client-Kompatibilität (welche Agenten können es heute nutzen)

## Gewählte Option
(a). Keeps the partner in the loop with a real, valuable function (edge cases, advice, non-wallet customers); the agent channel stays beratungsfrei.

## Bewusst verworfene Optionen und was die Wahl kippen kann
(b) rejected: creates the conflict the case warns about. (c) possible commercial variant; flips on distribution agreements.

## Konsequenzen / Umsetzung
Escalation queue + adviser panel (Phase 2); ADVISED_HANDOFF state.
