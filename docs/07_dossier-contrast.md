# Our plan vs. the "Agentic Commerce in Financial Distribution" dossier

*Contrast written 14 Sept 2026. "Ours" = docs/00–06 + ADR-01..10 + Phase 0 repo. "Dossier" = TRUSTEQ_Research_Dossier_EN.html.*

## 1. One-line positioning

| | Ours | Dossier |
|---|---|---|
| Thesis | "The agent opens the Depot end-to-end; the human acts only at the steps the law reserves for them." | "The agent prepares; a deterministic bank-controlled process concludes; the customer confirms in the bank's own interface." |
| Tone | Bolder, closer to the case's *Zielbild 2030* wording ("agentenbasierte Depoteröffnung inkl. Identitätsnachweis, Autorisierung, Vertragsschluss") | Conservative, production/legal-risk first; explicitly labels 2030 as assumptions |
| Where the human confirms | On the wallet (trusted surface), signing mandate / tax declaration / contract hash | In the bank customer UI with step-up authentication; snapshot + receipt |

Both keep the human as the declaring party; both put policy outside the LLM. The disagreement is *where* trust is anchored and *how much* of the 2030 stack to assume.

## 2. Difference by difference

### 2.1 Scope of the first case
- **Ours:** Depot opening *with* a savings-plan intent (150 €/month ETF), appropriateness run at opening, product classes unlocked, cost estimate for the plan.
- **Dossier:** "Account-only": no order, no advice, no credit; appropriateness is a *service* obligation and is `NOT_REQUIRED` for an empty Depot; an ETF purchase is a later, separately authorised act. Lists "every Depot requires a suitability assessment" as a claim to avoid.
- **Verdict:** Dossier is legally sharper. Ours matches what German brokers actually do (they collect Kenntnisse/Erfahrungen at opening to unlock classes), so it is defensible — but only if we *say* it that way: "Profil wird bei Eröffnung erhoben, um Produktklassen für spätere Orders freizuschalten; die Pflicht selbst hängt an der Dienstleistung, nicht am leeren Depot." Add a `service_mode` field (`account_only | non_advised | advised`) so the classification is explicit in the rules. Keep the savings-plan intent in the *mandate* (it drives the cost information the customer sees) but do not execute an order.

### 2.2 Authorisation of the agent
- **Ours:** provider-independent **Intent Mandate** signed by the customer's wallet key (AP2-inspired JWS); verified by the gateway; holder key later bound to the PID `cnf`. No agent-operator identity beyond `agent_id` + card fingerprint; no sender-binding.
- **Dossier:** OAuth/OIDC with a FAPI 2.0-style profile (PAR, PKCE, private_key_jwt/mTLS, DPoP), **registered confidential clients**, and a **bank-issued server-side grant** with actions, mutable fields, product, constraints, expiry, revocation, plus separate `legal_mandate_ref` and `consent_receipt_ref`. Three identities: agent operator, running instance, customer.
- **Pros dossier:** built on adopted RFCs; sender-constrained tokens; immediate revocation via grant service; fits any bank's IAM; covers the "agent operator" as a legal actor. **Cons:** requires the customer to visit the bank interface to delegate (reads like "web onboarding with agent prefill"); bank-specific grant per provider; far more surface to build (an AS, DPoP, PAR) — the dossier itself mocks all of it in its prototype.
- **Pros ours:** provider-independent, matches the "ohne Website-Besuch" requirement and the EUDI direction; cheap to build for real (JWS). **Cons:** relies on a mandate credential format nobody has standardised (AP2 is in beta); no protection against a stolen mandate replayed from another client; no operator accountability.
- **Verdict:** the two are *complementary*, and the dossier's own grant JSON admits it (`legal_mandate_ref`). Keep our wallet-signed mandate as the **legal** authorisation evidence; add the dossier's **technical** layer as an ADR and a thin implementation: registered agent clients (`client_id` + key), sender-binding of tool calls (DPoP-style proof over method/URL/nonce signed by the agent instance key), and a revocation check on every write. Update ADR-02 to say exactly this ("mandate = intent evidence; client registration + sender binding = access control").

### 2.3 Contract confirmation and bank acceptance
- **Ours:** `get_documents` returns a bundle + `contract_hash`; human signs it in the wallet (QES mock); `sign_contract` → `CONTRACT_SIGNED` → `DEPOT_OPENED`.
- **Dossier:** bank builds an **immutable snapshot** (application revision + product/pricing version + documents); customer confirms *that snapshot* with a one-time, expiring challenge; **receipt** is separate from any signature; **bank acceptance** is its own act and state; any material change (fee, product, contracting party) invalidates the receipt; QES is not assumed to be required.
- **Verdict:** adopt the dossier's structure. Concretely: (a) `bundle_hash` becomes `snapshot_digest` over application revision + product version + document hashes; (b) new states `CUSTOMER_CONFIRMED → BANK_ACCEPTED → PROVISIONING → DEPOT_OPENED`; (c) test "price changes after confirmation → old receipt invalid → new confirmation". Keep the wallet as the confirmation surface (it *is* the bank-controlled trusted surface in the EUDI model), but state on a slide that QES is a design choice, not a legal requirement.

