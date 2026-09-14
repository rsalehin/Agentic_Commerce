# Glossar DE/EN

| Begriff | Erklärung |
|---|---|
| Depot / Wertpapierdepot | Securities account holding funds/ETFs/shares |
| KVG / Fondsgesellschaft | Kapitalverwaltungsgesellschaft — fund company / asset manager |
| Depotbank / depotführende Stelle | Custodian bank that legally holds the Depot |
| Verrechnungskonto / Referenzkonto | Settlement account at the bank / external reference IBAN |
| GwG | Geldwäschegesetz — German AML law; replaced largely by AMLR from 10.07.2027 |
| AMLR | EU Anti-Money-Laundering Regulation (EU) 2024/1624 |
| AMLA | New EU AML authority |
| Identifizierung / Legitimation | KYC identity verification |
| VideoIdent / PostIdent / eID / AutoIdent | Identification methods |
| eIDAS 2.0 / EUDI-Wallet / PID / QES | EU digital identity regulation / wallet / person identification data credential / qualified electronic signature |
| SD-JWT VC | Selective-disclosure JWT verifiable credential (wallet credential format) |
| WpHG / MiFID II / MaComp | Securities trading act / EU directive / BaFin compliance circular |
| Angemessenheitsprüfung | Appropriateness test — knowledge & experience (§ 63 Abs. 10 WpHG) |
| Geeignetheitsprüfung | Suitability test — only with advice (§ 64 Abs. 3 WpHG) |
| Execution-only | § 63 Abs. 11 WpHG — no test for non-complex products on customer initiative |
| Zielmarkt | Manufacturer-defined target market per product |
| Basisinformationsblatt (BIB/KID) / Basisinformationen / Ex-ante-Kosteninformation | Mandatory documents |
| Steuer-ID / KiStAM / BZSt / FATCA / CRS / Freistellungsauftrag | Tax ID / church-tax attribute / federal tax office / US & OECD tax reporting / tax-free allowance order |
| Fernabsatz / Widerruf | Distance selling / withdrawal right |
| PEP | Politically exposed person |
| Mandat / Intent Mandate | Signed, scoped user authorisation held by the agent |
| Agent Card | Signed machine-readable description of an agent/provider (A2A) |
| MCP | Model Context Protocol — tool interface for agents |
| Human-in-the-loop / CUSTOMER_REQUIRED / REVIEW_REQUIRED | Step where a person must act — the *customer* (declare/sign/acknowledge) vs *staff* (adviser/compliance) |
| Kanalkonflikt | Channel conflict between direct and partner-bank sales |
| service_mode | Classification of the securities service at opening: `account_only` (appropriateness NOT_REQUIRED) / `non_advised` / `advised` (§ 63 Abs. 10/11 WpHG) |
| Snapshot / snapshot_digest | Immutable revision of application + product/pricing version + document hashes that the customer confirms; a material change invalidates the confirmation |
| Referral receipt | JWS signed by the partner bank binding a referred customer/product to the application (channel attribution) |
| Sender proof (x-sender-proof) | DPoP-shaped JWS by the agent instance key binding a call to a registered client (technical access control) |
| RECONCILING | Provisioning result was ambiguous/timeout; resolved by `get_opening_status`, never by a second create |
| IN_REVIEW | Masked status shown to the agent for a confidential AML review (GwG § 47) |
