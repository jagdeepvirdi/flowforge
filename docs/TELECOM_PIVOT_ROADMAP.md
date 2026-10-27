# FlowForge — Telecom Revenue Assurance Pivot Strategy

**Document Metadata:**
- **Date:** 2026-10-27
- **Author:** Alignment Briefing (Claude & Gemini Strategy)
- **Status:** Adopted Architectural Pivot
- **Target Repositories:** `flowforge-core` (Muscle) & `flowforge-brain` (Brain)

---

## Executive Summary & Product Positioning

> **FlowForge** is a high-performance, self-hostable data pipeline and ETL orchestrator. 
> 
> **Enterprise Focus:** While FlowForge can orchestrate any generic data workflow, its architecture is heavily optimized for the extreme volume and strict compliance requirements of the Telecom sector. When paired with our optional AI diagnostic microservice (`flowforge-brain`), the platform serves as a complete **Telecom Revenue Assurance Solution**, automating root cause analysis for dropped CDRs and orphaned subscriptions.

> **[claude]** Keep the second sentence honest in anything customer-facing. Today the telecom layer is direction, not shipped
> (see `ARCHITECTURE.md` section 7 and the `CLAUDE.md` "Reality check"): there are no CDR/mediation parsers, no
> reconciliation step, no leakage KPIs, no case management, and no volume benchmark. "Heavily optimized for extreme
> volume and strict compliance" should read "designed for" until a benchmark and a compliance review exist. A telco
> buyer will test this claim in the first meeting.

---

## 1. The First Proof-of-Concept Use Case (Orphaned Subscriptions)

**Strategic Decision:** Prioritize **Orphaned Subscriptions (HLR/HSS vs. Billing Status)** over raw Call Detail Record (CDR) reconciliation for the Phase 1 MVP.

- **Rationale:** Processing raw CDRs requires parsing high-velocity binary streams (ASN.1, TAP3 format), which FlowForge does not yet support out-of-the-box. In contrast, orphaned subscription audits are a 100% relational database reconciliation problem.
- **Execution:** Use FlowForge's existing `db_query` and `db_procedure` steps to run a multi-way `JOIN` across three datasets:
  1. **Commercial (CRM):** Active customer package records.
  2. **Financial (Billing Engine):** Actively billed tariff line items.
  3. **Technical (Network Provisioning / HLR / HSS):** Provisioned active profile flags.
- **Immediate Value:** Instantly catches "free riders" (services active on network but unbilled) without requiring new custom binary parser steps.

> **[claude]** Agree with this choice; it is the cheapest route to a demonstrable result. Two corrections:
>
> 1. **The "multi-way JOIN" assumes CRM, billing and HLR/HSS live in one database. They almost never do.** A single
>    `db_query` runs against one connection. You need one of: (a) stage all three extracts into one database first
>    (`data_load` exists, but it reads whole files into memory today, so it is not safe for a full subscriber base);
>    (b) run an aggregate/keyed query per system and compare the results in a new **reconciliation step**; or (c) use a
>    federated query / database links where the operator already has them. Option (b) is the missing telecom
>    primitive and is the largest hidden piece of Phase 1. It is not in the sequence in section 6.
> 2. **Define "orphaned" precisely before building** (active on network but unbilled; billed but not provisioned;
>    status mismatch; timing windows for in-flight provisioning). The false-positive rate on timing alone decides
>    whether analysts trust the output.

---

## 2. Target Scale & Ingestion Strategy (In-place Auditing)

**Strategic Decision:** Operate as an **In-place Database Audit Orchestrator** rather than attempting to ingest terabytes of raw files into memory.

- **Rationale:** FlowForge should not attempt to replace enterprise mediation engines (e.g., DigitalRoute, NetCracker). Streaming terabytes of raw call logs into application memory would hit proven memory bottlenecks (Excel/PDF streaming limits).
- **Execution:** Push the heavy data processing directly into the operator's high-performance data warehouse (Snowflake, BigQuery, Oracle, PostgreSQL). FlowForge schedules, triggers, and monitors SQL audit procedures in-place, extracting only the aggregated mismatch checksums and error logs.

> **[claude]** Agree, and this is the strongest decision in the document. Caveats: it moves the volume problem onto the
> operator's warehouse and SQL quality, so the product's value becomes the **audit templates** (the SQL), not the
> engine. Also, "extracting only aggregated mismatch checksums" still needs a way to pull a *capped sample of
> offending keys* for the Brain and for case work, so plan a bounded sample-extraction path. "Extreme volume" is
> then an operator-warehouse property, and the docs should say so rather than imply FlowForge itself handles it.

---

## 3. Deployment Reality & The "Brain" Architecture

**Strategic Decision:** Strict separation between the Air-gapped **Muscle** (Core ETL Engine) and the Enterprise Cloud **Brain** (AI Microservice).

