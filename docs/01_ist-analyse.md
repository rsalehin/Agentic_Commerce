# Ist-Analyse: How a Wertpapierdepot Is Opened in Germany Today

*Research document for the TRUSTEQ case study "Agentic Commerce im Finanzvertrieb" – written for a software engineer who is new to German financial regulation. German terms are kept (bold) because they will appear on the slides and in the Q&A.*

*Status: 12 September 2026. Everything here is a structured inventory, not legal advice – exactly what the case asks for ("keine juristische Vollanalyse").*

---

## 0. TL;DR – the five things to remember

1. **Opening a Depot is not one step, it is a chain of five legally required checks**: (1) who are you (**Identifizierung**, anti-money-laundering law), (2) where do you pay tax (**steuerliche Angaben**), (3) do you understand the product (**Angemessenheitsprüfung**, securities law), (4) have you received all mandatory information and signed the contract (**Vertragsschluss**), and only then (5) the Depot is technically opened (**Depoteröffnung**) and a settlement account is linked.
2. **Each check has its own law, its own data, and its own "proof"**. The bank cannot skip any of them, no matter how the customer arrives – via app, branch, or (in 2030) an AI agent. That is the core design constraint of the whole case.
3. **The single biggest friction point today is identity verification** (VideoIdent: ~6 € per attempt, ~30 % abort rate, waiting queues, 1–3 working days until the Depot is usable). And it is exactly the step that regulation is about to change: from **10 July 2027 the EU AML Regulation makes eIDAS-conform eID (Personalausweis online function / EUDI Wallet) the standard** and VideoIdent only a justified exception.
4. **A fund company like the case's client sells through two channels that must not conflict**: its own website/app (no personal advice → *beratungsfreies Geschäft*) and cooperating branch banks (personal advice → *Anlageberatung* with a stricter **Geeignetheitsprüfung**). An agent-based channel is a third channel and has to fit next to both.
5. **Under German civil law an AI agent cannot be a legal representative.** Every declaration the agent makes is attributed to the human who mandated it. So the target architecture must be built around a **verifiable human mandate** – which is also what the new agentic-commerce standards (AP2 mandates, signed agent cards) are designed for.

---

## 1. Who the client is and how they sell today

The case describes "a large German fund company, core product securities Depots, distributed via own website/app and cooperating branch banks". This is the profile of the big German **Fondsgesellschaften** (asset managers) that belong to a banking group – e.g. Union Investment (Volksbanken/Raiffeisenbanken), Deka (Sparkassen), DWS (Deutsche Bank). You do not have to name one; the pattern is what matters.

Two things about this business model shape the whole case:

**Two distribution channels with different legal duties.**

| Channel | Who talks to the customer | Legal mode | Which suitability check applies |
|---|---|---|---|
| Own website / app | Nobody – customer self-serves | **Beratungsfreies Geschäft** (no personal recommendation) | **Angemessenheitsprüfung** (§ 63 Abs. 10 WpHG): only knowledge & experience |
| Cooperating branch bank | A human **Berater** in the branch | **Anlageberatung** (personal recommendation) | **Geeignetheitsprüfung** (§ 64 Abs. 3 WpHG): knowledge, experience, financial situation, goals, risk tolerance, ESG preferences |

For fund companies in a banking group the branch bank is the main sales channel; Union Investment, for example, says a new UnionDepot is opened in a cooperative bank branch with an adviser, and online opening exists only for people who are already bank customers with online-banking access. That is the "Kanalkonflikt" the case warns about: an agent channel that bypasses the branch bank threatens the partner's revenue and relationship – so the target design must give the partner bank a role, not remove it.

**The Depot is legally held by a bank, not by the fund company.** A **Depot** is a securities account; a **Fondsgesellschaft (KVG – Kapitalverwaltungsgesellschaft)** manages funds but the Depot itself sits at a **Depotbank / depotführende Stelle** (often a group-internal service bank). This matters for the architecture: the "system of record" for the Depot, the KYC file and the tax data is a regulated bank core system, and the fund company's website/app is a front-end onto it.

---

## 2. The end-to-end process today, step by step

Below is the sequence you see when you open a Depot at any German provider today. Order and wording vary slightly between providers, but the content is fixed by law. For each step: what happens, why (which law), what data/proof is collected, and who is involved.

### Step 0 – Discovery and decision (before the process starts)

The customer researches on comparison sites, provider websites or in a branch conversation, chooses a provider, and clicks "Depot eröffnen". At a branch bank this is the advisory talk where the adviser records goals and recommends products.

