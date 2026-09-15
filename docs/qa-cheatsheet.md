# Q&A-Cheatsheet — erwartete Interviewfragen und Antworten

Kurz, mit Verweis auf ADR/Regel. Leitlinien: **Policy im Code, nicht im Prompt · echte Krypto, gemockte Parteien · jede Regel zitiert ihr Gesetz · Ports vor Adaptern.**

## Architektur & Vertrauen
**Warum ein wallet-signiertes Mandat statt eines Bank-Grants (OAuth)?**
Anbieterunabhängig, kryptografisch prüfbar, scoped (Klassen/Beträge/Datenfreigabe), ablaufend, widerrufbar; erfüllt „ohne Website-Besuch" und die EUDI-Richtung. Der Bank-Grant (FAPI 2.0, PAR/PKCE/DPoP) ist die **technische** Zugriffsschicht darunter — wir bilden sie als Client-Registrierung + Sender-Bindung (`x-sender-proof`) + Revocation ab. Mandat = **rechtliche** Autorisierung, Client/Sender = **Zugriff**. (ADR-02)

**Warum reicht die signierte Agent Card nicht?**
Ein Schlüssel von derselben Domain beweist Domain-Kontrolle (wie TLS), nicht „regulierte Depot-Vertragspartei". Vertrauensanker ist ein **verifiziertes Provider-Directory** (gepinnter Schlüssel, Rechtsträger, BaFin-ID). Ein validsigniertes Lookalike wird abgelehnt (`PROVIDER_UNVERIFIED`). (ADR-06)

**Warum MCP? Ist das nicht ein Deprecation-Risiko?**
Der kanonische Vertrag ist **REST/OpenAPI**; MCP (und A2A) sind 1:1-Adapter über dieselben Command-Handler. Ein Roh-HTTP-Request trifft dieselbe Policy und erzeugt dieselben Audit-Events wie der MCP-Aufruf (getestet). Protokoll ist Adapter, Policy nicht. (ADR-01)

**Was, wenn sich ein Standard ändert (EUDI, A2A, AP2)?**
Ports & Adapter: `IdentityVerifier`, `AgentDiscovery`, `MandateVerifier`. Demo: `IDENTITY_VERIFIER=eid_stub` tauscht Wallet↔eID **ohne Codeänderung**. Deprecation-Register führt die erwarteten Enddaten. (ADR-10)

## Compliance & Recht
**Entscheidet das LLM über Zulässigkeit?**
Nein. Ein deterministischer Regel-Engine im Gateway entscheidet; jede `RuleResult` trägt den Paragrafen. Das LLM extrahiert Argumente und spricht mit dem Menschen. (ADR-04)

**Wie verhindert ihr, dass der Agent Erklärungen fälscht?**
Steuerliche Selbstauskunft und Vertrag verlangen eine **Holder-Signatur** über die exakte Nutzlast (Wallet/QES). Ohne gültige Signatur → `CUSTOMER_REQUIRED` (`R-TAX-04`, `R-CTR-01`). Ein Prompt ist keine Kontrolle. (ADR-05)

**Sanktions-/PEP-Treffer = automatische Ablehnung?**
Nein — häufiger Fehler. Ein Listentreffer ist eine **mögliche** Übereinstimmung, die die Compliance prüft; `REJECTED` nur nach dokumentierter Entscheidung. Der Kunde sieht nur „**Ihr Antrag wird geprüft**" (`IN_REVIEW`, § 47 GwG). (R-AML-01, docs/03)

**Braucht jedes Depot eine Angemessenheitsprüfung?**
Die Pflicht knüpft an die **Dienstleistung**, nicht an das leere Depot. Wir erheben das Profil bei Eröffnung, um Produktklassen für spätere Orders freizuschalten; `service_mode` (`account_only`/`non_advised`/`advised`) macht das explizit. Beratung erfolgt nie autonom → Partnerbank. (ADR-12, R-SVC-01)

