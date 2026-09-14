# ADR-02: Representation of the customer's authorisation (Mandat)

**Status:** proposed · **Date:** 2026-09-14 · **Deciders:** Abir (author), reviewed with Claude Code

## Entscheidung (what had to be decided)
How does the provider know what the human actually authorised the agent to do?

## Betrachtete Optionen
- (a) AP2-style signed Intent Mandate (compact JWS / VC) held by the agent, audience-bound to the provider
- (b) OAuth 2.1 scopes issued by the provider after a browser login
- (c) Free-text consent logged by the agent

## Entscheidungskriterien
Regulatorik · Vertrauen/Sicherheit · Deprecation-Risiko · Kosten/Aufwand im MVP · Client-Kompatibilität (welche Agenten können es heute nutzen)

## Gewählte Option
(a). Provider-independent, cryptographically verifiable, scoped (classes, amounts, data release), expiring and revocable; mirrors the German Mandatsmodell (BGB attribution to the user). Consume-once `jti` prevents replay.

## Bewusst verworfene Optionen und was die Wahl kippen kann
(b) rejected: requires the human to visit the provider (contradicts 'ohne Website-Besuch') and binds to one provider. (c) rejected: unverifiable. Flips if the EUDI Wallet standardises a delegation credential — then the wallet issues the mandate.

## Konsequenzen / Umsetzung
Mandate schema in docs/05 §2; `MandateVerifier` port; holder key from PID `cnf` binds mandate to identity. This binding is enforced at `onboarding.identify`: the PID key binding (`cnf`) must equal the mandate signer (`iss`); a mismatch is `R-ID-05` → reason code `HOLDER_MANDATE_MISMATCH`, terminal `REJECT` (`IDENTIFIED --> REJECTED` in docs/03), preventing an untrusted agent from presenting a third party's PID under this mandate.