*Relevance for 2030:* this is exactly the step that the case says will be taken over by the customer's AI agent ("Produktrecherche, -vergleich und -erwerb"). Today a provider is "findable" through SEO, ads and branch presence; an agent needs machine-readable discovery (see section 6).

### Step 1 – Account creation and personal master data (Stammdaten)

- Email + password, email confirmation (like any web shop).
- Then the legally required personal data set: first/last name, date and place of birth, nationality, residential address, occupation. The **Geldwäschegesetz (GwG)** prescribes this data set.
- Under the EU AML Regulation from 2027 the mandatory data set grows: *all* first names, *all* nationalities, national ID number, and – where available – the tax ID.

*Who:* customer, provider's onboarding front-end.
*Proof:* none yet – this is self-declared and will be verified in Step 5.

### Step 2 – Tax information (steuerliche Angaben)

Three separate things are collected here, all driven by tax law:

| Item | What the customer gives | Why / legal basis | What the provider does with it |
|---|---|---|---|
| **Steuer-Identifikationsnummer (Steuer-ID / IdNr.)** – 11 digits | Types it in | § 139b AO; banks must record it for every account holder | Used for capital-gains tax reporting and the church-tax lookup below |
| **Steuerliche Ansässigkeit (tax residency) – FATCA/CRS-Selbstauskunft** | Declares: only Germany / also abroad / only abroad; if abroad, country + foreign TIN; US indicators (citizenship, birthplace, address) | **FKAustG** (implements OECD CRS) and the German–US **FATCA** agreement | A bank may **not open a new Depot without a valid self-certification**. US persons must additionally provide a W-9 with US TIN |
| **Kirchensteuer** | Nothing actively – but is informed that the bank will query the **Kirchensteuerabzugsmerkmal (KiStAM)** | § 51a EStG | Bank queries the **Bundeszentralamt für Steuern (BZSt)** once at account opening (**Anlassabfrage**) and every year 1 Sept–31 Oct (**Regelabfrage**), so it can withhold church tax on capital gains. Customer can block this with a **Sperrvermerk** at the BZSt |
| **Freistellungsauftrag** (optional) | Amount up to the 1,000 € / 2,000 € (couples) tax-free allowance | § 44a EStG | Exempts capital gains up to that amount from the 25 % **Abgeltungsteuer** |

*Plain language:* German banks are tax collectors on behalf of the state. They deduct 25 % **Abgeltungsteuer** + Solidaritätszuschlag + church tax directly from gains and dividends. To do that correctly they need your tax ID and your residency status before the first euro is invested.

*Who:* customer, provider, BZSt (external state system).

### Step 3 – Knowledge and experience (Kenntnisse und Erfahrungen) → Angemessenheitsprüfung

- The customer answers a questionnaire: which product classes have you traded before (funds, shares, bonds, certificates, derivatives), how often, in what volumes, for how many years, education/occupation in finance?
- Legal basis: **§ 63 Abs. 10 WpHG** (German implementation of **MiFID II**). Before providing any securities service other than advice/portfolio management, the firm must collect information on knowledge and experience "as far as necessary to assess whether the instrument is appropriate".
- Outcome: the customer is "unlocked" for product groups matching their experience. If a later order is for a product outside that, the provider must show a **Warnhinweis** (warning) – but may still execute if the customer insists.
- Exception – **Execution-only (§ 63 Abs. 11 WpHG)**: for non-complex instruments (plain shares, bonds, UCITS/OGAW funds) on the customer's own initiative, no appropriateness check is required, provided the customer is told in a standardised way that no check takes place. Many neobrokers make the questionnaire "voluntary" for this reason.
- In the branch-bank channel this is replaced by the much broader **Geeignetheitsprüfung (§ 64 Abs. 3 WpHG)** with a written **Geeignetheitserklärung** handed to the customer.

*Who:* customer, provider's compliance rules engine (in a branch: the adviser).
*Proof:* the questionnaire answers, timestamp, unlocked product classes – must be stored and retrievable for the supervisor (BaFin).

### Step 4 – Mandatory information and contract (Pflichtinformationen, Vertragsschluss)

The customer has to *receive* a defined bundle of documents before the contract and *confirm* receipt (checkboxes), then accept the contract. Typical bundle:

