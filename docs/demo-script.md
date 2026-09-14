# Demo script (10 min, German) — draft, finalise in P3-05

| Min | Slide / screen | Say |
|---|---|---|
| 0:00 | Titel | Wer ich bin, was gleich passiert (Konzept 4 Min, Demo 5 Min, Trade-offs 1 Min) |
| 0:30 | Ist-Analyse (2 Folien) | Fünf Pflichtprüfungen; Identifizierung ist Engpass; AMLR/EUDI ändern genau diesen Schritt |
| 2:00 | Zielbild | Gateway, Mandat, Wallet, Partnerbank; „jede Prüfung bleibt, Nachweis wird maschinenlesbar“ |
| 3:30 | Demo Lena | Anbieter verifiziert → Mandat → Identität → Steuer (Kunde signiert) → Angemessenheit → Dokumente → Vertrag (QES) → Depotnummer; Audit-Trail rechts |
| 7:00 | Demo Marco | Eskalation, Beraterin entscheidet, Termin → Kanalkonflikt gelöst |

> Hinweis Marco: Der Fall erzeugt **zwei** Eskalationen mit **zwei** Beraterentscheidungen — (1) `TAX_FOREIGN_RESIDENCY` im Schritt `tax_declaration` (Beraterin gibt frei → `TAX_CONFIRMED`), dann (2) `PRODUCT_OUTSIDE_UNLOCKED` + `COMPLEX_PRODUCT` im Schritt `appropriateness` (Beraterin vereinbart Termin → `ADVISED_HANDOFF`).
| 8:30 | Manipulation | Injizierte Anweisung abgelehnt (Policy im Code); Adapter-Wechsel Wallet→eID |
| 9:15 | Entscheidungslog | ADR-Tabelle: 4 wichtigste Trade-offs |
| 9:45 | Out of scope + nächste Schritte | – |

Fallback: Replay-Modus im UI-Header.
