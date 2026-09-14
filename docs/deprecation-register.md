# Deprecation Register

| Component / standard | Status today (09/2026) | Expected change | Impact on us | Mitigation |
|---|---|---|---|---|
| VideoIdent (BaFin RS 3/2017) | Market standard for remote ID | AMLR 10.07.2027: only justified exception | None (not used) | Documented as rejected option (ADR-03) |
| eID / Online-Ausweis | Available, low adoption | Basis of German EUDI Wallet | Fallback path | `eid_stub` adapter |
| EUDI Wallet (DE) | Planned 01/2027, DIdG in cabinet 05/2026 | Private wallets ~12 months later | Core dependency of ADR-03 | Mock now; interface follows OpenID4VP/SD-JWT VC |
| MCP | Stable; OAuth 2.1 since 01/2026 | Spec revisions quarterly | Tool transport | Version pinned in card; FastMCP upgrade path |
| A2A | v1.0 (03/2026), signed cards | Task API evolution | Discovery only | `AgentDiscovery` port |
| AP2 | v0.2, donated to FIDO 04/2026 | Governance/spec change likely | Mandate shape inspiration only | Own mandate schema, adapter if AP2 stabilises |
| ACP / UCP | Beta | Consolidation expected | Not used | – |
| Visa TAP / Mastercard Agent Pay | Live for cards | Might cover account onboarding? | Not used | Payment out of scope |
| PSD2 → PSD3/PSR | Draft | 2027+ | SCA model for later phases | Out of scope |
| Fernabsatz-RL (EU) 2023/2673 | Applies from 06/2026 | Widerrufsbutton, chatbot duties | Document bundle content | `widerrufsbelehrung` doc type |
| AI Act Art. 50 | Applies 08/2026 | Guidelines evolving | Agent disclosure text | System prompt + card `provider` fields |
