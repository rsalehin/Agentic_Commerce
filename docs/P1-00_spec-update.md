# P1-00 — Spec update before Phase 1 implementation

Source: `docs/07_dossier-contrast.md` (copy of 03_dossier-contrast.md). Apply these changes to the docs, rules and fixtures first; code follows in P1-01+. Every change below is a decision, not a proposal — implement as written, flag conflicts you find.

---

## 1. State machine — `docs/03_state-machine.md`

### 1.1 Split the human state
Replace `HUMAN_REQUIRED` with two states, both carrying `reason_codes[]` and `blocked_from`:
- `CUSTOMER_REQUIRED` — the *customer* must act (declare, sign, acknowledge a warning, choose another product). Resolved by the agent calling `ask_human` and re-submitting the blocked tool. No adviser involved.
- `REVIEW_REQUIRED` — *staff* must decide (partner-bank adviser or compliance). Resolved via the escalation queue. Resumes exactly at `blocked_from`.

### 1.2 Extend the tail of the flow
`INFORMED → CUSTOMER_CONFIRMED → BANK_ACCEPTED → PROVISIONING → DEPOT_OPENED`
- Rename `CONTRACT_SIGNED` → `CUSTOMER_CONFIRMED` (semantics: the customer confirmed *this snapshot*).
- `BANK_ACCEPTED`: the gateway records bank acceptance as its own act (`accepted_at`, `contract_ref`); in the demo this is automatic when all gates are current.
- `PROVISIONING`: exactly one core instruction per session, keyed by `operation_id` (= session_id + "create_depot").
- `RECONCILING`: entered when the core mock returns an ambiguous/timeout result; resolved by `get_opening_status(operation_id)` — never by a second create.
- Add terminal `EXPIRED` (mandate/session deadline) and `CANCELLED` (customer cancels before `CUSTOMER_CONFIRMED`).

### 1.3 Policy vocabulary
Replace `OK | WARN | HUMAN_REQUIRED | REJECT | ERROR` with:
`ALLOW | ALLOW_WITH_WARNING | REQUIRE_CUSTOMER | REQUIRE_REVIEW | DENY | ERROR`
- `ERROR` = guard rejection, state unchanged, retryable (audit event with from==to).
- `DENY` = terminal → `REJECTED`.
- Every `PolicyDecision` carries `policy_version` (semver of rules.yaml) and `reason_codes[]`.

### 1.4 Reason-code table (final)
| Code | Outcome | New? |
|---|---|---|
| MANDATE_SCOPE_EXCEEDED, MANDATE_EXPIRED, CLIENT_UNREGISTERED, SENDER_BINDING_INVALID | ERROR | 2 new |
| MANDATE_REVOKED, AGENT_UNVERIFIED, HOLDER_MANDATE_MISMATCH | DENY | – |
| TAX_ID_MISSING, TAX_DECLARATION_UNSIGNED, CONTRACT_UNSIGNED, PRODUCT_OUTSIDE_UNLOCKED, SNAPSHOT_STALE, ID_VERIFICATION_FAILED | REQUIRE_CUSTOMER | SNAPSHOT_STALE new |
| ID_NON_EU_DOCUMENT, ID_UNDERAGE, NAME_MISMATCH_REFERENCE_ACCOUNT, AML_SANCTIONS_HIT, AML_PEP_HIT, AML_HIGH_RISK_COUNTRY, TAX_FOREIGN_RESIDENCY, TAX_US_INDICIA, ADVICE_REQUESTED, COMPLEX_PRODUCT | REQUIRE_REVIEW | AML_SANCTIONS_HIT changed from REJECT |
| PROVISIONING_UNCERTAIN | → RECONCILING | new |
| REVIEW_REJECTED | DENY (only via adviser/compliance decision) | new |

### 1.5 Confidential compliance status
For `REVIEW_REQUIRED` caused by `AML_*` codes, the envelope returned to the agent contains `reason_codes: ["IN_REVIEW"]` and the German text "Ihr Antrag wird geprüft." The real codes are visible only in the Ops console and the audit log (GwG § 47 confidentiality). Document this in 03 and 05.

### 1.6 Audit event
Add fields `policy_version`, `rules_version`, `revision` (application revision), and actor value `compliance`.

---

## 2. Tool contracts — `docs/05_tool-contracts.md`

