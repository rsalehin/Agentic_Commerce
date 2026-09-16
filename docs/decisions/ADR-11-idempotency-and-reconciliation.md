# ADR-11: Business idempotency and reconciliation instead of exactly-once

**Status:** accepted · **Date:** 2026-09-14 (P1-00) · **Deciders:** Abir (author), reviewed with Claude Code

## Entscheidung (what had to be decided)
How do we guarantee that a customer confirming once — including on a retry, a timeout, or a duplicated call — opens exactly one Depot, without pretending distributed systems are exactly-once?

## Betrachtete Optionen
- (a) **Business idempotency + reconciliation**: `operation_id` keyed create, unique constraint in the core, a `RECONCILING` state, and `get_opening_status` to resolve ambiguity
- (b) Assume exactly-once delivery
- (c) A distributed-ledger/blockchain "single source of truth"

## Entscheidungskriterien
Regulatorik · Vertrauen/Sicherheit · Deprecation-Risiko · Kosten/Aufwand im MVP · Client-Kompatibilität

## Gewählte Option
(a). `create_depot` is issued exactly once per session, keyed by `operation_id = session_id + ":create_depot"` (unique constraint in the core mock). A duplicate `confirm`/create with the same `idempotency_key`/`operation_id` returns the stored result (same Depot number, count stays one). If the core returns ambiguous/timeout (`PROVISIONING_UNCERTAIN`), the session enters `RECONCILING` and is resolved by `get_opening_status(operation_id)` — never by a second create. "Timeout ≠ failure."

## Bewusst verworfene Optionen und was die Wahl kippen kann
(b) rejected: naive and produces duplicate accounts on retries. (c) rejected: unnecessary complexity; a unique constraint + reconciliation is the standard banking pattern.

## Konsequenzen / Umsetzung
States `PROVISIONING`/`RECONCILING` in `docs/03`; `onboarding.get_opening_status` in `docs/05`; core mock unique constraint and ambiguous-result mode (P1-05); negative tests: identical `confirm` retry → one Depot; provisioning timeout → `RECONCILING` → resolved.
