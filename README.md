# agentic-depot — Agentenbasierte Depoteröffnung (Prototype)

Prototype for the TRUSTEQ case study "Agentic Commerce im Finanzvertrieb". A customer's AI agent opens a Wertpapierdepot at a fund company end-to-end with a verified provider identity, a signed user mandate, wallet-based identification, a law-citing rules engine and a human-in-the-loop escalation path.

## Quick start (Windows)
```powershell
uv sync
.\run.ps1           # starts gateway :8080, wallet :8081, core :8082, ui :5174
```
Docker: `docker compose up` (compose file + Dockerfile are provided and the
compose config validates, but the image build has not yet been run/verified —
treat it as untested until someone runs it).

## Demo / replay (no LLM call)
```powershell
# populate a gateway with the recorded lena run and serve it for the UI (:8080)
uv run python -m agent.replay.demo_server
# then start the UI and open http://localhost:5174
cd ui; npm install; npm run dev
```
Or replay the recorded run through an already-running gateway over HTTP:
```powershell
uv run python -m agent.replay lena http://localhost:8080
```
The transcript in `fixtures/recorded_runs/lena.json` holds only the agent's
tool-call decisions; signatures/credentials are regenerated live and verified by
the real gateway (interview-safe fallback, ADR-09).

## Layout
See `CLAUDE.md` §4. Specs and interview deliverables live in `docs/`.

## Status
Phase 0 — see `ROADMAP.md`.
