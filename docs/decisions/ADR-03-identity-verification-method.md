# ADR-03: Identity verification method

**Status:** proposed · **Date:** 2026-09-14 · **Deciders:** Abir (author), reviewed with Claude Code

## Entscheidung (what had to be decided)
Which identification method does the 2030 flow rely on?

## Betrachtete Optionen
- (a) EUDI Wallet PID as SD-JWT VC (mocked issuer, real verification)
- (b) eID / Online-Ausweisfunktion via AusweisApp
- (c) VideoIdent provider API

## Entscheidungskriterien
Regulatorik · Vertrauen/Sicherheit · Deprecation-Risiko · Kosten/Aufwand im MVP · Client-Kompatibilität (welche Agenten können es heute nutzen)

## Gewählte Option
(a). AMLR (10.07.2027) makes eIDAS-conform means the standard; German EUDI Wallet planned 01/2027; the wallet also signs (QES), covering contract and tax declaration. Verification logic (issuer signature, key binding, nonce/aud) is real.

## Bewusst verworfene Optionen und was die Wahl kippen kann
(c) rejected: deprecated by AMLR, ~30 % abort, deepfake risk. (b) not built but kept as adapter stub; flips to (b) if the wallet rollout slips — same trust level, same port.

## Konsequenzen / Umsetzung
`IdentityVerifier` port; adapters `wallet_sdjwt` and `eid_stub`; config `IDENTITY_VERIFIER`.
