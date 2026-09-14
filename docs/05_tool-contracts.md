# 05 — Tool Contracts (source of truth for gateway ↔ agent)

All gateway tools are exposed via FastMCP (Streamable HTTP, `/mcp`). Every request carries `session_id` (except `onboarding.start`) and the mandate JWS in the `mandate` field or the MCP request metadata `x-mandate`. Every response has the envelope:

```json
{ "ok": true, "state": "IDENTIFIED", "data": {…}, "rules": [ {"id":"R-ID-01","outcome":"OK","law":"GwG §12 Abs. 1"} ], "reason_codes": [], "human_required": false, "next_tool": "onboarding.tax_declaration" }
```
On error: `{ "ok": false, "error": { "code": "MANDATE_SCOPE_EXCEEDED", "message_de": "…", "detail": {…} } }`.

## 1. Agent Card (`GET /.well-known/agent-card.json`)

A2A v1.0-shaped card with a JWS signature over the JCS-canonicalised card (without `signatures`). Minimal fields:

```json
{
  "name": "Fonds AG Depoteröffnung",
  "description": "Agentenfähige Depoteröffnung der Fonds AG (Mock).",
  "version": "1.0.0",
  "provider": { "organization": "Fonds AG (Demo)", "url": "https://fonds-ag.example", "lei": "5299000MOCK000000001", "bafin_id": "MOCK-123456", "custodian": "Fonds AG Depotbank (Mock)" },
  "supportedInterfaces": [ { "protocol": "mcp", "url": "http://localhost:8080/mcp", "version": "2025-06-18" } ],
  "capabilities": { "onboarding": "v1", "documents": "v1", "escalation": "v1" },
  "securitySchemes": { "mandate": { "type": "http", "scheme": "bearer", "bearerFormat": "JWS-Mandate/v1" } },
  "skills": [ { "id": "onboarding.v1", "name": "Depoteröffnung", "description": "…", "inputModes": ["application/json"], "outputModes": ["application/json"] } ],
  "termsManifest": "http://localhost:8080/terms-manifest.json",
  "aiDisclosure_de": "Sie interagieren mit einem automatisierten System der Fonds AG (Art. 50 KI-VO).",
  "signatures": [ { "protected": "<b64url header {alg:EdDSA,kid:fonds-ag-2026,jku:…/jwks.json}>", "signature": "<b64url>" } ]
}
```

`terms-manifest.json` lists every data field the provider will request with its legal basis (`{"field":"tax_id","law":"AO §139b","purpose":"Kapitalertragsteuer"}`) — the agent shows this to the human before creating the mandate.

**Card fingerprint.** `card_fingerprint` (used in `onboarding.start`, `mandate.agent.card_fingerprint`, and `R-MND-04`) is defined as `sha256(JCS-canonical card without the "signatures" field)`, base16, prefixed `sha256:`. The agent computes it over the card it verified; the gateway computes it over its own served card; `R-MND-04` requires the two to match.

## 2. Intent Mandate (signed by the customer's holder key)

Compact JWS (`alg: EdDSA`, `kid: <holder kid>`), payload:

```json
{
  "iss": "did:key:z6Mk…lena",            // holder
  "sub": "did:key:z6Mk…lena",
  "aud": "https://fonds-ag.example",     // provider domain from the verified card
  "iat": 1757844000, "exp": 1757930400, "jti": "mnd_…",
  "agent": { "id": "agent:kundenagent-demo", "provider": "Anthropic Claude (Demo)", "card_fingerprint": "sha256:…" },
  "purpose": "depot_opening",
  "scope": {
    "product_classes": ["fonds", "etf"],
    "monthly_amount_max": { "value": 200, "currency": "EUR" },
    "one_off_amount_max": { "value": 0, "currency": "EUR" },
    "advice_allowed": false,
    "data_release": ["pid.given_name","pid.family_name","pid.birth_date","pid.birth_place","pid.birth_place_country","pid.nationalities","pid.address","pid.tax_id","pid.national_id_number"]
  },
  "human_only": ["tax_declaration", "sign_contract"],
  "revocation_url": "http://localhost:8081/revocations"
}
```

