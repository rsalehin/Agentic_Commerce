# agentic-depot — Agentenbasierte Depoteröffnung (Prototype)

Prototype for the TRUSTEQ case study **"Agentic Commerce im Finanzvertrieb"**. A
customer's AI agent opens a **Wertpapierdepot** at a fund company end-to-end with a
verified provider identity, a signed user mandate, wallet-based identification
(SD-JWT VC), a law-citing rules engine, a hash-chained audit trail, and a
human-in-the-loop escalation path — shown in a split-screen UI.

Three scenarios run live and offline: **lena → `DEPOT_OPENED`** (happy path),
**marco → `ADVISED_HANDOFF`** (two adviser escalations) and
**sanction_test → `REJECTED`** (a confidential § 47 sanctions case — compliance
rejects; the customer/agent only sees `IN_REVIEW`).

---

## 1. Prerequisites

| Tool | Version | Notes |
|---|---|---|
| **Python** | 3.12.x | the project pins `>=3.12,<3.13` |
| **uv** | ≥ 0.11 | env + dependency manager — https://docs.astral.sh/uv/ |
| **Node.js + npm** | Node ≥ 20 | only needed for the UI |
| Docker (optional) | any recent | only for the `docker compose` path |

Windows is the primary target (PowerShell). The `Bash` steps below also work in
Git Bash / WSL / macOS / Linux — swap `.\run.ps1` for the manual commands in §4.

Install uv on Windows (PowerShell), if you don't have it:
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

---

## 2. One-time setup

From the repo root:
```powershell
uv sync                      # creates .venv and installs everything (incl. dev tools)
copy .env.example .env       # optional; defaults already work
```
`uv sync` also fetches Python 3.12 automatically if needed. Key material
(Ed25519 keys for the mock issuer, provider and each persona) is **generated on
first run** into `fixtures/keys/` (gitignored) — you don't create it by hand.

For the UI (first time only):
```powershell
cd ui
npm install
cd ..
```

`.env` (all optional — the defaults match the code):
```
GATEWAY_PORT=8080
WALLET_PORT=8081
CORE_PORT=8082
UI_PORT=5174
PROVIDER_DOMAIN=https://fonds-ag.example
IDENTITY_VERIFIER=wallet_sdjwt   # or eid_stub (deprecation-swap demo)
AGENT_LLM_PROVIDER=anthropic     # or deepseek; the demo uses the recorded replay, no key needed
AGENT_MODEL=claude-sonnet-5
ANTHROPIC_API_KEY=               # only if you wire a live LLM run (not needed for the demo)
```

---

## 3. Run it — three ways

### A) Fastest: UI only, fully offline (no backend, no network)
Best for a quick look or an interview with no network.
```powershell
cd ui
npm run dev
```
Open **http://localhost:5174** and use the header toggle **Replay: Lena**,
**Replay: Marco** or **Replay: Sanktion**. These render bundled recordings
(`ui/src/replay/*.json`) with no backend at all — chat on the left, Ops-Konsole
(state ribbon, hash-chained audit, adviser panel) on the right.

### B) Live demo with recorded data (recommended)
Serve a gateway pre-populated with a recorded run, then watch it in the UI.
```powershell
# terminal 1 — gateway on :8080, already populated with the lena session
uv run python -m agent.replay.demo_server            # or: ... demo_server marco 8080

# terminal 2 — the UI
cd ui
npm run dev
```
Open **http://localhost:5174** (header on **Live**). The Ops-Konsole shows the
provider "verifiziert" badge, the state machine, and the audit trail streamed
from the gateway via SSE (`/events`).

### C) Full stack + drive a run live
Start all four services, then drive a recorded transcript through the **running**
gateway over HTTP and watch the UI fill in live.
```powershell
.\run.ps1
```
`run.ps1` checks the four ports, starts gateway/wallet/core (each with a
`/health` endpoint) and the Vite UI, and prints whether each is healthy. If a
port is busy it prints the exact `taskkill` command instead of failing silently.

Then, in another terminal, drive a scenario (no LLM call — the agent's tool-call
decisions are replayed; crypto and the audit are real):
```powershell
uv run python -m agent.replay lena          http://localhost:8080
uv run python -m agent.replay marco         http://localhost:8080
uv run python -m agent.replay sanction_test http://localhost:8080
```
Watch **http://localhost:5174** (Live) populate as the events stream in. The
three scenarios end in **`DEPOT_OPENED`** (lena), **`ADVISED_HANDOFF`** (marco)
and **`REJECTED`** (sanction_test — a confidential § 47 sanctions case: the
customer/agent only ever sees "Ihr Antrag wird geprüft." / `IN_REVIEW`, while
compliance rejects it in the Ops-Konsole).

