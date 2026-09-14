# ADR-04: Where compliance policy lives

**Status:** proposed · **Date:** 2026-09-14 · **Deciders:** Abir (author), reviewed with Claude Code

## Entscheidung (what had to be decided)
Does an LLM judge compliance, or a deterministic engine?

## Betrachtete Optionen
- (a) Deterministic rules engine in the gateway, rules cite law
- (b) LLM judges compliance
- (c) LLM pre-filter + engine

## Entscheidungskriterien
Regulatorik · Vertrauen/Sicherheit · Deprecation-Risiko · Kosten/Aufwand im MVP · Client-Kompatibilität (welche Agenten können es heute nutzen)

## Gewählte Option
(a). Auditable, testable, explainable to BaFin; each RuleResult carries the paragraph. The LLM only extracts arguments and explains outcomes to the human.

## Bewusst verworfene Optionen und was die Wahl kippen kann
(b) rejected permanently for decisions. (c) may be added later for document understanding, never for outcomes.

## Konsequenzen / Umsetzung
`gateway/rules/rules.yaml` + `engine.py`; 100 % branch tests.
