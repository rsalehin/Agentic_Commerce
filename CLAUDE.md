# CLAUDE.md — agentic-depot

Prototype for the TRUSTEQ case study **"Agentic Commerce im Finanzvertrieb"**: a customer's AI agent opens a German securities account (Wertpapierdepot) at a fund company, end-to-end, with verifiable provider identity, a signed user mandate, wallet-based identification, a deterministic compliance rules engine, and a human-in-the-loop escalation path.

This file is the contract for every session. Read it fully before touching code. Then read `ROADMAP.md` for the current phase and `docs/` for the specs.

## 1. What we are building (one paragraph)

A **Kundenagent** (LLM + tools) discovers the fund company via a **JWS-signed Agent Card**, obtains a **signed Intent Mandate** from the customer, and calls the fund company's **Agent Gateway** (FastAPI + FastMCP) through MCP tools. The gateway verifies the mandate and a **mock EUDI Wallet PID credential (SD-JWT VC)**, runs a **rules engine** (each rule cites GwG / WpHG / AO), collects human-only confirmations (tax declaration, contract signature via mock QES), creates the Depot in a **mock Depotbank core**, and pushes anything it may not decide into an **escalation queue** handled by a partner-bank adviser. A **split-screen React UI** shows the customer chat on the left and the provider's Ops-Konsole (state machine, audit trail, escalations) on the right.

Deliverables for the interview: the running demo, `docs/` (Ist-Analyse, Zielkonzept, ADRs, assumptions, deprecation register, demo script) and a PowerPoint built from those docs. **Every design decision must land in `docs/decisions/` before or with the code that implements it.**

## 2. Non-negotiable principles

1. **Policy lives in code, never in a prompt.** The gateway validates every tool call against the signed mandate and the schema. The LLM extracts arguments and talks to the human; it never decides compliance outcomes.
2. **Human-only steps are enforced by the gateway.** `onboarding.tax_declaration` and `onboarding.sign_contract` require a signature from the customer's holder key over the exact payload; the agent cannot fabricate it. Failing that → `HUMAN_REQUIRED`.
3. **Real crypto, mocked parties.** Signatures (Ed25519/ES256 JWS), SD-JWT verification and hash-chained audit logs are real. Wallet issuer, BZSt, sanctions list and the bank core are mocks with fixtures. Never "simulate" a verification by returning `True`.
4. **Every rule cites its legal basis.** `gateway/rules/rules.yaml` entries carry `law:` (e.g. `GwG §10 Abs. 1 Nr. 1`) and `outcome:` (`OK | WARN | HUMAN_REQUIRED | REJECT`). No rule without a citation.
5. **Ports before adapters.** Standards will churn. Discovery, mandate verification, identity verification and signing are Python `Protocol` interfaces in `gateway/ports/`; concrete implementations live in `gateway/adapters/`. Swapping a standard must touch one adapter and one config line.
6. **Audit everything.** Every state transition appends `AuditEvent{ts, session_id, actor, from_state, to_state, reason_codes, evidence_hash, prev_hash}`; the chain must verify.
7. **Demo must survive a dead network.** `agent/replay/` can replay recorded runs without any LLM call. Keep recordings up to date after each phase.
8. **German user-facing copy, English code and docs.** UI strings, generated customer documents and reason texts are German; identifiers, comments and `docs/` are English (German legal terms kept in bold where they are terms of art).

## 3. Stack (fixed — do not introduce alternatives without an ADR)

- Python 3.12, `uv` for env/deps (`.venv` at repo root), `ruff` + `mypy --strict` on `gateway/`, `pytest` with `pytest-asyncio`. **A single `uv`-managed project** (root `pyproject.toml`) packaging the four flat top-level packages `gateway/`, `agent/`, `wallet/`, `core/` and sharing one `.venv` — deliberately not four separately-built workspace members, because the flat layout (e.g. `gateway/rules/rules.yaml`) requires each service directory to be its own importable top-level package. Run services with `python -m <pkg>.app` from the repo root.
- Gateway: FastAPI, **FastMCP** (Streamable HTTP transport), pydantic v2, SQLModel + SQLite (`data/demo.db`), `PyJWT` + `cryptography` for JWS (Ed25519 preferred, ES256 accepted), SD-JWT via `sd-jwt` (fallback: in-house `wallet/sdjwt.py` implementing JWS + disclosures — keep the interface identical).
- Agent: Anthropic Python SDK with tool use (model configurable via `AGENT_MODEL`), official `mcp` client package; `agent/llm/` has a provider abstraction so DeepSeek (OpenAI-compatible) works too.
- UI: React 18 + Vite + TypeScript + Tailwind. `strictPort: true`, port `5174`. Data via SSE from the gateway (`/events`).
- Ports: gateway `8080`, wallet `8081`, core `8082`, UI `5174`. All configurable through `.env`; `.env.example` is committed, `.env` is not.
- One-command start: `run.ps1` (Windows) and `docker-compose.yml`. Both must work.

