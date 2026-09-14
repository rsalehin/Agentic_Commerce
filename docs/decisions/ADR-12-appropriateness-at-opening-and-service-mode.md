# ADR-12: Appropriateness at opening and `service_mode`

**Status:** accepted · **Date:** 2026-09-14 (P1-00) · **Deciders:** Abir (author), reviewed with Claude Code

## Entscheidung (what had to be decided)
Do we run the Angemessenheitsprüfung at Depot opening, given the dossier's point that "every Depot requires a suitability assessment" is a claim to avoid?

## Betrachtete Optionen
- (a) **Collect the profile at opening to unlock product classes for later orders, and record `service_mode`** so the classification is explicit; the duty attaches to the *service*, not to the empty Depot
- (b) Account-only: no appropriateness at opening at all (dossier's strict reading)
- (c) Treat appropriateness as mandatory for the Depot itself

## Entscheidungskriterien
Regulatorik · Vertrauen/Sicherheit · Deprecation-Risiko · Kosten/Aufwand im MVP · Client-Kompatibilität

## Gewählte Option
(a). This matches what German brokers actually do (collect Kenntnisse/Erfahrungen at opening to unlock classes) while staying legally precise: `onboarding.appropriateness` returns `service_mode` — `account_only` (no requested classes → appropriateness `NOT_REQUIRED`, reason recorded), `non_advised` (requested classes present, the MVP default), `advised` (never autonomous → `REQUIRE_REVIEW` via `R-WPHG-02`). The § 63 Abs. 10 duty attaches to the securities service, not to the empty Depot; `R-SVC-01` records that. The savings-plan intent stays in the *mandate* to drive the cost information the customer sees — but no order is executed.

## Bewusst verworfene Optionen und was die Wahl kippen kann
(b) legally sharp but does not match market practice or the case's cost-information demo. (c) rejected as the exact overclaim the dossier warns against. Flips toward (b) if a regulator objects to profiling at opening.

## Konsequenzen / Umsetzung
`R-SVC-01` (informational) in `rules.yaml`; `service_mode` in `onboarding.appropriateness` output (`docs/05`); slide copy: "Profil wird bei Eröffnung erhoben, um Produktklassen für spätere Orders freizuschalten; die Pflicht knüpft an die Dienstleistung."