### 2.1 API-first, MCP as adapter
Define the canonical REST surface and state that MCP tools are 1:1 adapters over the same command handlers:
```
POST /v1/onboarding/start            ≡ onboarding.start
POST /v1/onboarding/{sid}/identify   ≡ onboarding.identify
POST /v1/onboarding/{sid}/tax        ≡ onboarding.tax_declaration
POST /v1/onboarding/{sid}/appropriateness
POST /v1/onboarding/{sid}/documents  ≡ onboarding.get_documents
POST /v1/onboarding/{sid}/confirm    ≡ onboarding.sign_contract
GET  /v1/onboarding/{sid}            ≡ onboarding.status
```
Same envelope, same errors. Add the invariant: "a raw HTTP request and an MCP call with identical payload produce identical policy decisions and audit events" (tested in P1-08).

### 2.2 Agent client registration and sender binding
- New fixture `fixtures/agent-clients.json`: `{client_id, operator_name, instance_jwk, status: active|blocked}`.
- Every call carries header/metadata `x-sender-proof`: a JWS (agent instance key) over `{htm, htu, session_id, iat, jti}` (DPoP-shaped, simplified). Gateway checks: client registered and active, proof signature valid, `jti` unused, `iat` within 60 s. Failures → `CLIENT_UNREGISTERED` / `SENDER_BINDING_INVALID` (ERROR).
- The mandate's `agent.id` must equal the `client_id` in the proof.
- Revocation: every *write* re-checks `revocation_url` (mandate) and the client status. Document as ADR-02 addendum.

### 2.3 Snapshot instead of bundle hash
- `get_documents` returns `revision`, `product_version`, `pricing_version`, `snapshot_digest = sha256(JCS({session_id, revision, product_id, product_version, pricing_version, document_hashes[], plan}))`.
- `sign_contract` (`/confirm`) signs `snapshot_digest`. Gateway recomputes; mismatch → `SNAPSHOT_STALE` (REQUIRE_CUSTOMER), and a fresh bundle is issued.
- `sign_contract` accepts `idempotency_key`; identical replay returns the stored result; same key with different payload → 409.

### 2.4 Channel attribution on the application
`Application` gains `origin_channel` (`agent|web|app|branch`), `servicing_partner_id`, `current_channel`, `commercial_attribution_ref`, `referral_receipt` (optional). `onboarding.start` accepts `referral_receipt`: a JWS signed by the partner bank key (`fixtures/keys/volksbank-leipzig`) with `{partner_id, product_id, sub (customer did), exp, jti}`. Invalid/foreign receipt → ignored with audit note `REFERRAL_INVALID`; never blocks opening.

### 2.5 Field additions already agreed (P0-01) — verify present
`reference_account_iban` (identify, optional), `birth_place_country` (identify out + data_release), `advice_requested` (appropriateness in), `pid.nationalities`, card fingerprint definition.

### 2.6 Service mode
`onboarding.appropriateness` output gains `service_mode: account_only | non_advised | advised`. In the MVP: `non_advised` when `requested_classes` non-empty, `account_only` when empty (then appropriateness is `NOT_REQUIRED`, recorded with reason "empty Depot, no service yet"), `advised` never (routes to REVIEW via ADVICE_REQUESTED).

---

## 3. Rules — `gateway/rules/rules.yaml`
- Migrate all `outcome:` values to the new vocabulary per §1.4.
- R-AML-01: `outcome: REQUIRE_REVIEW`, `message_de: "Ihr Antrag wird geprüft."`, add `confidential: true` (triggers §1.5 masking).
- Add R-CTR-02 `SNAPSHOT_STALE` (law: "BGB Vertragsschluss – Antrag und Annahme müssen inhaltlich übereinstimmen; Fernabsatz-Informationspflichten"), R-MND-05 `CLIENT_UNREGISTERED`/`SENDER_BINDING_INVALID` (law: "DORA Art. 28 ff. – Drittparteien; Zulassung externer Clients"), R-SVC-01 service-mode classification (law: "WpHG § 63 Abs. 10/11 – Pflicht knüpft an die Dienstleistung, nicht an das leere Depot").
- Add top-level `version: "1.1.0"`.
- Regenerate `docs/06_rules.md`.

---

## 4. Fixtures
- `fixtures/personas.json`: `sanction_test.expected_final_state` stays `REJECTED` but via `expected_path: REVIEW_REQUIRED → compliance decision reject`. Add to lena/marco: `origin_channel`, `servicing_partner_id: "volksbank-leipzig"`, and a `referral_receipt` stub reference. Add product `DE000MOCK0001` **pricing_version p-2** with `depot_fee_eur_year: 12.0` for the fee-change demo.
- New `fixtures/provider-directory.json` (agent side): `[{domain, legal_entity, custodian, bafin_id, lei, pinned_kid}]` for `fonds-ag.example`; plus `fixtures/attacks/lookalike-card.json` — a *validly signed* card for `fonds-ag.example.co` with its own JWKS (must be refused: `PROVIDER_UNVERIFIED`).
- New `fixtures/agent-clients.json` (§2.2). Add partner-bank key `volksbank-leipzig` to `wallet/keys.py` generation.