## 4. Repository layout

```
agentic-depot/
├── CLAUDE.md, ROADMAP.md, README.md, run.ps1, docker-compose.yml, pyproject.toml, .env.example
├── docs/            specs and the interview deliverables (see docs/README.md)
│   └── decisions/   ADR-01..10 (Entscheidungslog)
├── gateway/         FastAPI + FastMCP; rules/, ports/, adapters/, audit/, escalation/, tests/
├── agent/           orchestrator, discovery, mandate, llm/, replay/, tests/
├── wallet/          mock EUDI wallet: issuer, holder, sdjwt, qes_mock, tests/
├── core/            mock Depotbank core + stubs (bzst_kistam, sanctions, reference_account), tests/
├── ui/              React split-screen demo
└── fixtures/        personas.json, agent-card.example.json, mandate.example.json, keys/ (generated, gitignored), recorded_runs/
```

## 5. Workflow rules (how Abir works)

- **Plan mode first.** For every ROADMAP task: propose the plan (files, interfaces, tests), wait for approval, then implement. Do not start a phase without an approved plan.
- **Conventional commits**, one commit per verified step: `feat(gateway): …`, `test(wallet): …`, `docs(adr): …`. Commit only when tests pass.
- **Tests before UI.** Gateway, wallet and core logic get pytest coverage first; the UI comes after the happy path passes headless (`agent/tests/test_happy_path.py`).
- **ADR with the code.** When a task touches a decision listed in `docs/decisions/`, update that ADR (status, consequences) in the same commit.
- **Keep `docs/03_state-machine.md` and `docs/05_tool-contracts.md` as the source of truth.** If the code needs to deviate, change the doc first, in the same PR.
- After each phase: update `fixtures/recorded_runs/`, `README.md` and the demo script.

## 6. Windows rules (hard-won — do not violate)

- Never use inline Python heredocs in PowerShell; write `.py` files and run them.
- Batch/PS files are written ASCII-only (`System.IO.File::WriteAllText` with ASCII encoding when generated); no box-drawing characters in generated scripts.
- `strictPort: true` in every Vite config; never rely on port fallback.
- The virtualenv is `.venv` (with the dot). Scripts must reference it exactly.
- Port conflicts: `run.ps1` checks ports first and prints the `taskkill` command instead of failing silently.
- Backend env vars are loaded explicitly via `python-dotenv` in each service entrypoint; do not rely on npm-workspace propagation.

## 7. Definition of done per task

- Code + tests green (`uv run pytest`, `uv run ruff check .`, `uv run mypy gateway`).
- Docs updated (state machine / tool contracts / ADR as applicable).
- `run.ps1` still starts everything; the happy-path replay still passes.
- Commit message follows conventional commits and references the ROADMAP task id (e.g. `feat(gateway): P1-01 signed agent card endpoint`).

## 8. Do-not-do list

- Do not add real payment, SCA, order execution, Geeignetheitsprüfung, real OpenID4VP/DC-API, real eID, OAuth on MCP, or multi-tenant partner banks. They are documented as out of scope in `docs/04_annahmen.md`.
- Do not let the agent hold or forward raw ID data beyond what the wallet presentation returns for the session.
- Do not store private keys in the repo; generate into `fixtures/keys/` at first run (gitignored) and pin public keys in fixtures.
- Do not use LangChain/LlamaIndex/agent frameworks; the orchestrator is plain Python with the Anthropic SDK and the `mcp` client.
- Do not change the TRUSTEQ palette/typography tokens in `ui/src/theme.ts` (navy `#003366`, `#1A4775`, `#335C85`, `#001733`, gold `#AE9966`, light `#F2F2F2`; font Karla) — the UI screenshots go into the deck.

## 9. Glossary shortcuts (full list in docs/glossar.md)

Depot = securities account · KVG/Fondsgesellschaft = fund company · Depotbank = custodian bank holding the Depot · GwG = AML law · WpHG = securities trading act (MiFID II) · Angemessenheitsprüfung = appropriateness test (knowledge & experience) · Geeignetheitsprüfung = suitability test (advice only, out of scope) · KiStAM = church-tax attribute from BZSt · PID = person identification data credential in the EUDI Wallet · QES = qualified electronic signature · Mandat = signed, scoped user authorisation held by the agent.
