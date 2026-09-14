# ADR-02: Representation of the customer's authorisation (Mandat)

**Status:** accepted · **Date:** 2026-09-14 (rev. P1-00) · **Deciders:** Abir (author), reviewed with Claude Code

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
Mandate schema in docs/05 §2; `MandateVerifier` port; holder key from PID `cnf` binds mandate to identity. This binding is enforced at `onboarding.identify`: the PID key binding (`cnf`) must be the same key material as the mandate signer (`iss`), compared as `did:key(cnf) == iss` (not `kid` labels); a mismatch is `R-ID-05` → `HOLDER_MANDATE_MISMATCH`, terminal `DENY` (`IDENTIFIED --> REJECTED`), preventing an untrusted agent from presenting a third party's PID under this mandate.

## Addendum (P1-00): two layers — legal evidence vs. technical access control
The wallet-signed mandate is the customer's **legal authorisation evidence** (provider-independent, matches "ohne Website-Besuch", EUDI direction). It does **not** by itself prove *which client instance* is calling or stop a stolen mandate being replayed from another client. We therefore add a **technical access-control layer**, mirroring the dossier's bank-grant idea without building a full authorisation server:
- **Registered clients** (`fixtures/agent-clients.json`): `client_id`, operator name, instance public key, status.
- **Sender binding** (`x-sender-proof`): a DPoP-shaped JWS by the agent *instance* key over `{htm, htu, session_id, iat, jti}`; the gateway checks signature, unused `jti`, `iat` skew ≤ 60 s, and `mandate.agent.id == client_id` (`R-MND-05` `CLIENT_UNREGISTERED`, `R-MND-06` `SENDER_BINDING_INVALID`, both `ERROR` guards).
- **Revocation on writes:** every state-changing call re-checks the mandate `revocation_url` and client status (`R-MND-03` `MANDATE_REVOKED`, `DENY`).

**Production profile (not built in the MVP):** OAuth 2.0 Security BCP / FAPI 2.0 with PAR, PKCE, `private_key_jwt`/mTLS and DPoP, and a bank-issued server-side grant referencing `legal_mandate_ref` + `consent_receipt_ref`. The dossier itself mocks this; we document it as the target and implement the thin JWS version.