- **AGB** (general terms) and **Sonderbedingungen für Wertpapiergeschäfte**
- **Preis- und Leistungsverzeichnis** (fee schedule)
- **MiFID-Basisinformationen** ("Basisinformationen über Wertpapiere und weitere Kapitalanlagen") – the "Basisdokumentation" that must exist before a retail customer is advised or opens a Depot
- **Ex-ante Kosteninformation** – estimated total costs of the service and products, before the transaction
- Information on **Zielmarkt** logic and the provider's **Ausführungsgrundsätze** (best execution), **Interessenkonflikte**, **Zuwendungen** (inducements)
- **Datenschutzinformation** (GDPR)
- **Widerrufsbelehrung** – the distance-selling right of withdrawal (14 days) because the contract is concluded online (**Fernabsatz**, §§ 312c ff. BGB). The revised EU directive on distance financial services (Directive (EU) 2023/2673, applicable from June 2026) adds a mandatory **Widerrufsbutton**, stricter information duties and rules for chatbots/dark patterns – directly relevant for an agent channel.
- **Einlagensicherung** information for the settlement account
- Per product, at first purchase: the **Basisinformationsblatt (BIB / PRIIPs KID)** for funds and packaged products, or a **Produktinformationsblatt (PIB)** for others.

Contract conclusion itself is usually a click ("Depot jetzt eröffnen") – the legally binding step is completed once identity is verified in Step 5 and the bank accepts. Some providers still use a printed, signed application (PostIdent coupon).

*Who:* customer, provider, legal/compliance.
*Proof:* logged acknowledgements with timestamp and document versions; the signed/accepted application.

### Step 5 – Identity verification (Identifizierung / Legitimation) + AML checks

This is the heavy step. The **GwG** obliges banks to identify and verify every new contracting partner *before* the business relationship starts (§§ 10–13 GwG).

**What is verified:** name, birth date/place, nationality, address – against an official ID document (Personalausweis, Reisepass, or eID card for EU citizens).

**Accepted methods today (Germany):**

| Method | How it works | Pros / cons |
|---|---|---|
| **In branch (Filiale)** | Employee inspects the ID | Reliable, but requires physical presence – standard at branch banks |
| **PostIdent** | Customer goes to a Deutsche Post branch with a coupon | Slow, media break, days of delay |
| **VideoIdent** | Video call with an agent of an ident provider (IDnow, WebID, POSTIDENT Video…) who checks the ID's security features and takes screenshots | Market standard since BaFin circular 3/2017; ~6 € per attempt, ~30 % abort rate, waiting times at peak hours, deepfake risk |
| **eID / Online-Ausweisfunktion** | NFC read of the Personalausweis chip with the 6-digit PIN via smartphone (AusweisApp) | Fully automated, seconds, cheapest, eIDAS "high" assurance – but low adoption because many people never activated their PIN |
| **AutoIdent (semi/fully automated)** | Photo of ID + selfie + liveness check, AI-based; a human reviewer approves | Allowed in a supervised trial; not yet the regulated standard |
| **Referenzüberweisung / bestehende Bankbeziehung** | Identification is inherited from an existing verified account (e.g. Sparkasse S-Neo Depot opens inside the banking app "without VideoIdent because identification runs via the existing bank relationship") | Best UX – only works for existing customers of a group bank |

