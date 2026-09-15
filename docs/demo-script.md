# Demo-Skript (10 Minuten) — Agentic Commerce im Finanzvertrieb

Aufbau: **4 Min Konzept · 5 Min Live-Demo · 1 Min Trade-offs.** Sprache: Deutsch.
Fallback: **Replay-Modus** im UI-Header (bundled, ohne Netz) — siehe 0:00-Hinweis.

Vor dem Start: `.\run.ps1` (Gateway :8080, Wallet :8081, Core :8082, UI :5174).
Notfall ohne Netz: nur `cd ui; npm run dev`, im Header **Replay: Lena / Marco**.

| Min | Folie / Screen | Aussage |
|---|---|---|
| 0:00 | Titel | Wer ich bin; Ablauf (4/5/1). Hinweis: die Demo läuft auch offline (Replay-Modus). |
| 0:30 | Ist-Analyse (2 Folien) | Fünf Pflichtprüfungen (GwG, WpHG, AO/Steuer, Sanktionen, Vertrag); **Identifizierung ist der Engpass** (Branchenangaben: ~6 €, ~30 % Abbruch, 1–3 Tage). AMLR (10.07.2027) + EUDI-Wallet ändern genau diesen Schritt. |
| 2:00 | Zielbild | Kundenagent → **signiertes Mandat** → **Agent Gateway** (Regeln im Code) → **Wallet (SD-JWT/QES)** → **Partnerbank** für Eskalation. Leitsatz: „**Jede Prüfung bleibt; der Nachweis wird maschinenlesbar.**" |
| 3:30 | **Demo Lena** (Happy Path) | Anbieter **verifiziert** (Directory + gepinnter Schlüssel) → Mandat (Kunde signiert im Wallet) → Identität (PID/SD-JWT) → Steuer (**Kunde signiert**) → Angemessenheit (beratungsfrei, Klassen freigeschaltet) → Unterlagen → Vertrag (**Kunde signiert**) → **Depotnummer**. Rechts: Zustandsband + Audit-Trail mit **„Kette gültig"** und sha256-Hashes. |
| 6:00 | **Demo Marco** (Eskalation) | Zwei Eskalationen, zwei Beraterentscheidungen: (1) `TAX_FOREIGN_RESIDENCY` → Beraterin (Volksbank Leipzig, Frau Weber) **gibt frei** → Schritt abgeschlossen; (2) `COMPLEX_PRODUCT` (Bonus-Zertifikat) → **Termin vereinbart** → `ADVISED_HANDOFF`. **Kanalkonflikt als Architektur** (Channel-Felder + signierter Referral-Beleg). |
| 7:30 | **Negativfälle** | (1) Agent bestätigt ohne Kundensignatur → `CUSTOMER_REQUIRED`, kein Depot. (2) Identischer Retry (gleicher `idempotency_key`) → gleiche Depotnummer, **Anzahl = 1**. (3) Preis ändert sich nach Bestätigung → `SNAPSHOT_STALE` → erneute Bestätigung. (4) Injizierte Anweisung „ignoriere Limits" → `MANDATE_SCOPE_EXCEEDED` (rotes Audit-Event, `from==to`). (5) Validsigniertes **Lookalike** `fonds-ag.example.co` → `PROVIDER_UNVERIFIED`. |
| 8:45 | Deprecation & Nachweis | Adapter-Wechsel `IDENTITY_VERIFIER=eid_stub` (Wallet→eID) **ohne Codeänderung** — Ports & Adapter. `GET /sessions/{id}/evidence`: jede Regel → Rechtsgrundlage → Evidenz-Hash (JSON-Export). |
| 9:15 | Entscheidungslog | 4 wichtigste Trade-offs: Mandat vs. Bank-Grant (ADR-02) · API-first, MCP als Adapter (ADR-01) · Directory als Vertrauensanker (ADR-06) · Policy im Code, nicht im LLM (ADR-04). |
| 9:45 | Out of Scope + nächste Schritte | Kein echtes OpenID4VP/eID/VideoIdent, keine Zahlung/Orderausführung, keine Geeignetheitsprüfung, kein OAuth 2.1 auf MCP (dokumentiert). Nächster Schritt: FAPI-2.0-Grant, echte Wallet, Compliance-Fallmanagement. |

## Marco im Detail (zwei Beraterentscheidungen)
1. `onboarding.tax_declaration` mit DE+IT-Ansässigkeit → `TAX_FOREIGN_RESIDENCY` → `REVIEW_REQUIRED` (Beraterin). Freigabe → **schließt den Schritt ab** (→ `TAX_CONFIRMED`), keine Wiederholung derselben Regel.
2. `onboarding.appropriateness` mit Zertifikaten → `PRODUCT_OUTSIDE_UNLOCKED` + `COMPLEX_PRODUCT` → `REVIEW_REQUIRED`. Termin → `ADVISED_HANDOFF` (terminal für den Agentenkanal).

## Regie / Fallback
- Läuft das Netz nicht: Header **Replay: Lena** (Happy) und **Replay: Marco** (Eskalation) zeigen die aufgezeichneten Läufe vollständig offline — kein LLM-Aufruf, Krypto/Nachweis echt.
- Screenshots: siehe `docs/assets/README.md`.