---

## 5. Agent — `docs/05 §4` + `agent/`
- `discovery.verify(url)`: (1) domain must be in `provider-directory.json`; (2) card signature must verify with the *pinned* kid, not merely with the JWKS the card points to; (3) no PII is sent before both pass. Reason codes on failure: `PROVIDER_UNVERIFIED`, `CARD_SIGNATURE_INVALID`.
- Agent instance key generated at startup; `x-sender-proof` on every call.
- `ask_human` gains a `warning_ack` mode for `PRODUCT_OUTSIDE_UNLOCKED` (customer acknowledges the § 63 (10) warning or drops the class).

---

## 6. ADRs — `docs/decisions/`
- **ADR-01** rewrite: "API-first canonical contract; MCP (and later A2A) are adapters over the same commands; identical-policy test." Rejected: MCP as the only surface.
- **ADR-02** addendum: mandate = legal authorisation evidence; client registration + sender binding + revocation check = technical access control; production profile = OAuth 2.0 Security BCP / FAPI 2.0 with PAR/PKCE/DPoP (not built in MVP).
- **ADR-06** rewrite: signed Agent Card is the format; trust anchor is the verified provider directory (pinned key, legal entity, BaFin ID); later: partner referral, eIDAS QWAC, industry register.
- **ADR-07** rewrite: channel attribution as data (four fields + signed referral receipt); adviser handles REVIEW cases; commission logic stays in existing settlement systems.
- **ADR-11** new: "Business idempotency and reconciliation instead of exactly-once" (operation_id, unique constraint, RECONCILING, no blockchain).
- **ADR-12** new: "Appropriateness at opening and service_mode" — profile collected at opening to unlock classes; the duty attaches to the service; account-only → NOT_REQUIRED with recorded reason.

---

## 7. Docs 01 / 04 / demo / glossary
- `docs/01_ist-analyse.md`: add rows P02 (eligibility: adulthood, account type, residence), P03 (access & contact channel — email confirmation is not KYC), P15 (ongoing monitoring, re-screening, retention). Label friction figures as "Branchenangaben aus Sekundärquellen". Fix retention wording: GwG 5 years (destruction by 10), WpHG 5 (+2 on order).
- `docs/04_annahmen.md`: add assumptions — "sanctions/PEP matches are resolved by compliance, never automatically rejected"; "QES via wallet is a design choice, not a statutory requirement"; "agent operator is a registered client, not a licensed intermediary"; "AI Act dates to be re-verified against the July 2026 amendment before the deck". Add to open questions: which entity accepts the contract; commission rules.
- `docs/demo-script.md`: replace the manipulation minute with three negatives — (1) agent calls `/confirm` without holder signature → `CUSTOMER_REQUIRED`, no Depot; (2) identical `/confirm` retry → same Depot number, count = 1; (3) pricing_version changes after confirmation → `SNAPSHOT_STALE` → re-confirm. Keep forged/lookalike card as the discovery negative. Note Marco's two escalations.
- New `docs/test-plan.md`: import dossier tests T02–T08, T12–T17, T19, T22–T24 as the negative-test backlog with our reason codes mapped.
- `docs/glossar.md`: add service_mode, snapshot, referral receipt, sender proof, RECONCILING.
- Handoff legal basis: cite Art. 246b § 3(3) EGBGB (human intervention on request when online tools are used) wherever the "Berater/Mensch anfordern" button is described.

---

## 8. CLAUDE.md and ROADMAP
- CLAUDE.md §2: replace principle 4's outcome list with the new vocabulary; add principle 9: "API-first — MCP is an adapter; a raw HTTP request must hit the same policy"; principle 10: "Compliance cases are confidential — the agent sees IN_REVIEW only."
- ROADMAP: insert **P1-00** (this spec, docs+fixtures only, commit `docs(specs): P1-00 …`). Amend P1-05 (idempotent `create_depot`, `get_opening_status`, ambiguous-result mode), P1-08 (REST + MCP over shared handlers; identical-policy test), P1-02 (directory + pinned kid + lookalike test), P1-03 (client registration + sender proof), P2-01 (two queues: customer vs review; compliance role), P3-01 (three negatives per §7).

---

## 9. Acceptance for P1-00
- All reason codes in rules.yaml ∈ docs/03 table; all states in 03 ∈ 05 envelope docs; personas reach expected states under the new rules on paper (lena → DEPOT_OPENED; marco → ADVISED_HANDOFF via two REVIEW_REQUIRED; sanction_test → REJECTED via compliance decision).
- `docs/06_rules.md` regenerated; ADR statuses set; ROADMAP updated. Then stop for approval of the P1-01..P1-04 plan.