**Additional AML checks in the same step (invisible to the customer, done by the bank's compliance system):**
- **Wirtschaftlich Berechtigter** (beneficial owner) – for private individuals normally the customer themself; must be declared.
- **PEP check** (politically exposed person) and **Sanktionslisten-Screening** against EU/UN/US lists.
- **Zweck der Geschäftsbeziehung** (purpose of the relationship, e.g. "Vermögensaufbau").
- Risk classification of the customer and start of **kontinuierliche Überwachung** (ongoing monitoring).

**What changes from 10 July 2027 (EU AML Regulation (EU) 2024/1624, directly applicable):**
- Remote identification must in principle use **eIDAS-conform means**: a notified national **eID** (Online-Ausweis, eID-Karte) or a **qualified trust service**, and in future the **EUDI Wallet**.
- **VideoIdent is not eIDAS-conform** and becomes a narrow fallback that must be justified case by case (e.g. non-EU citizens without an eID).
- Germany plans to launch the state **EUDI Wallet in January 2027**; the national legal basis (**Digitale-Identitäten-Gesetz, DIdG**) was adopted by the cabinet on 20 May 2026. The onboarding flow with the wallet: customer opens wallet via link/QR, releases the required data points, bank receives data with proof of authenticity, and the contract can be **signed inside the wallet** (qualified electronic signature).

*Who:* customer, ident service provider (outsourced), bank's compliance/**Geldwäschebeauftragter**, sanctions/PEP data providers, (future) EUDI wallet issuer.
*Proof:* the identification record (method, ID document data, images/transcript for video, timestamps, verifier), PEP/sanctions results – must be retained for 5 years (soon 10 under AMLR rules) and be auditable.

### Step 6 – Settlement account (Verrechnungskonto) and reference account (Referenzkonto)

- Every Depot needs a cash account. Either the bank opens a **Verrechnungskonto** (settlement account) alongside the Depot, or the customer links an external **Referenzkonto** (IBAN in the customer's own name) from which money is pulled and to which payouts go.
- Name match between the reference account and the identified customer is mandatory (AML). Some providers verify it by a **Referenzüberweisung** (a small transfer from that account).
- Payments run under **PSD2** rules with **starke Kundenauthentifizierung (SCA)** – a second factor (app push-TAN etc.) for every order and payment.
- A **Schufa** credit check is *not* required for a pure Depot; it appears only if the account has an overdraft or margin facility.

### Step 7 – Back-office processing and activation (Freischaltung)

- The bank's back office matches the ident result against the application, runs the compliance checks, queries KiStAM at the BZSt, creates the Depot and account in the core banking system, and sends access credentials (often still partially by post: PIN letter, TAN activation).
- Duration: the data entry plus VideoIdent takes 10–15 minutes; until the Depot is activated and money can be paid in "typically 1–3 working days depending on the bank". At peak times (e.g. the expected rush for the state-subsidised **Altersvorsorgedepot** in January 2027) identity checks "take days rather than minutes" and video slots are booked out.

### Step 8 – First order (not part of opening, but the goal of it)

- The customer picks a fund/ETF, sees the **BIB/KID** and the **ex-ante Kosteninformation** for that product, passes the **Zielmarkt** check (the manufacturer's defined target market vs. the customer's category/knowledge), possibly gets a **Warnhinweis**, confirms with SCA.
- The provider must report each executed order on a durable medium (**§ 63 Abs. 12 WpHG**) and send annual **ex-post Kosteninformation**.

---

## 3. The regulatory map in plain language

You will be asked in the Q&A "which regulation matters where". This table is the cheat sheet.

| Law / regulation | What it is about | Where it bites in the process | Key point for the 2030 concept |
|---|---|---|---|
| **GwG (Geldwäschegesetz)** – German AML law; from 10 Jul 2027 largely replaced by the directly applicable **EU AMLR (VO 2024/1624)**, supervised by the new EU authority **AMLA** | Know your customer: identify, verify, screen, monitor | Steps 1, 5, 6 | Verification must be eIDAS-conform (eID / EUDI Wallet); VideoIdent only as justified exception. Persons acting *on behalf of* the customer must also be identified (Art. 20(1)(i) AMLR) – relevant for agents |
| **WpHG (Wertpapierhandelsgesetz)** = German **MiFID II** implementation; detailed in BaFin's **MaComp** circular | Investor protection: information duties, appropriateness/suitability, costs, target market, conflicts | Steps 3, 4, 8 | Duties are per *customer* and per *product*, not per channel. An agent flow must still produce an appropriateness assessment and deliver KID/cost info to the human |
| **PRIIPs-VO** | Standardised 3-page key information document (BIB/KID) for packaged products incl. funds | Step 8 | Machine-readable KID data would let an agent compare products; today they are PDFs |
| **AO / EStG / FKAustG / FATCA** | Tax ID, withholding tax, church tax lookup, tax residency exchange | Step 2, Step 7 (KiStAM query) | Structured data an agent can supply – but the self-certification must be *the customer's* declaration |
| **BGB §§ 312c ff. (Fernabsatz)** + Directive (EU) 2023/2673 (from June 2026) | Distance contracts for financial services: information duties, 14-day withdrawal, withdrawal button, chatbot/dark-pattern rules | Step 4 | An agent-concluded contract is still a distance contract with a human consumer on the other side |
| **BGB §§ 164 ff. (Stellvertretung)** | Who may make declarations for whom | Step 4 | Prevailing view: an AI has no will of its own, so it cannot be a *Stellvertreter*; its declarations are attributed to the user who mandated it (models: "verlängerter Arm", Computererklärung, Blanketterklärung, Mandatsmodell). Practical consequence: define the scope of the mandate technically and legally |
| **eIDAS 2.0 (VO 2024/1183)** + **DIdG** | European digital identity wallet, qualified electronic signatures | Step 5, Step 4 | The wallet becomes the identity *and* signature tool; Germany's wallet launches Jan 2027 |
| **PSD2 / (PSD3 in preparation)** | Payments, strong customer authentication | Step 6, 8 | Any money movement triggered by an agent still needs SCA or a delegated authorisation mechanism |
| **DSGVO (GDPR)** | Data minimisation, purpose limitation, automated decisions (Art. 22) | All steps | An agent should transfer only the minimum data set; automated rejection needs human review path |
| **EU AI Act, Art. 50** (transparency, applies from Aug 2026) | Users must know they interact with an AI; AI-generated content labelling | Step 0, all agent interactions | Both the customer agent and the provider's agent must disclose themselves |
| **BaFin circulars (MaComp, MaRisk, BAIT/DORA)** | Outsourcing, IT risk, operational resilience | Architecture | Ident providers and agent platforms are outsourcing partners under **DORA** – needs contracts, exit strategy, deprecation planning |

---

## 4. Roles involved (beteiligte Rollen)

| Role | What they do in the process | In the target picture |
|---|---|---|
| **Kunde** (retail customer, *Privatkunde* under MiFID) | Provides data, proves identity, accepts contract, pays | Delegates to a personal AI agent, but stays the legal principal and must give consent at defined points |
| **Fondsgesellschaft / KVG** | Product manufacturer; defines target market, produces KID; runs website/app front-end | Publishes agent-readable product data and an agent-facing onboarding API/endpoint |
| **Depotbank / depotführende Stelle** (regulated bank, often group-internal) | Holds Depot and settlement account; legally responsible for KYC, tax withholding, reporting | System of record; exposes onboarding services behind policy/consent checks |
| **Kooperierende Filialbank / Berater** | Advises, opens the Depot in branch, earns distribution fees | Must keep a role (advice, human escalation, existing-customer identification) to avoid channel conflict |
| **Ident-Dienstleister** (IDnow, WebID, Deutsche Post, AusweisApp/eID service providers) | Perform VideoIdent / eID / AutoIdent as outsourcing | Replaced or complemented by EUDI Wallet verification |
| **Bundeszentralamt für Steuern (BZSt)** | Issues tax IDs; answers KiStAM queries; receives CRS/FATCA reports | Unchanged – state API |
| **Compliance / Geldwäschebeauftragter / WpHG-Compliance** | PEP/sanctions screening, risk classification, appropriateness rules, audit trail | Rule engine + human review queue for escalations |
| **Backoffice / Operations** | Account creation, credential dispatch, exception handling | Mostly automated; handles the "agent may not decide" cases |
| **Datenanbieter** (sanctions lists, PEP databases, target-market data feeds such as WM Datenservice) | Reference data | Same, consumed via APIs |
| **Aufsicht (BaFin, from 2027 also AMLA; Bundesbank)** | Supervises everything above | Wants audit trails that show *who* decided *what* on *whose* mandate |

---

## 5. Friction points today (Reibungspunkte) – with numbers

These are the arguments for *why* an agent-based process is worth building, and they should appear on the Ist-Analyse slide.

1. **Identity verification is the bottleneck.** VideoIdent costs about 6 € per attempt, has abort rates around 30 %, and involves waiting queues; the BaFin-supervised process still relies on a human operator per call. Deepfake attacks are an emerging systemic risk according to the EBA's stakeholder group.
2. **Days of dead time.** Data entry takes minutes but activation takes 1–3 working days; in peak periods identity checks take days and slots are sold out.
3. **High drop-off in banking onboarding generally.** Industry surveys report banks having the highest onboarding abandonment of all sectors (~23 %), with identity verification and process complexity as the top reasons; 10–37 mandatory fields per application; media breaks between app, email, SMS and browser.
4. **Redundant data entry.** The same person types the same master data at every provider; nothing is portable. (EUDI Wallet is the fix.)
5. **Information overload without comprehension.** The customer clicks through 8–12 PDFs (AGB, Basisinformationen, cost info, KID) – legally delivered, practically unread. An agent could actually *read* and summarise them, but only if they are machine-readable.
6. **Channel silos.** Online opening at group fund companies often requires an existing bank relationship; new customers are sent to a branch. Direct channel and branch channel have separate journeys and data.
7. **Unclear when a human is needed.** Edge cases (foreign tax residency, PEP hit, mismatched address, minors, joint accounts, non-EU ID, unusual experience profile) fall out of the digital flow into email/phone ping-pong.
8. **Deprecation risk built into today's stack.** VideoIdent, the main remote method, is scheduled to lose its regular status in July 2027 – every provider must re-platform identification anyway.

---

## 6. What is changing between now and 2030 (the "tailwind")

You need this to argue that the 2030 target is realistic and to justify technology choices in the decision log.

**Identity & signature**
- EU AMLR from 10 Jul 2027: eIDAS-conform remote identification is the rule. AMLA's revised RTS draft (Feb 2026) keeps that line; non-eIDAS methods only "where eIDAS means are not available or cannot reasonably be expected".
- German EUDI Wallet: first stage planned for Jan 2027; DIdG adopted by cabinet May 2026; over 100 companies already building on it, including account-opening use cases; private wallet providers to be admitted ~12 months after start. The wallet carries Person Identification Data plus a qualified e-signature – i.e. it can do both Step 5 (identify) and Step 4 (sign).
- A **European Business Wallet** (proposal Nov 2025) will do the same for legal entities.

**Agent discovery, identity and tooling**
- **MCP** (Model Context Protocol) is the de-facto standard for exposing tools/APIs to agents; it added OAuth 2.1 with PKCE for HTTP transports in Jan 2026.
- **A2A** (Agent-to-Agent) v1.0 (Jan 2026, Linux Foundation / Agentic AI Foundation) introduced **signed Agent Cards** – a machine-readable, cryptographically verifiable description of an agent's capabilities and auth requirements, published at a well-known URL. This is the natural answer to the case's "Auffindbarkeit und verifizierbare Anbieteridentität".
- Agent authentication drafts at the IETF (agent auth, transaction tokens for agents, Web Bot Auth) and academic proposals (AIP) address delegation chains user → agent → provider. Still immature – a deprecation risk to document.

**Agentic commerce / consent standards**
- **AP2** (Agent Payments Protocol, Google, Sept 2025; donated to the FIDO Alliance April 2026): three signed **Mandates** – *Intent* (what the user wants), *Cart* (what the agent selected), *Payment* – as W3C Verifiable Credentials, giving the merchant a cryptographic record of what the human authorised.
- **ACP** (Agentic Commerce Protocol, OpenAI + Stripe, beta) for the checkout handshake; **UCP** (Google) for commerce operations.
- **Visa Intelligent Commerce / Trusted Agent Protocol** and **Mastercard Agent Pay**: network-issued verified agent IDs, tokenised credentials scoped to an agent, user-set guardrails (spend cap, merchant categories, human approval). Visa's Intelligent Commerce Connect (Apr 2026) accepts multiple agent standards at once.
- Consensus in the industry: the landscape is multi-protocol and still in beta – which is *why* the case grades "Robustheit gegen Deprecation".

**Legal framing of agent actions**
- German civil law: the AI cannot be a Stellvertreter; declarations are attributed to the user within the scope they defined. The **Mandatsmodell** (user defines a decision corridor in advance) is the approach most compatible with signed mandates.
- AI Act Art. 50 transparency duties (Aug 2026) and the new distance-selling rules (Jun 2026) both assume a human consumer who must be informed – the agent does not replace those duties, it has to relay them.

---

## 7. Translation to the 2030 target concept and the demo MVP

This is the bridge from the Ist-Analyse to part 2 of the case. The principle: **keep every legal check, change who performs it and how the proof is produced.**

### 7.1 Mapping table

| Today's step | Legal duty that stays | 2030: how an agent-based flow fulfils it | What the MVP should show |
|---|---|---|---|
| 0 Discovery | AI Act transparency | Provider publishes a **signed Agent Card / capability manifest** at a well-known URL + machine-readable product data (KID data, costs, target market). Customer agent verifies the provider's identity (signature bound to the provider's domain / eIDAS certificate) before talking to it | Agent fetches `/.well-known/agent-card.json`, verifies signature, lists capabilities |
| 1 Master data | GwG data set | Data comes from the customer's **EUDI Wallet** as verified attributes, not from typing | Mock wallet presentation of PID (name, birth date, address, nationality) |
| 2 Tax data | AO/FKAustG: self-certification must be the customer's | Agent pre-fills; customer confirms residency declaration explicitly (signed) | Structured tax step; explicit human confirmation event |
| 3 Appropriateness | § 63 Abs. 10 WpHG | Agent submits knowledge/experience profile *on the customer's mandate*; provider's rules engine decides product unlocks and issues warnings to the *human* | Rules engine + returned "unlocked product classes" + warning path |
| 4 Information & contract | MiFID/PRIIPs/Fernabsatz duties; BGB attribution | Provider delivers documents in machine-readable + human-readable form; contract signed via wallet QES or bound to a signed **Intent Mandate**; withdrawal info delivered | Document bundle returned to agent; human signs (mock QES); mandate stored |
| 5 Identification | AMLR: eIDAS-conform, plus identification of persons acting on behalf | Wallet-based identification of the customer; agent identity/authorisation proven by signed mandate chain (customer → agent) | Mock EUDI verification; mandate chain check; PEP/sanction screening call |
| 6 Account | PSD2 SCA | Reference account from wallet/open-banking; SCA via wallet or bank app | Stubbed |
| 7 Activation | Bank creates Depot | Instant if all checks pass; otherwise **human-in-the-loop** queue | Depot ID returned in seconds; or escalation ticket |
| 8 First order | Zielmarkt, KID, SCA | Agent can prepare a **Cart Mandate**; execution only after human SCA | Optional in MVP |

### 7.2 "Agent may not complete autonomously" – the escalation catalogue

The case explicitly asks for reliable detection of when a human must step in. From the Ist-Analyse these triggers fall out naturally:

- Identity: wallet verification failed, non-EU ID, name mismatch with reference account, age < 18, joint account requested.
- AML: PEP or sanctions hit, high-risk country, unclear beneficial owner, unusual purpose.
- Tax: foreign or multiple tax residencies, US indicia, missing Steuer-ID.
- Investor protection: requested product outside unlocked classes (Warnhinweis must reach the human, not the agent), customer wants advice (→ route to partner bank adviser = channel-conflict solution), complex products.
- Mandate: agent's request exceeds the scope of the signed mandate (amount, product type, time window), mandate expired/revoked, agent not verifiable.
- Legal: any step where the law requires the *customer's own* declaration (tax self-certification, contract signature, withdrawal) – the agent prepares, the human confirms.
- Operational: provider agent-endpoint degraded, standard deprecated, signature verification impossible.

### 7.3 Things the MVP must not pretend

- It must not let the agent "sign" for the human – show the human confirmation step explicitly (this is the legal core and interviewers will probe it).
- It must not skip the appropriateness logic – even a 5-rule engine is better than a checkbox.
- It should show the audit trail: which mandate, which agent, which decision, which human confirmation, with timestamps.

---

## 8. Assumptions to document (Annahmen) and open questions

The case rewards documenting assumptions. Candidates from this research:

1. The client is a KVG in a banking group; the Depot is held by a group bank; the fund company's website/app is a front-end (not itself the KYC-obliged entity).
2. Target customers are German-resident retail customers with an EUDI Wallet (available from 2027); non-wallet customers fall back to eID or – as justified exception – VideoIdent, or to the branch.
3. By 2030 the AMLR is in force; VideoIdent is no longer the regular remote method.
4. Agents present themselves via signed capability descriptors (A2A-style Agent Card) and carry a user mandate as a verifiable credential (AP2-style). Which concrete standard wins is unknown → the architecture must abstract the "mandate" and "agent identity" interfaces.
5. The partner bank keeps the advisory role and the escalation role; the agent channel is *beratungsfrei* by default.
6. The customer's agent runs on a third-party platform (ChatGPT/Gemini/Claude-style assistant or a bank's own assistant) – the provider cannot trust it and must verify every claim cryptographically.

