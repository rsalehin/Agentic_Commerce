# ADR-06: Provider identity verification for the agent (verified provider directory)

**Status:** accepted · **Date:** 2026-09-14 (rev. P1-00) · **Deciders:** Abir (author), reviewed with Claude Code

## Entscheidung (what had to be decided)
How does the customer's agent know it talks to the real Fonds AG — the regulated Depot contracting party, not just some domain?

## Betrachtete Optionen
- (a) **Signed Agent Card as the format + a verified provider directory as the trust anchor** (pinned key id, legal entity, BaFin ID, custodian per domain)
- (b) Signed Agent Card with JWKS on the card's own domain, trusted on first use
- (c) Central agent-provider registry / eIDAS QWAC only
- (d) TLS only

## Entscheidungskriterien
Regulatorik · Vertrauen/Sicherheit · Deprecation-Risiko · Kosten/Aufwand im MVP · Client-Kompatibilität

## Gewählte Option
(a). A card whose signing key is served from the same domain only proves **domain control** (like TLS) — not that the domain belongs to the regulated entity. The trust anchor must come from **outside** the card: `fixtures/provider-directory.json` maps `domain → legal entity → custodian → BaFin ID → LEI → pinned_kid`. `discovery.verify` requires the domain to be listed **and** the card signature to verify against the **pinned kid** (not the `jku` the card points to); no PII is sent before both pass. There is no trust-on-first-use — an unlisted domain is `PROVIDER_UNVERIFIED`.

## Bewusst verworfene Optionen und was die Wahl kippen kann
(b) rejected: circular (self-served key proves only domain control) and TOFU accepts lookalikes. (c) not available yet — add as a second anchor (eIDAS QWAC, partner referral, industry register) when it exists. (d) rejected. Flips toward (c) once a regulated register/QWAC is available.

## Konsequenzen / Umsetzung
`fixtures/provider-directory.json`; `agent/discovery.py` (P1-02) enforces directory + pinned-kid; negative test: a *validly signed* lookalike card for `fonds-ag.example.co` is refused (`PROVIDER_UNVERIFIED`). Forged-card (bad signature) → `CARD_SIGNATURE_INVALID`.