### 2.4 State machine and policy vocabulary
- **Ours:** 9 linear states + `HUMAN_REQUIRED` / `REJECTED`; outcomes `OK | WARN | HUMAN_REQUIRED | REJECT (+ERROR guard)`.
- **Dossier:** application state (`DRAFT … OPENED`, plus `RECONCILING`, `EXPIRED`, `CANCELLED`, `TECHNICAL_HOLD`) with **parallel check objects** carrying `input_version`; session state (`AUTHENTICATED`, `DELEGATION_VERIFIED`) separated from business state; policy outcomes `ALLOW | DENY | REQUIRE_CUSTOMER | REQUIRE_REVIEW` with policy version.
- **Pros dossier:** honest about asynchrony ("timeout ≠ failure"), recovery, and who must act (customer vs. staff). **Cons:** heavier to build and to explain in ten minutes.
- **Verdict:** keep our linear spine (it maps 1:1 to the Ist-Analyse blocks and is easy to narrate), but (a) split `HUMAN_REQUIRED` into `CUSTOMER_REQUIRED` and `REVIEW_REQUIRED` — different actors, different UI; (b) add `PROVISIONING` and `RECONCILING` with an idempotency key on `create_depot`; (c) add `EXPIRED`/`CANCELLED`; (d) record `policy_version` and the rules version on every audit event.

### 2.5 Sanctions and PEP handling
- **Ours:** `AML_SANCTIONS_HIT → REJECT` automatically.
- **Dossier:** a list match is a *possible* identity correspondence; fuzzy matches are resolved by compliance; PEP is never automatic exclusion; suspicious-activity handling is confidential (§ 47 GwG) — the customer sees a neutral status.
- **Verdict:** the dossier is right and ours is a real error. Change R-AML-01 to `REVIEW_REQUIRED` (compliance case); `REJECTED` only after a documented compliance decision. The `sanction_test` persona then ends in `REJECTED` via the adviser/compliance panel — a better demo anyway. Also: the agent/customer must only see "in Prüfung", never the match details.

### 2.6 Provider discovery and trust anchor
- **Ours:** JWS-signed Agent Card with JWKS on the provider's own domain; ADR-06 defers a registry/QWAC to later.
- **Dossier:** points out the circularity — a card whose key is served from the same domain proves domain control (like TLS), not "this domain belongs to the regulated Depot contracting party". Anchor must come from outside: a versioned **provider directory/allowlist**, signed partner referral, or documented domain verification; treat search results as untrusted; send no PII before verification. REST + OpenAPI canonical; MCP/A2A optional adapters; custom `/.well-known/...` names must not be presented as standards.
- **Verdict:** keep the signed card (it is still the right *format*), add a tiny **verified provider directory** on the agent side (`fixtures/provider-directory.json`: domain → legal entity → custodian → BaFin ID → pinned key id). Demo: a lookalike domain with a validly signed card is refused because it is not in the directory. Rename ADR-06 accordingly.

### 2.7 Interface: MCP-first vs. API-first
- **Ours:** FastMCP tools are the provider surface (ADR-01).
- **Dossier:** versioned REST/OpenAPI is the canonical contract; MCP and A2A are adapters that translate into the same domain commands; "a direct API call encounters the same policy" is the manipulation proof.
- **Verdict:** implement domain commands once, expose them via REST *and* MCP, and add one test that a hand-crafted HTTP request without a valid mandate is rejected identically. Cost is low with FastAPI + FastMCP mounted side by side; the message ("protocol is an adapter") scores directly on the *Deprecation* criterion.

### 2.8 Channel conflict
- **Ours:** partner bank keeps advice and escalations (ADR-07).
- **Dossier:** channel relationship is **data**: `origin_channel`, `servicing_partner_id`, `current_channel`, `commercial_attribution_ref`, plus a **signed referral receipt** bound to the application; the same application ID continues across branch, app, and agent; commission logic stays in existing settlement systems.
- **Verdict:** adopt the four fields and the referral receipt (a signed JWT from the partner bank in the fixtures). It turns "Kanalkonflikt" from a process answer into an architecture answer, which is what the case grades.

### 2.9 Prototype scope and demo
- **Ours:** happy path (~5 min) + Marco escalation + manipulation (scope exceeded, forged card).
- **Dossier:** 90-second demo built around **negative cases**: agent tries to confirm itself → blocked; customer confirms → one account; retry → still one account; price change → old receipt invalid. 28 test cases (T01–T28), many about idempotency, replay, revision conflicts, cross-customer access, revoked grant during session.
- **Verdict:** shorten our happy path narration and add three negatives that the dossier makes central: (1) agent calls `sign_contract` without holder signature → `CUSTOMER_REQUIRED`; (2) identical `sign_contract` retry → same Depot number, count stays one; (3) fee changes after confirmation → re-confirmation required. Import T02–T08, T12–T17, T19, T22–T24 into `docs/test-plan.md` as the Phase 1–3 negative-test backlog.

