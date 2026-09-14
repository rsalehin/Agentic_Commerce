# 06 — Regelkatalog (human-readable)

Generated from `gateway/rules/rules.yaml` by `uv run python -m gateway.rules.export_md` (add in P1-06). Until then, read the YAML directly.

| Id | Schritt | Rechtsgrundlage | Ergebnis | Reason code |
|---|---|---|---|---|
| R-MND-01..04 | alle / start | BGB §§ 164 ff., AMLR Art. 20(1)(i), AI Act Art. 50 | ERROR (Guard: -01 Scope, -02 Expiry) / REJECT (-03 Revoked, -04 Agent) | MANDATE_*, AGENT_UNVERIFIED |
| R-ID-01..05 | identify | GwG §§ 12, 13; AMLR Art. 22(6); BGB §§ 106 ff., §§ 164 ff. | HUMAN_REQUIRED (-01..04) / REJECT (-05) | ID_*, HOLDER_MANDATE_MISMATCH |
| R-AML-01..03 | identify | Sanktions-VO; GwG § 15 | REJECT (-01 Sanktionen) / HUMAN_REQUIRED (-02 PEP, -03 Länderrisiko) | AML_* |
| R-TAX-01..04 | tax_declaration | AO § 139b; FKAustG § 3a; FATCA | HUMAN_REQUIRED | TAX_* |
| R-WPHG-01..03 | appropriateness | WpHG § 63 Abs. 10/11, § 64 Abs. 3 | HUMAN_REQUIRED | PRODUCT_OUTSIDE_UNLOCKED, ADVICE_REQUESTED, COMPLEX_PRODUCT |
| R-CTR-01 | sign_contract | BGB §§ 312c ff.; eIDAS Art. 25 | HUMAN_REQUIRED | CONTRACT_UNSIGNED |

Unlock logic for R-WPHG-01 (engine helper `unlocked_classes(experience)`): a class is unlocked if `years >= 1 and trades_per_year >= 1` for that class, or for `etf` if `fonds` is unlocked; `zertifikate`/`derivate` require `years >= 2 and trades_per_year >= 10` and are still HUMAN_REQUIRED via R-WPHG-03 in the agent channel.
