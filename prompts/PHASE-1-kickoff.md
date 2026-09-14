# Phase 1 kickoff (use after Phase 0 acceptance)

Read `CLAUDE.md`, `ROADMAP.md` (Phase 1), `docs/03_state-machine.md`, `docs/05_tool-contracts.md`, `gateway/rules/rules.yaml`, `fixtures/personas.json` and `docs/decisions/ADR-01..06`.

Plan P1-01 to P1-04 first (crypto foundations: signed Agent Card, discovery/verification client, mandate signing/verification, mock wallet SD-JWT VC issue/present/verify). For each: module layout under `gateway/ports`, `gateway/adapters`, `wallet/`, `agent/`; the exact JWS header/payload shapes; negative tests (tampered card, foreign key, expired mandate, wrong audience, wrong nonce). Prefer `PyJWT` + `cryptography` (Ed25519). If `sd-jwt` does not install cleanly on Windows, implement `wallet/sdjwt.py` (JWS + `_sd` disclosures + KB-JWT) behind the same interface and note it in ADR-03.

After approval and green tests, continue with P1-05..P1-08 (core mock, rules engine, state machine + audit chain, MCP tools), then P1-09..P1-13 (agent, headless happy-path test, SSE, UI, recording). Update ADR statuses to `accepted` as you go.
