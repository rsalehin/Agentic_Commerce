# ADR-05: Enforcement of human-only steps

**Status:** proposed · **Date:** 2026-09-14 · **Deciders:** Abir (author), reviewed with Claude Code

## Entscheidung (what had to be decided)
How do we guarantee the agent cannot fabricate the customer's declarations?

## Betrachtete Optionen
- (a) Gateway requires a holder-key signature over the exact payload (tax declaration, contract hash)
- (b) Agent prompt instructs the model to ask the human

## Entscheidungskriterien
Regulatorik · Vertrauen/Sicherheit · Deprecation-Risiko · Kosten/Aufwand im MVP · Client-Kompatibilität (welche Agenten können es heute nutzen)

## Gewählte Option
(a). A prompt is not a control. The signature is produced on the wallet (trusted surface) after `ask_human`.

## Bewusst verworfene Optionen und was die Wahl kippen kann
(b) rejected; used only as UX layer on top of (a).

## Konsequenzen / Umsetzung
R-TAX-04, R-CTR-01; `wallet.sign` only after approval; tests with agent-forged payloads.
