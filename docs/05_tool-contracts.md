# 05 — Tool Contracts (source of truth for gateway ↔ agent)

## 0. API-first; MCP is an adapter

The **canonical contract is a versioned REST/OpenAPI surface**. MCP tools (FastMCP, Streamable HTTP, `/mcp`) and, later, A2A are **1:1 adapters over the same command handlers**. A raw HTTP request and an MCP call with identical payloads MUST produce identical policy decisions and audit events (tested in P1-08).

| REST | MCP tool |
|---|---|
| `POST /v1/onboarding/start` | `onboarding.start` |
| `POST /v1/onboarding/{sid}/identify` | `onboarding.identify` |
| `POST /v1/onboarding/{sid}/tax` | `onboarding.tax_declaration` |
| `POST /v1/onboarding/{sid}/appropriateness` | `onboarding.appropriateness` |
| `POST /v1/onboarding/{sid}/documents` | `onboarding.get_documents` |
| `POST /v1/onboarding/{sid}/confirm` | `onboarding.sign_contract` |
| `GET  /v1/onboarding/{sid}` | `onboarding.status` |
| `GET  /v1/onboarding/{sid}/opening/{operation_id}` | `onboarding.get_opening_status` |

Every request (except `onboarding.start`, which has no `session_id`) carries `session_id`, the mandate JWS (field `mandate` or MCP metadata `x-mandate`), and a sender proof (header/metadata `x-sender-proof`, §2.2). Response envelope:

```json
{ "ok": true, "state": "IDENTIFIED", "data": {…},
  "rules": [ {"id":"R-ID-01","outcome":"ALLOW","law":"GwG §12 Abs. 1"} ],
  "policy_version": "1.1.0", "reason_codes": [], "outcome": "ALLOW",
  "next_tool": "onboarding.tax_declaration" }
```
On error / guard rejection: `{ "ok": false, "error": { "code": "MANDATE_SCOPE_EXCEEDED", "message_de": "…", "detail": {…} } }`.
For a confidential AML review (GwG § 47) the envelope is masked: `outcome: "REQUIRE_REVIEW"`, `reason_codes: ["IN_REVIEW"]`, text "Ihr Antrag wird geprüft." — the real codes live only in the Ops console and audit log.

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

**JWKS role separation.** The gateway's `GET /.well-known/jwks.json` serves the **provider** key only (`fonds-ag-2026`). The credential **issuer** key (`mock-bundesdruckerei`) is served by the wallet at its own origin (`WALLET/.well-known/jwks.json`, used to verify the SD-JWT VC in §onboarding.identify). Customer **holder** keys are `did:key` (self-certifying) and are never served by the provider. `fixtures/jwks.public.json` bundles all keys only as a test aggregate (role-tagged).

**Trust anchor is the verified provider directory, not the card's own key.** A card whose key is served from the same domain proves domain control (like TLS), not that the domain is the regulated Depot contracting party. The agent therefore verifies the card signature against the **pinned kid from `fixtures/provider-directory.json`** for that domain; the `jku` in the signature header is not trusted for key discovery. See §5.

**Card fingerprint.** `card_fingerprint = "sha256:" + hex(sha256(JCS(card without "signatures")))`. The agent computes it over the verified card; the gateway over its own served card; `R-MND-04` requires the call's `card_fingerprint` **and** the mandate-embedded `agent.card_fingerprint` (what the human approved) to both equal the gateway's.

`terms-manifest.json` lists every requested data field with its legal basis (`{"field":"tax_id","law":"AO §139b","purpose":"Kapitalertragsteuer"}`) — shown to the human before the mandate is created.

## 2. Intent Mandate (signed by the customer's holder key)

Compact JWS (`alg: EdDSA`, header `kid: "holder-<persona>"`), payload:

```json
{
  "iss": "did:key:z6Mk…lena",            // holder (did:key = the signing public key)
  "sub": "did:key:z6Mk…lena",
  "aud": "https://fonds-ag.example",     // provider domain from the verified directory/card
  "iat": <now>, "exp": <now+ttl>, "jti": "mnd_…",
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

`iat`/`exp` are minted dynamically (never the literal epochs above). The mandate builder wraps a persona's scalar `monthly_amount_max` as `{value, "EUR"}` and fills `data_release` from this default set.

The gateway verifies: signature against the holder JWK (from the PID's `cnf` after identification; before that from the mandate `iss` `did:key`), `aud` == its own domain, `exp`, `jti` not consumed (consume-once for `onboarding.start`), and that every later call stays within `scope`. At `onboarding.identify` the PID key binding (`cnf`) MUST be the **same key material** as the mandate signer (`iss`) — compared as `did:key(cnf) == iss`, not as `kid` labels; a mismatch is `HOLDER_MANDATE_MISMATCH` (`R-ID-05`, `DENY`).

### 2.2 Agent client registration and sender binding

The mandate is the customer's **legal authorisation evidence**; client registration + sender binding are the **technical access control** (ADR-02).

- `fixtures/agent-clients.json`: registered clients `{ client_id, operator_name, instance_jwk, status: active|blocked }`.
- Every call carries `x-sender-proof`: a compact JWS signed by the agent **instance** key over `{ htm, htu, session_id, iat, jti }` (DPoP-shaped, simplified). The gateway checks: client registered and `active` (`R-MND-05` → `CLIENT_UNREGISTERED`); proof signature valid, `jti` unused, `iat` within 60 s, and `mandate.agent.id == proof.client_id` (`R-MND-06` → `SENDER_BINDING_INVALID`). Both are `ERROR` guards.
- **Revocation on writes:** every state-changing call re-checks the mandate `revocation_url` and the client status; a hit is `MANDATE_REVOKED` (`R-MND-03`, `DENY`).

## 3. Tools

### `onboarding.start`
in: `{ "mandate": "<JWS>", "card_fingerprint": "sha256:…", "agent_id": "agent:…", "referral_receipt": "<JWS>"|null }`
out: `data: { "session_id": "ses_…", "requested_credentials": { "pid": ["given_name", …], "nonce": "…", "aud": "https://fonds-ag.example" }, "terms_manifest_hash": "sha256:…" }`
`referral_receipt` (§2.4) is optional; an invalid/foreign one is ignored with audit note `REFERRAL_INVALID` and never blocks. states: `DISCOVERED → MANDATE_VALID`. Rules: R-MND-01..06.

### `onboarding.identify`
in: `{ "session_id", "presentation": "<SD-JWT VC + KB-JWT>", "reference_account_iban": "DE89…"|null }`
`reference_account_iban` is optional; `R-ID-04` is evaluated only when supplied.
out: `data: { "kyc": { "given_name","family_name","birth_date","birth_place","birth_place_country","nationalities":[…],"address":{…},"national_id_number","assurance_level":"high","issuer":"mock-bundesdruckerei" }, "screening": { "sanctions":"clear|hit","pep":"clear|hit" } }`
states: `MANDATE_VALID → IDENTIFIED → SCREENED` (or `CUSTOMER_REQUIRED` on `R-ID-01`; `REVIEW_REQUIRED` on `R-ID-02..04`/`R-AML-*`; `REJECTED` on `R-ID-05`). Rules: R-ID-01..05, R-AML-01..03. AML reviews are masked to `IN_REVIEW`.

### `onboarding.tax_declaration` (human-only)
in: `{ "session_id", "declaration": { "tax_id": "12 345 678 901", "residencies": [{"country":"DE","tin":"…"}], "us_person": false, "church_tax_query_consent": true, "freistellungsauftrag_eur": 1000 }, "holder_signature": "<JWS over canonical(declaration) with aud+session_id+nonce>" }`
out: `data: { "kistam": { "status": "queried", "result": "ev|rk|none" }, "residency_status": "DE_ONLY" }`
states: `SCREENED → TAX_CONFIRMED` (or `CUSTOMER_REQUIRED` on R-TAX-01/04; `REVIEW_REQUIRED` on R-TAX-02/03). Rules: R-TAX-01..04.

### `onboarding.appropriateness`
in: `{ "session_id", "profile": { "experience": { "fonds": {"years":2,"trades_per_year":12}, "aktien": {"years":0}, "zertifikate": {"years":0}, "derivate": {"years":0} }, "education": "…", "occupation": "…", "requested_classes": ["fonds","etf"], "advice_requested": false } }`
out: `data: { "service_mode": "account_only|non_advised|advised", "unlocked_classes": ["fonds","etf"], "blocked_classes": ["zertifikate","derivate"], "warnings_de": ["…"], "execution_only_notice_de": "…" }`
`service_mode` (R-SVC-01): `account_only` when `requested_classes` empty (appropriateness `NOT_REQUIRED`, reason recorded), else `non_advised`; `advised` routes to review via R-WPHG-02. states: `TAX_CONFIRMED → APPROPRIATENESS_DONE` (or `CUSTOMER_REQUIRED` on R-WPHG-01; `REVIEW_REQUIRED` on R-WPHG-02/03). Rules: R-SVC-01, R-WPHG-01..03.

### `onboarding.get_documents`
in: `{ "session_id", "plan": { "monthly_amount": {"value":150,"currency":"EUR"}, "product_isin": "DE000MOCK0001" } }`
out: `data: { "bundle_id", "revision", "product_version", "pricing_version", "snapshot_digest": "sha256:…", "documents": [ {"type":"agb","title_de":"…","url":"…","hash":"…"}, {"type":"basisinformationen"}, {"type":"kosteninformation_ex_ante","summary_de":"…","total_cost_year1_eur":…}, {"type":"basisinformationsblatt","isin":"…"}, {"type":"widerrufsbelehrung"}, {"type":"datenschutz"} ], "contract": { "summary_de": "…" } }`
`snapshot_digest = sha256(JCS({session_id, revision, product_id, product_version, pricing_version, document_hashes[], plan}))` — an immutable snapshot the customer confirms. states: `APPROPRIATENESS_DONE → INFORMED`.

### `onboarding.sign_contract` (human-only; REST `/confirm`)
in: `{ "session_id", "snapshot_digest": "sha256:…", "holder_signature": "<JWS over {snapshot_digest, session_id, aud}>", "idempotency_key": "…", "qes_mock": true }`
out: `data: { "depot": { "depot_number": "1234567890", "verrechnungskonto_iban": "DE89…", "opened_at": "…", "custodian": "Fonds AG Depotbank (Mock)" }, "operation_id": "…", "withdrawal_deadline": "2026-09-28" }`
The gateway recomputes the current `snapshot_digest`; a mismatch → `SNAPSHOT_STALE` (`R-CTR-02`, `REQUIRE_CUSTOMER`) and a fresh bundle is issued. An identical `idempotency_key` replay returns the stored result (same Depot number); the same key with a different payload → HTTP 409. states: `INFORMED → CUSTOMER_CONFIRMED → BANK_ACCEPTED → PROVISIONING → DEPOT_OPENED` (or `RECONCILING` on `PROVISIONING_UNCERTAIN`). Rules: R-CTR-01, R-CTR-02.

### `onboarding.get_opening_status`
in: `{ "session_id", "operation_id" }` — out: `data: { "state", "depot": {…}|null }`. Resolves `RECONCILING` without a second create.

### `onboarding.status`
in: `{ "session_id" }` — out: `data: { "state", "blocked_from", "reason_codes" (masked for AML), "service_mode", "escalation": {…}|null, "audit_chain_ok": true }`.

**Lifecycle terminals.** A customer may `cancel` before `CUSTOMER_CONFIRMED` → `CANCELLED`; a mandate/session deadline → `EXPIRED`; an adviser `request_appointment` → `ADVISED_HANDOFF`; an adviser/compliance `reject` → `REVIEW_REJECTED` → `REJECTED` (see `docs/03`).

## 2.4 Channel attribution on the Application

`Application` carries `origin_channel` (`agent|web|app|branch`), `servicing_partner_id`, `current_channel`, `commercial_attribution_ref`, and optional `referral_receipt`. The receipt is a JWS signed by the partner-bank key (`fixtures/keys/volksbank-leipzig`) over `{ partner_id, product_id, sub (customer did), exp, jti }`, supplied to `onboarding.start`. Invalid/foreign → ignored, audit note `REFERRAL_INVALID`, never blocks opening. The same application ID continues across branch/app/agent; commission logic stays in existing settlement systems (ADR-07).

## 4. Agent-local tools (not exposed by the gateway)

- `discovery.verify(url)` → `{ "verified": bool, "card": {...}, "fingerprint": "sha256:…", "reason": "PROVIDER_UNVERIFIED|CARD_SIGNATURE_INVALID|ONBOARDING_UNSUPPORTED"|null }`. Steps: (1) the domain in the card's `provider.url` must be in `fixtures/provider-directory.json` (else `PROVIDER_UNVERIFIED`); (2) the card signature must verify against the **pinned key** for that domain, loaded from a trusted local keystore by `pinned_kid` (not the JWKS the card points to), and the signature's `kid` must equal `pinned_kid` (else `CARD_SIGNATURE_INVALID`) — this refuses both a lookalike domain and a same-domain key substitution; (3) the trusted card must advertise `onboarding.v1` in `skills[]`, `capabilities.onboarding=="v1"` and an `mcp` `supportedInterfaces` entry (else `ONBOARDING_UNSUPPORTED`); (4) no PII is sent before `verified=true`.
- `wallet.present_pid(requested_claims, nonce, aud)` → SD-JWT VC presentation (selective disclosure + KB-JWT).
- `wallet.sign(payload, purpose)` → holder JWS (mandate, tax declaration, snapshot). **Only callable after `ask_human` approved that payload.**
- `ask_human(question_de, payload_to_confirm?, mode?)` → `{ "approved": bool, "answer": str }`. `mode: "warning_ack"` handles a `PRODUCT_OUTSIDE_UNLOCKED` §63(10) warning (customer acknowledges or drops the class). Rendered as buttons; in replay mode answered from the recording.

## 5. Error / reason codes

Envelope error codes: `WRONG_STATE`, `MANDATE_INVALID`, `MANDATE_EXPIRED`, `MANDATE_SCOPE_EXCEEDED`, `MANDATE_REVOKED`, `AGENT_UNVERIFIED`, `CLIENT_UNREGISTERED`, `SENDER_BINDING_INVALID`, `PRESENTATION_INVALID`, `SIGNATURE_INVALID`, `SNAPSHOT_STALE`, `PROVISIONING_UNCERTAIN`, `REJECTED`, `INTERNAL`. Discovery (agent-side): `PROVIDER_UNVERIFIED`, `CARD_SIGNATURE_INVALID`, `ONBOARDING_UNSUPPORTED`. Policy reason codes and outcomes: see `docs/03` (`IN_REVIEW` is the masked AML value; `REVIEW_REJECTED` is the terminal compliance/adviser DENY).

## 6. Ops/adviser HTTP API (Phase 2)

`GET /escalations` (two queues: `customer` vs `review`; `review` split adviser/compliance), `GET /escalations/{id}`, `POST /escalations/{id}/decision {"decision":"approve|request_appointment|reject","note":"…","actor":"adviser|compliance"}`, `GET /sessions/{id}`, `GET /sessions/{id}/evidence`, `GET /events` (SSE).
