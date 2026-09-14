# ROADMAP

Phases and tasks. Each task has an id used in commit messages, a deliverable, and acceptance criteria. Work top-down; do not start a task before the previous phase's acceptance is green. Mark tasks `[x]` when done and add the commit hash.

Legend: **G** gateway · **A** agent · **W** wallet · **C** core · **U** ui · **D** docs

---

## Phase 0 — Skeleton (target: 1 session)

- [x] **P0-01 (D)** Confirm `docs/` skeleton is complete: 00–06 specs, ADR-01..10, deprecation register, demo script, glossary, `docs/README.md`. Fill nothing new; only fix inconsistencies you find and list them in the plan. — `b4f546f`
- [x] **P0-02** `pyproject.toml` (uv-managed project packaging the flat `gateway`, `agent`, `wallet`, `core` packages), `ruff`, `mypy`, `pytest` config, `.env.example`, `.gitignore`, `README.md` quick start. — `131dfc6`
- [x] **P0-03 (W)** `wallet/keys.py`: generate Ed25519 key pairs on first run into `fixtures/keys/` (issuer `mock-bundesdruckerei`, provider `fonds-ag-2026`, one holder key per persona), export public JWKs to `fixtures/jwks.public.json`. — `30ecfc7`
- [x] **P0-04** `run.ps1` + `docker-compose.yml` starting gateway/wallet/core/ui with port checks. `/health` endpoints on the three backends (UI: run.ps1 verifies Vite binds 5174). — `66f9e78`
- [x] **P0-05** CI: GitHub Actions running ruff + mypy + pytest on push. — `480cdc6`

**Acceptance:** `uv run pytest` passes (smoke tests), `run.ps1` prints four healthy services, CI green.

---

## Phase 1 — Happy path (ship first)

