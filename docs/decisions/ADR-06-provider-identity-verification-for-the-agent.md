# ADR-06: Provider identity verification for the agent

**Status:** proposed · **Date:** 2026-09-14 · **Deciders:** Abir (author), reviewed with Claude Code

## Entscheidung (what had to be decided)
How does the customer's agent know it talks to the real Fonds AG?

## Betrachtete Optionen
- (a) JWS-signed Agent Card with JWKS on the provider's own origin (later: eIDAS QWAC / EU trusted list)
- (b) Central agent-provider registry
- (c) TLS only

## Entscheidungskriterien
Regulatorik · Vertrauen/Sicherheit · Deprecation-Risiko · Kosten/Aufwand im MVP · Client-Kompatibilität (welche Agenten können es heute nutzen)

## Gewählte Option
(a). Works today, no central party; domain binding + key pinning in the agent; fingerprint carried in the mandate so the provider sees which card the human approved.

## Bewusst verworfene Optionen und was die Wahl kippen kann
(b) does not exist yet; add as second trust anchor when BaFin/EU provide one. (c) rejected: TLS proves the domain, not the regulated entity.

## Konsequenzen / Umsetzung
P1-01/P1-02; forged-card negative test.
