# docs/ — index

| File | Purpose | Feeds |
|---|---|---|
| 00_build-plan.md | Accepted MVP plan (scenario, architecture, phases) | ROADMAP, deck |
| 01_ist-analyse.md | Research on today's Depot opening, regulation, roles, friction | Deck part 1, Q&A |
| 02_zielkonzept.md | Target architecture 2030 with diagrams (fill during Phase 1) | Deck part 2 |
| 03_state-machine.md | States, transitions, reason codes, audit event — **source of truth** | gateway/state.py |
| 04_annahmen.md | Assumptions and out-of-scope list | Deck, Q&A |
| 05_tool-contracts.md | Agent Card, mandate, MCP tool I/O, error codes — **source of truth** | gateway/tools, agent |
| 06_rules.md | Human-readable rules catalogue (generated from gateway/rules/rules.yaml, v1.1.0) | Deck, Q&A |
| 07_dossier-contrast.md | Our plan vs. the external research dossier (merge decisions) | P1-00, Q&A |
| P1-00_spec-update.md | Spec-update decisions applied before Phase 1 (from 07) | ROADMAP P1-00 |
| test-plan.md | Adversarial/negative-test backlog (dossier T-cases → our reason codes) | Phases 1–3 |
| decisions/ | ADR-01..12 = Entscheidungslog required by the case | Deck |
| deprecation-register.md | Standards and their expected end-of-life | ADR-10, deck |
| demo-script.md | 10-minute presentation + live demo script (with timings) | Interview |
| qa-cheatsheet.md | Expected interviewer questions + answers (DE) | Interview |
| assets/ | Deck screenshots + capture guide | Deck |
| glossar.md | DE/EN glossary | Everyone |

Rule: change a source-of-truth doc first, then the code, in the same commit.
