# ADR-07: Role of the cooperating branch bank (Kanalkonflikt as data)

**Status:** accepted · **Date:** 2026-09-14 (rev. P1-00) · **Deciders:** Abir (author), reviewed with Claude Code

## Entscheidung (what had to be decided)
How does the agent channel coexist with partner banks, and how is the channel relationship represented so commission/attribution is not lost?

## Betrachtete Optionen
- (a) **Channel relationship as data on the Application** (`origin_channel`, `servicing_partner_id`, `current_channel`, `commercial_attribution_ref`) + a **signed referral receipt**; advisers handle `REVIEW_REQUIRED`; commission logic stays in existing settlement systems
- (b) Process-only answer: escalations routed to a partner adviser, nothing modelled
- (c) Direct-only agent channel

## Entscheidungskriterien
Regulatorik · Vertrauen/Sicherheit · Deprecation-Risiko · Kosten/Aufwand im MVP · Client-Kompatibilität

## Gewählte Option
(a). Making the channel relationship **data** turns "Kanalkonflikt" from a process promise into an architecture answer, which is what the case grades. The same application ID continues across branch/app/agent (`current_channel` changes, `origin_channel` and attribution do not). A **referral receipt** — a JWS signed by the partner-bank key (`fixtures/keys/volksbank-leipzig`) over `{partner_id, product_id, sub, exp, jti}` — is supplied to `onboarding.start`; invalid/foreign receipts are ignored with an audit note `REFERRAL_INVALID` and never block opening. The agent channel stays beratungsfrei; `REVIEW_REQUIRED` cases go to the adviser (or compliance) queue.

## Bewusst verworfene Optionen und was die Wahl kippen kann
(b) rejected: loses attribution and auditability. (c) rejected: creates the very conflict the case warns about. Flips on concrete distribution agreements (who is attributed for an agent-originated, partner-serviced customer).

## Konsequenzen / Umsetzung
`Application` fields + referral receipt in `docs/05 §2.4`; two escalation queues (customer vs review; review split adviser/compliance) in Phase 2; `ADVISED_HANDOFF`. Commission math is out of scope (existing settlement systems).
