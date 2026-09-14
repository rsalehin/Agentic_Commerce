# 04 — Annahmen und Abgrenzung

## Annahmen (Assumptions)
1. Der Kunde der Fallstudie ist eine KVG in einem Bankverbund; das Depot wird bei einer verbundeigenen Depotbank geführt; die Website/App der Fondsgesellschaft ist ein Frontend, die Depotbank ist GwG-Verpflichtete.
2. Zielkunden 2030 sind in Deutschland ansässige Privatkunden mit EUDI-Wallet (Start 01/2027). Kunden ohne Wallet nutzen eID oder – als begründete Ausnahme – VideoIdent bzw. die Filiale.
3. 2030 gilt die AMLR (ab 10.07.2027); eIDAS-konforme Fernidentifizierung ist Standard, VideoIdent nur Ausnahme.
4. Agenten weisen sich über signierte Agent Cards aus und tragen ein vom Kunden signiertes Mandat. Welcher konkrete Standard sich durchsetzt, ist offen → Ports/Adapter.
5. Die Partnerbank behält Beratung und Eskalation; der Agentenkanal ist beratungsfrei (Angemessenheitsprüfung, keine Geeignetheitsprüfung).
6. Der Kundenagent läuft auf einer fremden Plattform und ist nicht vertrauenswürdig; jede Aussage wird kryptografisch geprüft.
7. Zivilrechtlich ist der Agent kein Stellvertreter; Erklärungen werden dem Kunden im Rahmen des Mandats zugerechnet. Steuerliche Selbstauskunft und Vertrag signiert der Kunde selbst (QES im Wallet).
8. Das Verrechnungskonto wird bei der Depotbank geführt; Referenzkonto per IBAN-Namensabgleich (kein echtes Open Banking im MVP).

## Bewusst außerhalb des Prototyps (Out of scope)
- Echte OpenID4VP/DC-API-Wallet-Integration, echte eID/AusweisApp, echtes VideoIdent
- Zahlungen, PSD2-SCA, Orderausführung, Sparplanausführung
- Anlageberatung / Geeignetheitsprüfung
- OAuth 2.1 auf dem MCP-Endpunkt (als „nächster Schritt“ dokumentiert)
- Mandantenfähigkeit für mehrere Partnerbanken, Produktion/Hosting, Datenschutz-Folgenabschätzung

## Offene Fragen an den Kunden (für die Präsentation)
- Welche Gesellschaft ist GwG-Verpflichtete – KVG oder Depotbank?
- Dürfen über den Agentenkanal auch Nicht-Kunden der Partnerbanken aufgenommen werden?
- Soll Beratung jemals über Agenten erfolgen?
- Welche Nationalitäten/Märkte sind im Scope?