Open questions worth stating on a slide as "would clarify with the client": Which entity is the GwG-Verpflichtete? Is the agent channel allowed to onboard customers who are not customers of a partner bank? Is Anlageberatung ever to be offered via agents (then Geeignetheitsprüfung applies)? Which markets/nationalities are in scope?

---

## 9. Slide-ready German summary (Ist-Analyse, 2 Folien)

**Folie: Depoteröffnung heute – fünf gesetzlich zwingende Prüfschritte**

1. **Stammdaten & Identifizierung** (GwG §§ 10–13): Name, Geburtsdatum/-ort, Staatsangehörigkeit, Adresse; Legitimation per Filiale, PostIdent, VideoIdent, eID; PEP-/Sanktions-Screening, wirtschaftlich Berechtigter
2. **Steuerliche Angaben** (AO, FKAustG, EStG): Steuer-ID, FATCA/CRS-Selbstauskunft, KiStAM-Abfrage beim BZSt, Freistellungsauftrag
3. **Angemessenheitsprüfung** (§ 63 Abs. 10 WpHG): Kenntnisse & Erfahrungen → freigeschaltete Produktklassen, Warnhinweis; bei Beratung stattdessen Geeignetheitsprüfung (§ 64 WpHG)
4. **Pflichtinformationen & Vertrag** (MiFID II, PRIIPs, Fernabsatz): AGB, Basisinformationen, Ex-ante-Kosten, Basisinformationsblatt, Widerrufsbelehrung
5. **Depoteröffnung & Verrechnungs-/Referenzkonto** (PSD2/SCA): Freischaltung durch Backoffice, Zugangsdaten