### 2.10 Legal precision points the dossier is stricter on
- AI Act: the dossier states it was **amended in July 2026** and that high-risk deadlines moved (Dec 2027 / Aug 2028). Our timeline claims "Art. 50 from 08/2026" — this must be re-verified before it goes on a slide.
- Distance selling 2026: Art. 246b § 3(3) EGBGB gives the customer a right to **human intervention on request** when online tools are used — a legal basis for our handoff button. Use it.
- Retention: GwG 5 years (destroy after 10), WpHG 5 (+2). We wrote "5–10"; say it precisely.
- Friction numbers: the dossier deliberately avoids quantitative abandonment claims. Ours cites 6 €/30 %/1–3 days from secondary sources — keep them, but label them "Branchenangaben (Sekundärquellen)" and never as the client's numbers.
- "AML_SANCTIONS_HIT = reject", "QES required", "eID completes AML" — all on the dossier's avoid-list; our current wording brushes against the first two.

### 2.11 What ours has that the dossier lacks
- A **real credential path**: SD-JWT VC issuance/presentation/verification and holder-key binding (dossier mocks KYC as pass/review/fail and explicitly builds no eID/wallet crypto).
- **Rules with statutory citations per rule** and a machine-readable catalogue (dossier has a policy function with reason codes; citations live in prose).
- A completed **Ist-Analyse with roles, friction, timeline** and the Figma boards; the dossier's process table (P01–P15) is broader (adds P02 eligibility, P03 access/contact, P15 ongoing maintenance) — worth folding those three rows into ours.
- **Split-screen UI with live audit trail** and an adviser panel; the dossier proposes a small HTML status page.
- A working **repo, CI and ADR set** already at Phase 0.

## 3. Recommended merge (ordered by value ÷ effort)

| # | Change | Where | Effort |
|---|---|---|---|
| 1 | Sanctions hit → `REVIEW_REQUIRED`; reject only by compliance decision; neutral status to agent | rules.yaml R-AML-01, docs/03, personas | S |
| 2 | Split `HUMAN_REQUIRED` → `CUSTOMER_REQUIRED` / `REVIEW_REQUIRED`; outcomes `ALLOW/DENY/REQUIRE_CUSTOMER/REQUIRE_REVIEW/ERROR`; `policy_version` on audit events | docs/03, 05, 06, rules.yaml, engine | M |
| 3 | Snapshot digest + states `CUSTOMER_CONFIRMED → BANK_ACCEPTED → PROVISIONING → DEPOT_OPENED`, `RECONCILING`, idempotency key; fee-change invalidation test | docs/03, 05, core mock, tests | M |
| 4 | Verified provider directory on the agent + lookalike-domain negative test; ADR-06 rewrite | agent/, fixtures, ADR-06 | S |
| 5 | REST + MCP over the same domain commands; "raw HTTP hits same policy" test; ADR-01 rewrite | gateway | M |
| 6 | Channel fields + signed referral receipt in Application; ADR-07 rewrite | docs/05, core, fixtures | S |
| 7 | Agent client registration + sender-binding + revocation check on writes; ADR-02 addendum | gateway/adapters, agent | M |
| 8 | `service_mode` classification; appropriateness framed as "unlock for later orders" | rules.yaml, docs/04, slide copy | S |
| 9 | Demo restructure: three negatives (self-confirm, retry, fee change); import dossier tests as backlog | docs/demo-script.md, docs/test-plan.md | S |
| 10 | Verify AI Act amendment and dates; fix retention wording; label friction numbers as industry figures | docs/01, Figma boards, deck | S |

Not adopted: full FAPI/PAR/DPoP authorisation server (mocked in the dossier too — describe as production profile in ADR-02); parallel check objects with `input_version` (say it in the deck as the production extension); dossier's account-only scope (keep the savings-plan intent in the mandate for the cost-information demo; do not execute orders).

## 4. What to say in the interview if asked "why not X"
- *Why a wallet-signed mandate instead of a bank grant?* Provider-independent, matches "ohne Website-Besuch" and the EUDI direction; the bank grant/sender-binding is the technical access layer underneath it (ADR-02).
- *Why is the Agent Card not enough?* It is the format; trust comes from the verified provider directory (ADR-06).
- *Why MCP?* It is an adapter over a canonical API; the policy is identical for both (ADR-01, test).
- *Why run appropriateness at opening?* Market practice to unlock product classes; the legal duty attaches to the service; `service_mode` records that (rules).