- [x] **P1-00 (D)** Spec update from the dossier contrast (`docs/07_dossier-contrast.md`): implement `docs/P1-00_spec-update.md` — docs, `rules.yaml` (v1.1.0, new outcome vocabulary), fixtures and ADRs only, no service code beyond the `wallet/keys.py` key list. Commit `docs(specs): P1-00 …`. Acceptance in its §9. — `999a590`
- [x] **P1-01 (G)** Signed Agent Card: `GET /.well-known/agent-card.json` per `fixtures/agent-card.example.json`, JWS over JCS-canonical card without `signatures` (Ed25519, `gateway/canonical.py`), `card_fingerprint`, `GET /.well-known/jwks.json` **provider key only**. Tests: valid verifies; tampered fails; foreign-key fails; jwks excludes issuer/holder kids. — `4363357`
- [x] **P1-02 (A)** Discovery + verification client (`agent/discovery.py`): domain must be in `fixtures/provider-directory.json`; verify card signature against the **pinned key** (local keystore by `pinned_kid`, not the card's `jku`); check `skills[].id` contains `onboarding.v1` + `capabilities.onboarding=="v1"` + an `mcp` `supportedInterfaces` entry; send no PII before both pass. Negative tests incl. **validly-signed lookalike** (`fixtures/attacks/lookalike-card.json`) → `PROVIDER_UNVERIFIED`, bad signature / key substitution → `CARD_SIGNATURE_INVALID`. — `c97cb86`
- [x] **P1-03 (W+G)** Mandate + access control: pydantic model per `docs/05 §2`; wallet signs (holder key) → compact JWS; gateway `MandateVerifier` port + JWS adapter checks signature (against `iss` did:key), `aud`, `exp` (guard), `jti` consume-once, scope, and R-MND-04 card/agent binding. **Agent client registration** (`fixtures/agent-clients.json`) + **`x-sender-proof`** JWS (R-MND-05/06) + **revocation check on writes**. Tests: expired, wrong audience, scope tamper, foreign key, jti replay, unregistered client, bad sender proof. — `f873e7a`
- [x] **P1-04 (W)** Mock EUDI wallet: in-house `wallet/sdjwt.py` (JWS + `_sd` + KB-JWT) issues PID as SD-JWT VC per persona with `cnf` = that persona's holder key; wallet serves the **issuer JWKS** and `/revocations`; present selected claims (nonce + aud); verify in gateway via `IdentityVerifier` port (+ R-ID-05 `did:key(cnf)==iss`). Tests: correct claims only; wrong nonce/aud; issuer-key mismatch; tampered disclosure; cnf≠iss → `HOLDER_MANDATE_MISMATCH`. — `d0ff029`
- [ ] **P1-05 (C)** Core mock: SQLModel tables (Customer, Depot, KycRecord, AppropriatenessProfile, Contract, Application w/ channel fields), **idempotent `create_depot(operation_id)`** with a unique constraint, `get_opening_status(operation_id)`, an ambiguous/timeout mode (`PROVISIONING_UNCERTAIN` → `RECONCILING`); stubs `bzst_kistam.lookup(tax_id)`, `sanctions.screen(...)` (fixture hit), `reference_account.check(iban, name)`.
- [ ] **P1-06 (G)** Rules engine: load `gateway/rules/rules.yaml` (v1.1.0), evaluate per step, return `PolicyDecision` with `policy_version`, outcomes `ALLOW | ALLOW_WITH_WARNING | REQUIRE_CUSTOMER | REQUIRE_REVIEW | DENY | ERROR`, aggregation precedence per `docs/03`; guards `R-MND-01/02/05/06` → `ERROR`; AML confidential masking → `IN_REVIEW`. 100 % branch coverage on the seed rules via synthetic-`ctx` unit tests; test that every `reason_code` in `rules.yaml` ∈ `docs/03` table.
- [ ] **P1-07 (G)** State machine + audit: `Session` with states per `docs/03` (incl. `CUSTOMER_REQUIRED`/`REVIEW_REQUIRED`, `CUSTOMER_CONFIRMED → BANK_ACCEPTED → PROVISIONING → DEPOT_OPENED`, `RECONCILING`), guarded transitions, hash-chained `AuditEvent` (with `policy_version`, `rules_version`, `revision`), `verify_chain()`; guard rejections audited with `from==to`.
- [ ] **P1-08 (G)** Command handlers exposed via **REST (FastAPI `/v1/...`) and MCP (FastMCP) over the same handlers** — `onboarding.start/identify/tax_declaration/appropriateness/get_documents/sign_contract(/confirm)/status/get_opening_status` exactly per `docs/05`. Human-only tools reject payloads without a valid holder signature. **Identical-policy test:** a raw HTTP request and an MCP call with the same payload produce identical policy decisions and audit events.
- [ ] **P1-09 (A)** Orchestrator: plain-Python loop with Anthropic tool use; tools = the MCP tools + local `wallet.*` tools + `ask_human(question, payload_to_sign?)`. System prompt in `agent/prompts/kundenagent.de.md`. Provider abstraction in `agent/llm/`.
- [ ] **P1-10 (A)** `agent/tests/test_happy_path.py`: headless run for persona `lena` reaches `DEPOT_OPENED` with a valid audit chain, using a recorded LLM transcript (no network in tests).
- [ ] **P1-11 (G)** `GET /events` SSE stream of audit events + session state; `GET /sessions/{id}` for the UI.
- [ ] **P1-12 (U)** Split-screen UI: left chat (agent messages, human prompts with "Bestätigen/Signieren" buttons), right Ops-Konsole (state machine ribbon, audit list with evidence hashes, provider card with "verifiziert" badge). German copy. TRUSTEQ theme tokens.
- [ ] **P1-13 (A)** Record the happy path into `fixtures/recorded_runs/lena.json`; `agent/replay/` replays it through the real gateway.

**Acceptance:** Lena scenario runs live and in replay, ends with a Depot number, audit chain verifies, all tests green, ADR-01..06 status `accepted`.

---

## Phase 2 — Escalation and partner bank

- [ ] **P2-01 (G)** Escalation queues — **two queues**: `customer` (from `CUSTOMER_REQUIRED`, resolved by the agent via `ask_human`) and `review` (from `REVIEW_REQUIRED`, split **adviser** vs **compliance**; AML cases are compliance-only and confidential). `Escalation{session, queue, actor_role, reasons, evidence, status, note}`; endpoints `GET /escalations`, `POST /escalations/{id}/decision` (approve / request_appointment / reject → `REVIEW_REJECTED`).
- [ ] **P2-02 (G)** Resume logic: an approved escalation re-enters the state machine at the blocked step; appointment sets `ADVISED_HANDOFF` and returns a structured next-step to the agent.
- [ ] **P2-03 (U)** Adviser panel in the Ops-Konsole (partner bank persona "Volksbank Leipzig, Beraterin Frau Weber"): list, detail with rule citations, decision buttons.
- [ ] **P2-04 (A)** Persona `marco` end-to-end: agent explains the handoff in German, waits, continues after adviser decision.
- [ ] **P2-05 (G)** Nachweis view: `GET /sessions/{id}/evidence` mapping each rule to the evidence that satisfied it; JSON export.
- [ ] **P2-06 (A)** Record `fixtures/recorded_runs/marco.json`.

**Acceptance:** Marco scenario runs live and in replay; ADR-07 accepted.

---

## Phase 3 — Robustness and polish

- [ ] **P3-01 (A+G)** Negative-case demo (per `docs/P1-00 §7`): (1) agent calls `/confirm` without a holder signature → `CUSTOMER_REQUIRED`, no Depot; (2) identical `/confirm` retry (same `idempotency_key`) → same Depot number, count = 1; (3) `pricing_version` changes after confirmation → `SNAPSHOT_STALE` → re-confirm. Plus the injected-instruction over-limit call → `MANDATE_SCOPE_EXCEEDED` (red event), and the validly-signed lookalike/forged card → discovery refuses.
- [ ] **P3-02 (G)** Deprecation adapter demo: `IDENTITY_VERIFIER=eid_stub` swaps the wallet adapter for an eID stub without code change; documented in ADR-10 and `docs/deprecation-register.md`.
- [ ] **P3-03 (A)** Replay-mode toggle in the UI header; interview fallback tested with network disabled.
- [ ] **P3-04 (U)** Final German copy review, screenshots for the deck into `docs/assets/`.
- [ ] **P3-05 (D)** `docs/demo-script.md` finalised with timings; `docs/qa-cheatsheet.md` (expected interviewer questions + answers).

**Acceptance:** all three paths demoable in under 8 minutes; docs complete; tag `v1.0-interview`.

---

## Explicitly out of scope (see docs/04_annahmen.md)

Real OpenID4VP/DC-API, real eID/AusweisApp, VideoIdent, payments/SCA, order execution, Geeignetheitsprüfung, OAuth 2.1 on MCP, multi-tenant partner banks, production hosting.