Beteiligte Rollen: Kunde · Fondsgesellschaft · Depotbank · Filialbank/Berater · Ident-Dienstleister · BZSt · Compliance/GwB · Backoffice · Aufsicht

**Folie: Reibungspunkte und Regulatorik im Wandel**

- Identifizierung ist der Engpass: VideoIdent ≈ 6 €/Vorgang, ≈ 30 % Abbruch, Wartezeiten; Freischaltung 1–3 Werktage
- Onboarding-Abbruch im Banking ≈ 23 % – Hauptgründe Komplexität und Identitätsprüfung; 10–37 Pflichtfelder; Medienbrüche
- Redundante Dateneingabe, ungelesene Pflichtdokumente, getrennte Kanäle (online nur für Bestandskunden)
- Unklare Eskalation: Sonderfälle (Auslandssteuerpflicht, PEP, Nicht-EU-Ausweis) fallen aus dem digitalen Prozess
- Regulatorischer Rückenwind: AMLR ab 10.07.2027 (eIDAS-konforme Fernidentifizierung, VideoIdent nur Ausnahme), EUDI-Wallet ab 01/2027, AI Act Art. 50 (08/2026), Fernabsatz-Novelle (06/2026)
- Zivilrecht: KI-Agent ist kein Stellvertreter – Erklärungen werden dem Nutzer zugerechnet → verifizierbares Mandat als Kernbaustein