**Ist QES zwingend?**
Nein — eine Designentscheidung. Kern ist die Bestätigung eines unveränderlichen **Snapshots** plus Beleg; QES im Wallet ist unsere Umsetzung. (docs/04)

**Wer ist GwG-Verpflichtete — KVG oder Depotbank?**
Offene Frage an den Auftraggeber; im Prototyp: Depotbank führt das Depot und ist Verpflichtete, die KVG/App ist Frontend. (docs/04)

## Integrität, Nachweis, Robustheit
**Wie ist der Nachweis „maschinenlesbar"?**
Hash-verkettete Audit-Events (`prev_hash`/`hash`, `verify_chain`); `GET /sessions/{id}/evidence` bildet **jede Regel auf die Evidenz** ab, die sie erfüllt (Ergebnis, Gesetz, Evidenz-Hash) — JSON-Export für die Prüfung. Auch geblockte Versuche (`from==to`) stehen in der Kette.

**Doppelbuchung / „exactly once"?**
Business-Idempotenz statt exactly-once: `create_depot` ist per `operation_id` eindeutig (Unique-Constraint); identischer Retry → gleiche Depotnummer, Anzahl 1. Unklares Ergebnis → `RECONCILING`, aufgelöst per `get_opening_status`, nie durch zweite Anlage. (ADR-11)

**Preisänderung nach Bestätigung?**
Der signierte `snapshot_digest` wird beim Abschluss gegen den aktuellen Snapshot geprüft; Abweichung → `SNAPSHOT_STALE`, frisches Bündel, erneute Bestätigung. (R-CTR-02)

**Prompt-Injection über Produktdaten?**
Die Policy liegt im Code. Ein injiziertes „ignoriere die Mandatsgrenzen" führt zu einem Aufruf außerhalb des Mandats → `MANDATE_SCOPE_EXCEEDED` (Guard, Zustand unverändert, rot im Audit). Der Agent kann das Mandat nicht überschreiben.

**Kanalkonflikt?**
Als Daten modelliert: `origin_channel`, `servicing_partner_id`, `current_channel`, `commercial_attribution_ref` + signierter Referral-Beleg. Dieselbe Antrags-ID über Filiale/App/Agent; Provisionslogik bleibt in den Bestandssystemen. (ADR-07)

**Datenschutz / PII?**
Selektive Offenlegung (SD-JWT `_sd`): nur die im Mandat freigegebenen Claims werden präsentiert; keine PII vor verifizierter Anbieteridentität; keine PII in URLs. (docs/05)

**Was ist echt, was gemockt?**
Echt: Ed25519-JWS-Signaturen, SD-JWT-Ausstellung/Präsentation/Verifikation, Holder-Key-Bindung, Hash-Ketten, Regel-Engine. Gemockt (mit Fixtures): Wallet-Aussteller, BZSt/KiStAM, Sanktionsliste, Depotbank-Core. Nie wird eine Prüfung durch `return True` simuliert.

**Fällt im Interview das Netz aus?**
Replay-Modus im UI-Header spielt aufgezeichnete Läufe (Lena/Marco) vollständig offline ab — kein LLM-Aufruf, Krypto und Nachweis echt. (ADR-09)

## Abgrenzung
**Out of scope:** echtes OpenID4VP/DC-API, echte eID/AusweisApp, VideoIdent, Zahlungen/PSD2-SCA, Orderausführung, Geeignetheitsprüfung, OAuth 2.1 auf MCP, Mandantenfähigkeit, Produktion/Hosting. Alles bewusst dokumentiert (docs/04, Deprecation-Register).

**Zu prüfen vor der Präsentation:** AI-Act-Daten gegen die Änderung vom Juli 2026 (Art. 50; Hochrisiko-Fristen); Friktionszahlen sind Branchenangaben aus Sekundärquellen, nicht Zahlen des Auftraggebers.
