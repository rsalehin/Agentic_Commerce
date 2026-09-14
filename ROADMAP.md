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

- [ ] **P1-01 (G)** Signed Agent Card: `GET /.well-known/agent-card.json` per `fixtures/agent-card.example.json`, JWS signature (JCS-canonicalised payload, Ed25519), `GET /.well-known/jwks.json`. Tests: valid signature verifies; tampered card fails; card signed with foreign key fails.
- [ ] **P1-02 (A)** Discovery + verification client (`agent/discovery.py`): fetch card, verify signature against JWKS on the same origin, check `supportedInterfaces` contains `onboarding.v1`, refuse otherwise. Negative tests.
- [ ] **P1-03 (W+G)** Mandate: pydantic model per `docs/05_tool-contracts.md §2`; wallet signs (holder key) → compact JWS; gateway `MandateVerifier` port + JWS adapter checks signature, `aud` (provider domain), `exp`, scope fields. Tests incl. expired, wrong audience, scope tampering.
- [ ] **P1-04 (W)** Mock EUDI wallet: issue PID as SD-JWT VC for each persona (`fixtures/personas.json`), present selected claims with key binding (nonce + audience), verify in gateway via `IdentityVerifier` port. Tests: correct claims only; wrong nonce fails; issuer-key mismatch fails.
- [ ] **P1-05 (C)** Core mock: SQLModel tables (Customer, Depot, KycRecord, AppropriatenessProfile, Contract), `create_depot()`, stubs `bzst_kistam.lookup(tax_id)`, `sanctions.screen(name, dob, nationality)` (fixture list with a deliberate hit), `reference_account.check(iban, name)`.
- [ ] **P1-06 (G)** Rules engine: load `gateway/rules/rules.yaml`, evaluate per step, return `RuleResult[]` with outcome and law citation; aggregate to `OK | WARN | HUMAN_REQUIRED | REJECT | ERROR` (guards `R-MND-01/02` → `ERROR` envelope, state unchanged; see `docs/03` Guards). 100 % branch coverage on the 20 seed rules via engine unit tests over synthetic `ctx` (the three personas cover only the end-to-end paths). Add a test asserting every `reason_code` in `rules.yaml` exists in the `docs/03_state-machine.md` table.
- [ ] **P1-07 (G)** State machine + audit: `Session` with states per `docs/03_state-machine.md`, guarded transitions, hash-chained `AuditEvent`, `verify_chain()`.
- [ ] **P1-08 (G)** MCP tools via FastMCP: `onboarding.start`, `onboarding.identify`, `onboarding.tax_declaration`, `onboarding.appropriateness`, `onboarding.get_documents`, `onboarding.sign_contract`, `onboarding.status` — request/response exactly per `docs/05_tool-contracts.md`. Human-only tools reject payloads without a valid holder signature.
- [ ] **P1-09 (A)** Orchestrator: plain-Python loop with Anthropic tool use; tools = the MCP tools + local `wallet.*` tools + `ask_human(question, payload_to_sign?)`. System prompt in `agent/prompts/kundenagent.de.md`. Provider abstraction in `agent/llm/`.
- [ ] **P1-10 (A)** `agent/tests/test_happy_path.py`: headless run for persona `lena` reaches `DEPOT_OPENED` with a valid audit chain, using a recorded LLM transcript (no network in tests).
- [ ] **P1-11 (G)** `GET /events` SSE stream of audit events + session state; `GET /sessions/{id}` for the UI.
- [ ] **P1-12 (U)** Split-screen UI: left chat (agent messages, human prompts with "Bestätigen/Signieren" buttons), right Ops-Konsole (state machine ribbon, audit list with evidence hashes, provider card with "verifiziert" badge). German copy. TRUSTEQ theme tokens.
- [ ] **P1-13 (A)** Record the happy path into `fixtures/recorded_runs/lena.json`; `agent/replay/` replays it through the real gateway.

**Acceptance:** Lena scenario runs live and in replay, ends with a Depot number, audit chain verifies, all tests green, ADR-01..06 status `accepted`.

---

## Phase 2 — Escalation and partner bank

- [ ] **P2-01 (G)** Escalation queue: `Escalation{session, reasons, evidence, status, adviser_note}`; created automatically on `HUMAN_REQUIRED`; endpoints `GET /escalations`, `POST /escalations/{id}/decision` (approve / request_appointment / reject).
- [ ] **P2-02 (G)** Resume logic: an approved escalation re-enters the state machine at the blocked step; appointment sets `ADVISED_HANDOFF` and returns a structured next-step to the agent.
- [ ] **P2-03 (U)** Adviser panel in the Ops-Konsole (partner bank persona "Volksbank Leipzig, Beraterin Frau Weber"): list, detail with rule citations, decision buttons.
- [ ] **P2-04 (A)** Persona `marco` end-to-end: agent explains the handoff in German, waits, continues after adviser decision.
- [ ] **P2-05 (G)** Nachweis view: `GET /sessions/{id}/evidence` mapping each rule to the evidence that satisfied it; JSON export.
- [ ] **P2-06 (A)** Record `fixtures/recorded_runs/marco.json`.

**Acceptance:** Marco scenario runs live and in replay; ADR-07 accepted.

---

## Phase 3 — Robustness and polish

- [ ] **P3-01 (A+G)** Manipulation demo: fixture provider response with injected instruction; agent proposes over-limit call; gateway returns `MANDATE_SCOPE_EXCEEDED`; UI shows red event. Forged-card fixture → discovery refuses.
- [ ] **P3-02 (G)** Deprecation adapter demo: `IDENTITY_VERIFIER=eid_stub` swaps the wallet adapter for an eID stub without code change; documented in ADR-10 and `docs/deprecation-register.md`.
- [ ] **P3-03 (A)** Replay-mode toggle in the UI header; interview fallback tested with network disabled.
- [ ] **P3-04 (U)** Final German copy review, screenshots for the deck into `docs/assets/`.
- [ ] **P3-05 (D)** `docs/demo-script.md` finalised with timings; `docs/qa-cheatsheet.md` (expected interviewer questions + answers).

**Acceptance:** all three paths demoable in under 8 minutes; docs complete; tag `v1.0-interview`.

---

## Explicitly out of scope (see docs/04_annahmen.md)

Real OpenID4VP/DC-API, real eID/AusweisApp, VideoIdent, payments/SCA, order execution, Geeignetheitsprüfung, OAuth 2.1 on MCP, multi-tenant partner banks, production hosting.