---

## 10. Sources consulted

Process descriptions (German consumer guides, 2026): finanzguru.de "Aktiendepot eröffnen 2026"; goldesel.de "Depot eröffnen 2026"; t-online "Depot eröffnen Schritt für Schritt"; finanzen.net on Altersvorsorgedepot rush (Sept 2026); neuebanken.de on Sparkasse S-Neo (July 2026); fragfina.de walkthrough of a DAB/Smartbroker application.

Client model: union-investment.de FAQ "Wie kann ich ein Depot eröffnen?", vr-networld UnionDepot pages, Volksbank partner pages.

Identification / AML: Waldeck Rechtsanwälte, "Identifizierung unter der AMLR: Vom Videoident zur eID" (29 Jun 2026); Bird & Bird / Lexology on the GwVideoIdentV draft (2024); IDnow blog on the VideoIdent-Verordnung; GK-law.de; Wikipedia "Videoident" (BaFin circular 3/2017).

Investor protection: gesetze-im-internet.de § 63 WpHG; sp-unternehmerforum.de and S+P Compliance on Angemessenheits-/Geeignetheitsprüfung and MaComp BT 6/7; compliance-advisor.de on MiFID II documentation duties for retail clients; flatex.at MiFID II page (Zielmarkt, ex-ante costs).

