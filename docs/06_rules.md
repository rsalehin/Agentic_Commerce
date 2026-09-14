# 06 — Regelkatalog (human-readable)

Generated from `gateway/rules/rules.yaml` (version **1.1.0**) by `uv run python -m gateway.rules.export_md` (added in P1-06). Until then, read the YAML directly. Outcome vocabulary and precedence: see `docs/03_state-machine.md` (`ALLOW | ALLOW_WITH_WARNING | REQUIRE_CUSTOMER | REQUIRE_REVIEW | DENY | ERROR`).

| Id | Schritt | Rechtsgrundlage | Ergebnis | Reason code |
|---|---|---|---|---|
| R-MND-01 | alle | BGB §§ 164 ff., Mandatsmodell | ERROR (Guard: Scope) | MANDATE_SCOPE_EXCEEDED |
| R-MND-02 | alle | GwG § 10 Abs. 1 Nr. 5 | ERROR (Guard: Ablauf) | MANDATE_EXPIRED |
| R-MND-03 | alle / write | Mandatsmodell (Widerruf) | DENY | MANDATE_REVOKED |
| R-MND-04 | start | AMLR Art. 20(1)(i); AI Act Art. 50 | DENY | AGENT_UNVERIFIED |
| R-MND-05 | alle | DORA Art. 28 ff. (Client-Registrierung) | ERROR (Guard) | CLIENT_UNREGISTERED |
| R-MND-06 | alle | DORA Art. 28 ff. (Sender-Bindung) | ERROR (Guard) | SENDER_BINDING_INVALID |
| R-ID-01 | identify | GwG §§ 12, 13; AMLR Art. 22(6) | REQUIRE_CUSTOMER | ID_VERIFICATION_FAILED |
| R-ID-02 | identify | AMLR Art. 22(6); RTS Art. 7 | REQUIRE_REVIEW | ID_NON_EU_DOCUMENT |
| R-ID-03 | identify | BGB §§ 106 ff. | REQUIRE_REVIEW | ID_UNDERAGE |
| R-ID-04 | identify | GwG § 10 Abs. 1 Nr. 1 (Referenzkonto) | REQUIRE_REVIEW | NAME_MISMATCH_REFERENCE_ACCOUNT |
| R-ID-05 | identify | BGB §§ 164 ff.; Mandatsbindung (cnf == iss, did:key) | DENY | HOLDER_MANDATE_MISMATCH |
| R-AML-01 | identify | Sanktions-VO; GwG § 10, § 47 | REQUIRE_REVIEW *(vertraulich)* | AML_SANCTIONS_HIT → `IN_REVIEW` |
| R-AML-02 | identify | GwG § 15 Abs. 3 Nr. 1; § 47 | REQUIRE_REVIEW *(vertraulich)* | AML_PEP_HIT → `IN_REVIEW` |
| R-AML-03 | identify | GwG § 15 Abs. 3 Nr. 2; § 47 | REQUIRE_REVIEW *(vertraulich)* | AML_HIGH_RISK_COUNTRY → `IN_REVIEW` |
| R-TAX-01 | tax_declaration | AO § 139b; EStG § 44a | REQUIRE_CUSTOMER | TAX_ID_MISSING |
| R-TAX-02 | tax_declaration | FKAustG § 3a Abs. 2 (CRS) | REQUIRE_REVIEW | TAX_FOREIGN_RESIDENCY |
| R-TAX-03 | tax_declaration | FATCA DE/USA | REQUIRE_REVIEW | TAX_US_INDICIA |
| R-TAX-04 | tax_declaration | FKAustG § 3a Abs. 2; BGB Zurechnung | REQUIRE_CUSTOMER | TAX_DECLARATION_UNSIGNED |
| R-SVC-01 | appropriateness | WpHG § 63 Abs. 10/11 (Pflicht an der Dienstleistung) | ALLOW *(informational: sets `service_mode`)* | — |
| R-WPHG-01 | appropriateness | WpHG § 63 Abs. 10; MaComp BT 6 | REQUIRE_CUSTOMER | PRODUCT_OUTSIDE_UNLOCKED |
| R-WPHG-02 | appropriateness | WpHG § 64 Abs. 3 | REQUIRE_REVIEW | ADVICE_REQUESTED |
| R-WPHG-03 | appropriateness | WpHG § 63 Abs. 11 | REQUIRE_REVIEW | COMPLEX_PRODUCT |
| R-CTR-01 | sign_contract | BGB §§ 312c ff.; eIDAS Art. 25 | REQUIRE_CUSTOMER | CONTRACT_UNSIGNED |
| R-CTR-02 | sign_contract | BGB Vertragsschluss; Fernabsatz-Informationspflichten | REQUIRE_CUSTOMER | SNAPSHOT_STALE |

Non-rule reason codes (emitted by the core/adviser, documented in `docs/03`): `PROVISIONING_UNCERTAIN` (→ `RECONCILING`), `REVIEW_REJECTED` (DENY), `REFERRAL_INVALID` (audit note), `IN_REVIEW` (masked AML status).

**Unlock logic** for R-WPHG-01 (engine helper `unlocked_classes(experience)`): a class is unlocked if `years >= 1 and trades_per_year >= 1` for that class, or for `etf` if `fonds` is unlocked; `zertifikate`/`derivate` require `years >= 2 and trades_per_year >= 10` and are still `REQUIRE_REVIEW` via R-WPHG-03 in the agent channel.

**Service mode** (R-SVC-01): `account_only` (no requested classes → appropriateness `NOT_REQUIRED`, reason recorded), `non_advised` (requested classes present, MVP default), `advised` (never autonomous → `REQUIRE_REVIEW` via R-WPHG-02). The duty attaches to the service, not to the empty Depot.
