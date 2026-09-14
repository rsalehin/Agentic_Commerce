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

## Layout
See `CLAUDE.md` §4. Specs and interview deliverables live in `docs/`.

## Status
Phase 0 — see `ROADMAP.md`.