> The demo is driven by the recorded replay so it is deterministic and
> network-independent. A real-LLM run would use the Anthropic provider
> (`AGENT_LLM_PROVIDER=anthropic`, `ANTHROPIC_API_KEY=…`) via `agent/`, but is not
> required — and is deliberately not wired into the one-command demo.

### D) Interactive from the UI (P3-07)
`run.ps1` also starts the **runner** service on `:8083`. In the UI header, pick a
persona (**Lena · Marco · Sanktion**) and click **Start**: the run appears in the
Kundenchat and pauses at each human-only step. Click **Signieren** to continue or
**Ablehnen** to stop.

- **Lena** → Signieren the mandate, tax and contract → **`DEPOT_OPENED`**, "✓ Kette gültig".
- **Ablehnen at the tax step** → the gateway session is cancelled → **`CANCELLED`**
  in the state ribbon and the audit trail. (Declining at the *first* prompt is the
  privacy-correct variant: nothing was ever sent to the provider, so there is no
  session — the chat says so and no audit trail is created.)
- **Marco** → Signieren mandate + tax → **`ADVISED_HANDOFF`** (adviser decisions
  applied); **Sanktion** → **`REJECTED`** (confidential § 47).

The runner replays the recorded tool-call decisions (no LLM); with
`VITE_ENABLE_LIVE=1` a **Start (LLM)** button drives the same flow via the
Anthropic provider (needs `ANTHROPIC_API_KEY`). The terminal `agent.replay`
commands above remain the deterministic fallback — the runner is additive.

---

## 4. Run services individually (without run.ps1)

Each backend is `python -m <pkg>.app` and reads its port from the environment:
```powershell
uv run python -m gateway.app      # :8080  (Agent Card, /mcp, /v1/..., /events, /sessions)
uv run python -m wallet.app       # :8081  (issuer JWKS, /revocations)
uv run python -m core.app         # :8082  (health)
cd ui; npm run dev                # :5174  (strictPort)
```
Health checks:
```bash
curl http://localhost:8080/health
curl http://localhost:8080/.well-known/agent-card.json
```

---

## 5. Tests & checks (the definition of done)
```powershell
uv run pytest            # 144 tests
uv run ruff check .
uv run mypy gateway
cd ui; npm run build     # type-checks (tsc) + bundles the UI
```

---

## 6. Docker (optional, not build-verified here)
A `Dockerfile` + `docker-compose.yml` are provided (compose config validates);
the image build has not been run in this environment, so treat it as untested:
```powershell
docker compose up --build
```
This builds one shared Python image for gateway/wallet/core (with `/health`
healthchecks) and runs the Vite UI in a Node container.

---

## 7. Ports

| Service | Port | Health |
|---|---|---|
| gateway | 8080 | `GET /health` |
| wallet  | 8081 | `GET /health` |
| core    | 8082 | `GET /health` |
| ui (Vite) | 5174 | dev server (strictPort) |

---

## 8. Useful extras
- **Deprecation swap** (ports & adapters): `IDENTITY_VERIFIER=eid_stub` swaps the
  wallet SD-JWT verifier for an eID stub with no gateway code change.
- **Nachweis / evidence** (machine-readable proof): `GET /sessions/{id}/evidence`
  maps each rule to the evidence (law + sha256) that satisfied it (JSON export).
- **Regenerate** after changing keys/specs:
  `uv run python -m wallet.keys` (keys + public JWKS) and
  `uv run python -m agent.replay.export_ui_bundle` (offline UI bundles).
- **Rules catalogue** as Markdown: `uv run python -m gateway.rules.export_md`.

---

## 9. Windows notes
- The virtualenv is `.venv` (with the dot). `run.ps1` uses `.\.venv\Scripts\python.exe`.
- Vite uses `strictPort: true` on 5174 — it will not silently pick another port.
- Port conflict? `run.ps1` prints the `taskkill /PID <pid> /F` line to run.
- Do not commit `.env` (gitignored) or `fixtures/keys/` (gitignored); the public
  JWKS `fixtures/jwks.public.json` is committed.

---

## 10. Layout & docs
Code layout: see `CLAUDE.md` §4. Specs and interview deliverables are in `docs/`
(`00`–`07` specs, `decisions/` ADR-01..12, `demo-script.md`, `qa-cheatsheet.md`,
`assets/` screenshot guide). Progress: `ROADMAP.md` (all phases complete;
tag `v1.0-interview`).