- **The Muscle (`flowforge-core`):** Deployed completely on-premise or within the Telco's private network. Handles raw data, SQL execution, and scheduling. Air-gapped from LLM APIs. Written in Python / Flask.
- **The Brain (`flowforge-brain`):** Hosted in a secure enterprise Cloud (Vertex AI on Google Cloud) or deployed locally with open-weight models (Llama 3) for strict air-gapped environments. Written in FastAPI.
- **Data Egress Rule:** No raw customer data (MSISDN, IMSI, names) ever leaves the network. Data must be sanitized locally by the Muscle before hitting the Brain API.
- **UI Integration:** The React frontend acts as the single pane of glass, fetching operational status from Core and diagnostic insights from Brain via HTTP.

> **[claude]** Right direction, wrong word. **"Air-gapped" is not accurate**: Core sends sanitized evidence to the Brain and the
> browser talks to the Brain directly, so Core is *not* air-gapped from it. The true and stronger statement is:
> "Core contains no LLM code or provider keys, and only sanitized, minimized evidence ever leaves the network." A
> telco CISO will check the network paths, so describe them exactly.
>
> Open points to decide and document:
> - If the Brain is on Google Cloud, operators' **browsers must reach it** (and Core must reach it outbound). Many
>   telco networks forbid both. Proxying UI traffic through Core would fix the browser path but contradicts the
>   "UI calls Brain directly" decision in `ARCHITECTURE.md`; pick one deliberately.
> - **Two Brain deployment modes** (Vertex AI vs. a local open-weight model such as Llama 3) means the Brain must be
>   **model-agnostic behind its own interface**. `ARCHITECTURE.md` currently names Gemini; reconcile.
> - **UI-to-Brain auth** needs short-lived, audience-scoped, asymmetrically signed tokens, not the shared HS256
>   secret.
> - Repo naming: this repository is `flowforge`, not `flowforge-core`. Decide whether to rename; this doc and
>   `ARCHITECTURE.md` should use one name.

---

## 4. The Compliance Floor (PII Masking, RBAC, Tech Debt)

To pass a Telecom Chief Information Security Officer (CISO) review, the platform must satisfy three mandatory security pillars:

| Security Pillar | Requirement Standard | Implementation Status |
| :--- | :--- | :--- |
| **PII Masking Step** | Irreversible hashing/regex scrubbing of MSISDN/IMSI before LLM egress | Required for Phase 1 |
| **RBAC & Audit Trails** | AES-256-GCM credential encryption, SSO (SAML/Google/M365), immutable audit logs | Already Built in Core |
| **Vulnerability Remediation** | Zero critical SonarCloud findings, React-Router security patch upgrade | Pending Tech Debt |

