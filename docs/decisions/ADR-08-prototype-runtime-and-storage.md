# ADR-08: Prototype runtime and storage

**Status:** proposed · **Date:** 2026-09-14 · **Deciders:** Abir (author), reviewed with Claude Code

## Entscheidung (what had to be decided)
How is the prototype run and where does state live?

## Betrachtete Optionen
- (a) Local services, SQLite, run.ps1 + docker-compose
- (b) Cloud deployment

## Entscheidungskriterien
Regulatorik · Vertrauen/Sicherheit · Deprecation-Risiko · Kosten/Aufwand im MVP · Client-Kompatibilität (welche Agenten können es heute nutzen)

## Gewählte Option
(a). Zero interview-day dependencies.

## Bewusst verworfene Optionen und was die Wahl kippen kann
(b) unnecessary for the case.

## Konsequenzen / Umsetzung
P0-04.
