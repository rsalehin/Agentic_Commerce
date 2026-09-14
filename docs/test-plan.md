# Test plan — negative-case backlog (Phase 1–3)

Imported from the dossier's test catalogue (`docs/07_dossier-contrast.md §2.9`: T02–T08, T12–T17, T19, T22–T24), mapped to our states, rules and reason codes. Titles are inferred from the dossier themes (idempotency, replay, revision conflicts, cross-customer access, revoked grant, self-confirmation); each becomes a pytest case in the phase noted. This list is the backlog — not all are wired yet.

| T-id | Case | Expected result (our vocabulary) | Phase |
|---|---|---|---|
| T02 | Agent tries to confirm on the customer's behalf (no holder signature) | `R-CTR-01` → `CONTRACT_UNSIGNED` → `CUSTOMER_REQUIRED`; no Depot | P1-08 |
| T03 | Identical `/confirm` retry (same `idempotency_key`) | stored result returned; same Depot number; count = 1 | P1-05/08 |
| T04 | `/confirm` retry with **different** payload, same `idempotency_key` | HTTP 409 (conflict) | P1-08 |
| T05 | Pricing/product changes after confirmation | `R-CTR-02` → `SNAPSHOT_STALE` → `CUSTOMER_REQUIRED`; fresh bundle | P1-08 |
| T06 | Provisioning timeout / ambiguous core result | `PROVISIONING_UNCERTAIN` → `RECONCILING`; resolved by `get_opening_status`, never a second create | P1-05/07 |
| T07 | Duplicate `create_depot` for the same `operation_id` | one Depot; idempotent stored result | P1-05 |
| T08 | Mandate scope exceeded (over-limit / wrong class) | `R-MND-01` → `MANDATE_SCOPE_EXCEEDED` (ERROR guard); state unchanged; audited `from==to` | P1-06/08 |
| T12 | Expired mandate | `R-MND-02` → `MANDATE_EXPIRED` (ERROR guard); retryable | P1-03 |
| T13 | Revoked mandate mid-session (revocation on write) | `R-MND-03` → `MANDATE_REVOKED` (DENY) → `REJECTED` | P1-03/08 |
| T14 | Unregistered / blocked agent client | `R-MND-05` → `CLIENT_UNREGISTERED` (ERROR guard) | P1-03 |
| T15 | Sender proof invalid / replayed `jti` / stale `iat` / `agent.id≠client_id` | `R-MND-06` → `SENDER_BINDING_INVALID` (ERROR guard) | P1-03 |
| T16 | PID `cnf` ≠ mandate `iss` (third-party PID under this mandate) | `R-ID-05` → `HOLDER_MANDATE_MISMATCH` (DENY) → `REJECTED` | P1-04 |
| T17 | Wrong presentation nonce / audience | `R-ID-01` → `ID_VERIFICATION_FAILED` → `CUSTOMER_REQUIRED` | P1-04 |
| T19 | Sanctions/PEP list correspondence | `R-AML-01/02` → `REQUIRE_REVIEW`; agent sees only `IN_REVIEW`; `REJECTED` only after compliance `REVIEW_REJECTED` | P1-06 / P2-01 |
| T22 | Cross-customer access (session/mandate for another `sub`) | rejected; no data leak; audited | P1-07/08 |
| T23 | Validly-signed **lookalike** domain card (`fonds-ag.example.co`) | discovery refuses: `PROVIDER_UNVERIFIED` (domain not in directory) | P1-02 |
| T24 | Forged card (bad signature) / wrong pinned kid | discovery refuses: `CARD_SIGNATURE_INVALID` | P1-02 |

Positive end-to-end paths (personas) live in `agent/tests/`; this file is the adversarial backlog. Update reason-code mappings if `rules.yaml` changes (they must stay ⊆ `docs/03`).