> **[claude]** Correct list, but three of the claims need care before they appear in a buyer document:
>
> - **"Irreversible hashing" of MSISDN/IMSI does not hold with a plain hash.** The phone-number space is small, so
>   an unsalted (or even shared-salt) hash is reversed by brute force in minutes. Use a **keyed HMAC with a
>   per-deployment secret held in Core**, or **tokenization** (random token plus a local lookup table). Tokenization
>   also lets Core map the Brain's findings back to real subscribers locally, which analysts need; a one-way hash
>   cannot. Also scrub free-text fields (error messages, names embedded in descriptions) and cap/sample the payload.
> - **"Immutable audit logs: already built" is unverified.** The audit log is append-only in application code, but I
>   have not confirmed that the database blocks UPDATE/DELETE, and the retention job deletes old rows. Verify and,
>   if needed, add DB-level protection (revoked privileges / trigger / hash chain) before using the word "immutable".
> - **"Zero critical SonarCloud findings" is the wrong bar.** The known open items are two SonarCloud findings
>   (S5496, S3649) plus the react-router advisory; the SSRF, dependency and secret issues from the earlier audit are
>   fixed (PR #123). The floor an operator security review asks for is wider: data residency and retention
>   mandates, a documented data-flow diagram, pen-test evidence, key management, and a statement on lawful-intercept
>   and CPNI-type data handling. None of that exists yet.

---

## 5. Business Model & Go-To-Market Strategy

**Commercial Framework: Dual Open-Core Model**

- **FlowForge Core (Open Source - MIT):** Self-hostable, general-purpose ETL & pipeline orchestrator. Drives developer adoption and trust.
- **FlowForge Telecom RA Pack + Brain (Proprietary Enterprise License):** Commercial add-on containing pre-built telecom SQL audit templates, dynamic thresholding, and the AI Root Cause Analysis diagnostic engine.
- **Go-To-Market (GTM) Execution:** Conduct a historical "Leakage Audit" Proof of Concept (PoC) using 30 days of anonymized billing/HLR logs with regional telecom partners to demonstrate immediate monetary recovery before requiring software purchase.

> **[claude]** Plausible, but note the tensions rather than treat them as settled:
>
> - **MIT core means anyone can build the telecom pack.** The moat is domain knowledge, audit templates that are
>   proven against real operator data, and the partner relationship, not the licence. That makes the design
>   partner more important than the licence structure.
> - **There is no customer or design partner yet.** The leakage-audit PoC depends entirely on regional telecom
>   partners we do not have. Finding one is the true critical path and is not in the development sequence.
> - **Proprietary pack alongside an MIT repo** needs a delivery mechanism (separate private repo / package index) and
>   a contributor policy (CLA) so contributions to the core cannot become licence problems later.
> - **Selling the Brain** conflicts with the "no cloud SaaS" non-goal only if you host it. If operators run it
>   themselves, there is no conflict; if you run it for them, it is a hosted tier and that decision must be made
>   explicitly (`docs/TASKS.md` section 7).

---

## 6. Development Sequence (Telecom Logic First, AI Brain Second)

1. **Step 1: Extract Legacy AI from FlowForge Core**
   - Execute repository scrub via Claude Code. Strip all legacy Ollama/Claude/Gemini helper code from `flowforge-core` and save prompts to `extracted_ai_logic.md`.
2. **Step 2: Implement Conditional Execution & Alerting**
   - Add DAG conditional evaluation step (e.g., `if mismatch_count > threshold then trigger_alert`) necessary for automated leakage detection.
3. **Step 3: Build PII Anonymization Utility Step**
   - Add a deterministic hashing/masking pipeline step to sanitize raw log payloads prior to external transmission.
4. **Step 4: Scaffold FastAPI `flowforge-brain` Microservice**
   - Implement standalone Python microservice using Google AI Studio / Vertex AI SDK with structured JSON schemas for automated Root Cause Analysis.

> **[claude] Development sequence: my proposed ordering** (replaces the four steps above; reasoning follows the table)
>
> | # | Work | Why here | Rough effort |
> | :-- | :--- | :--- | :--- |
> | 0 | **Find one design partner** (an RA analyst at one operator) and get a sample schema for CRM, billing and HLR | Everything below is guesswork without a real schema; longest lead time, so start now and run in parallel | Calendar time, not dev time |
> | 1a | **Brain scrub** per `docs/BRAIN_DECOUPLING_PLAN.md` (phases A0-A8) | Mostly deletion, makes the positioning true, unblocks clean docs and the CI deny-list | 3-4 days |
> | 1b | **Conditional execution** (gate a step on a prior step's result: alert only if `mismatch_count > threshold`) | Needed for any threshold alerting; independent of 1a, so it can run in parallel | about 1 week |
> | 2 | **Reconciliation step** (compare keyed aggregates or key sets across two connections, with tolerance and a capped sample of offending keys) | The real telecom primitive; the orphaned-subscription audit cannot be built without it (see section 1) | 1-2 weeks |
> | 3 | **PII tokenization/masking step** (keyed HMAC or tokenization with local lookup, free-text scrubbing, payload cap) | Must exist and be reviewed before any data can go to a Brain | about 1 week |
> | 4 | **Orphaned-subscription audit template** and a seeded demo dataset; run it end to end on the partner's data or a synthetic equivalent | Proves the product; produces the PoC evidence | about 1 week |
> | 5 | **Verify and harden compliance claims** (audit-log immutability, data-flow diagram, retention, react-router v7, the two SonarCloud findings) | Cheap, and removes the objections a security review raises first | 1-2 weeks, parallelizable |
> | 6 | **Scaffold `flowforge-brain`** (FastAPI, model-agnostic provider interface, structured-JSON RCA, async contract from `ARCHITECTURE.md` section 4) | The Brain only adds value once steps 2-4 produce trustworthy findings | 2-3 weeks |
>
> Differences from the original sequence: partner discovery is added as step 0; the reconciliation step is added
> (it was missing); PII masking comes before the Brain and is reviewed on its own; the Brain moves to the end; the
> scrub and conditional execution run in parallel rather than one after the other. Effort figures are my estimates for
> one full-time developer and are unvalidated.

> **[claude] Where I disagree or am not convinced**
>
> 1. **"Air-gapped" as a headline.** Inaccurate (see section 3); I would not let it into marketing copy.
> 2. **Scrub as the strict first step.** It is cheap and worthwhile, but it should not block the telecom primitives;
>    steps 1a and 1b are independent. Doing only the scrub first gives a cleaner repo and zero telecom progress.
> 3. **Saving prompts to `extracted_ai_logic.md`.** The legacy prompts are generic (SQL explain, chart suggestion,
>    failure diagnosis). A telecom RCA Brain needs different, structured-JSON prompts built around reconciliation
>    evidence, so their reuse value is low. Keep the extraction as a record, but do not let it drive the Brain design.
> 4. **"Dynamic thresholding" as a proprietary feature.** Basic threshold gating (step 1b) belongs in the MIT core,
>    because it is general-purpose and the core already has statistical anomaly detection (2-sigma on row counts and
>    durations). Charging for it would fragment the product. The defensible paid layer is the audit templates, the
>    case workflow and the Brain.
> 5. **Commercialization before validation.** A dual-licence model, a proprietary pack and a partner PoC are planned
>    before there is a single external user. I would hold the licensing decision until a partner has seen the
>    reconciliation output; the shape of the paid product will likely change after that.
> 6. **Llama 3 for air-gapped sites.** Reasonable as a deployment option, but open-weight models are materially
>    weaker at structured-JSON RCA; it needs an evaluation set before it is promised to a customer.
> 7. **"Already Built in Core" for RBAC.** True for RBAC, SSO and encryption (they exist and are tested); not yet
>    shown for telecom-grade assurance (see the audit-log point in section 4). Do not tick the box until verified.