Tax: Deutsche Bank FATCA/CRS self-certification form; Consorsbank tax FAQ (KiStAM at account opening, FATCA indicia); DAB depot application (KiStAM Anlass-/Regelabfrage); BZSt self-certification page; amtsdeutschland.de on the Steuer-ID.

Friction data: der-bank-blog.de / Cofinpro onboarding study (10–37 mandatory fields, media breaks); Namirial "Banken haben die höchste Abbruchrate" (23 %); Fenergo KYC Trend Report 2023; Signius/Arkwright figures.

Agent law: Händlerbund "Vertragsschluss durch KI-Agenten" (May 2026); PayTechLaw "Agentic Commerce: Ist unser Recht bereit?" (Sept 2026); Noerr "Wenn Roboter Verträge schließen"; HÄRTING on Agentic AI shopping.

Standards: eco.com and paz.ai on AP2 (FIDO donation Apr 2026); wetheflywheel.com "ACP vs AP2"; universalcommerceprotocol.fr on Visa/Mastercard (June 2026); agenticplug.ai protocol tracker; arXiv 2604.23280 "AI Identity: Standards, Gaps" (MCP OAuth 2.1, A2A JWS-signed cards); arXiv 2507.10644 (A2A v1.0 signed Agent Cards, AAIF); datalakehousehub "State of Agentic AI Standards 2026".
