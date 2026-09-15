# docs/assets — deck screenshots

Screenshots for the PowerPoint. Capture them from the split-screen UI in
**replay mode** (self-contained, no backend needed), so they are reproducible
and network-independent.

## Capture setup
```powershell
cd ui
npm install      # first time only
npm run dev      # http://localhost:5174
```
The header toggle switches source: **Live** (SSE from a running gateway) or
**Replay: Lena / Replay: Marco** (bundled recordings, offline). Use replay for
stable, identical captures. Recommended browser viewport: **1440×900**,
100% zoom, light theme.

Regenerate the bundles after any spec/keys change:
```powershell
uv run python -m agent.replay.export_ui_bundle
```

## Shot list (filenames referenced by the deck)
| File | View | How |
|---|---|---|
| `01-lena-happy.png` | Lena → `DEPOT_OPENED`: chat left, state ribbon + audit trail right | Replay: Lena; scroll so the ribbon + "Kette gültig" are visible |
| `02-ops-audit.png` | Ops-Konsole close-up: provider "verifiziert" badge, hash-chained audit | Replay: Lena; scroll the right pane to the Audit-Trail |
| `03-marco-review.png` | Marco in `REVIEW_REQUIRED`: chat "Ihr Antrag wird geprüft" + adviser panel with the rule citation and decision buttons | **Live** (`uv run python -m agent.replay.demo_server` stops before the appointment) *or* pause a live run at the tax review |
| `04-marco-handoff.png` | Marco → `ADVISED_HANDOFF`: "An die Partnerbank-Beraterin übergeben" + resolved escalations | Replay: Marco |
| `05-negative-scope.png` | Manipulation: over-limit call → red `MANDATE_SCOPE_EXCEEDED` guard event (from==to) | Live; drive an over-limit `get_documents` |
| `06-nachweis.png` | Nachweis JSON (`GET /sessions/{id}/evidence`): rule → law → evidence hash | Live; open the endpoint or show the exported `nachweis-*.json` |

## Notes
- Colours/typography are the TRUSTEQ tokens (`ui/src/theme.ts`, navy/gold/Karla)
  — do not restyle for the deck.
- The audit "Kette gültig" badge and the sha256 hashes are the money shot for the
  "maschinenlesbarer Nachweis" slide.
- `03/05/06` need a live gateway (`.\run.ps1` or `python -m agent.replay.demo_server`);
  `01/02/04` work fully offline in replay mode.