The gateway verifies: signature against holder JWK (from the PID's `cnf` after identification; before that from the mandate `iss` DID), `aud` equals its own domain, `exp`, `jti` not consumed (consume-once for `onboarding.start`), and that every later call stays within `scope`. At `onboarding.identify` the PID key binding (`cnf`) MUST equal the mandate signer (`iss`); a mismatch is `HOLDER_MANDATE_MISMATCH` (`R-ID-05`, terminal `REJECT`) so an untrusted agent cannot present a third party's PID under this mandate.

## 3. Tools

### `onboarding.start`
in: `{ "mandate": "<JWS>", "card_fingerprint": "sha256:…", "agent_id": "agent:…" }`
out: `data: { "session_id": "ses_…", "requested_credentials": { "pid": ["given_name", …], "nonce": "…", "aud": "https://fonds-ag.example" }, "terms_manifest_hash": "sha256:…" }`
states: `DISCOVERED → MANDATE_VALID`. Rules: R-MND-01..04.

### `onboarding.identify`
in: `{ "session_id", "presentation": "<SD-JWT VC + KB-JWT>", "reference_account_iban": "DE89…"|null }`
`reference_account_iban` is optional (may be `null`); `R-ID-04` (reference-account name match) is evaluated only when it is supplied.
out: `data: { "kyc": { "given_name","family_name","birth_date","birth_place","birth_place_country","nationalities":[…],"address":{…},"national_id_number","assurance_level":"high","issuer":"mock-bundesdruckerei" }, "screening": { "sanctions":"clear|hit","pep":"clear|hit" } }`
states: `MANDATE_VALID → IDENTIFIED → SCREENED` (or `HUMAN_REQUIRED`, or `REJECTED` on `R-AML-01`/`R-ID-05`). Rules: R-ID-01..05, R-AML-01..03.

### `onboarding.tax_declaration` (human-only)
in: `{ "session_id", "declaration": { "tax_id": "12 345 678 901", "residencies": [{"country":"DE","tin":"…"}], "us_person": false, "church_tax_query_consent": true, "freistellungsauftrag_eur": 1000 }, "holder_signature": "<JWS over canonical(declaration) with aud+session_id+nonce>" }`
out: `data: { "kistam": { "status": "queried", "result": "ev|rk|none" }, "residency_status": "DE_ONLY" }`
states: `SCREENED → TAX_CONFIRMED` (or `HUMAN_REQUIRED`). Rules: R-TAX-01..04.

### `onboarding.appropriateness`
in: `{ "session_id", "profile": { "experience": { "fonds": {"years":2,"trades_per_year":12}, "aktien": {"years":0}, "zertifikate": {"years":0}, "derivate": {"years":0} }, "education": "…", "occupation": "…", "requested_classes": ["fonds","etf"], "advice_requested": false } }`
out: `data: { "unlocked_classes": ["fonds","etf"], "blocked_classes": ["zertifikate","derivate"], "warnings_de": ["…"], "execution_only_notice_de": "…" }`
states: `TAX_CONFIRMED → APPROPRIATENESS_DONE` (or `HUMAN_REQUIRED`). Rules: R-WPHG-01..03.

### `onboarding.get_documents`
in: `{ "session_id", "plan": { "monthly_amount": {"value":150,"currency":"EUR"}, "product_isin": "DE000MOCK0001" } }`
out: `data: { "bundle_id", "bundle_hash": "sha256:…", "documents": [ {"type":"agb","title_de":"…","url":"…","hash":"…"}, {"type":"basisinformationen"}, {"type":"kosteninformation_ex_ante","summary_de":"…","total_cost_year1_eur":…}, {"type":"basisinformationsblatt","isin":"…"}, {"type":"widerrufsbelehrung"}, {"type":"datenschutz"} ], "contract": { "contract_hash": "sha256:…", "summary_de": "…" } }`
states: `APPROPRIATENESS_DONE → INFORMED`.

### `onboarding.sign_contract` (human-only)
in: `{ "session_id", "contract_hash": "sha256:…", "holder_signature": "<JWS over {contract_hash, bundle_hash, session_id, aud}>", "qes_mock": true }`
out: `data: { "depot": { "depot_number": "1234567890", "verrechnungskonto_iban": "DE89…", "opened_at": "…", "custodian": "Fonds AG Depotbank (Mock)" }, "withdrawal_deadline": "2026-09-28" }`
states: `INFORMED → CONTRACT_SIGNED → DEPOT_OPENED`. Rules: R-CTR-01.

### `onboarding.status`
in: `{ "session_id" }` — out: `data: { "state", "blocked_from", "reason_codes", "escalation": {…}|null, "audit_chain_ok": true }`.

## 4. Agent-local tools (not exposed by the gateway)

- `wallet.present_pid(requested_claims, nonce, aud)` → SD-JWT VC presentation.
- `wallet.sign(payload, purpose)` → holder JWS (used for mandate, tax declaration, contract). **Only callable after `ask_human` returned approval for that payload.**
- `ask_human(question_de, payload_to_confirm?)` → `{ "approved": bool, "answer": str }` — rendered as buttons in the chat UI; in replay mode answered from the recording.
- `discovery.verify(url)` → `{ "verified": bool, "card": {...}, "fingerprint": "sha256:…" }`.

## 5. Error codes

`WRONG_STATE`, `MANDATE_INVALID`, `MANDATE_EXPIRED`, `MANDATE_SCOPE_EXCEEDED`, `MANDATE_REVOKED`, `AGENT_UNVERIFIED`, `PRESENTATION_INVALID`, `SIGNATURE_INVALID`, `HUMAN_REQUIRED` (with reason codes), `REJECTED`, `INTERNAL`.

## 6. Ops/adviser HTTP API (Phase 2)

`GET /escalations`, `GET /escalations/{id}`, `POST /escalations/{id}/decision {"decision":"approve|request_appointment|reject","note":"…","adviser":"…"}`, `GET /sessions/{id}`, `GET /sessions/{id}/evidence`, `GET /events` (SSE).
