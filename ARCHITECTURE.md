# FlowForge Architecture — "Muscle" and "Brain"

*Written 2026-10-27. This describes the **target architecture** adopted on that date. Sections marked
**[Proposed]** are design intent that is not yet built or frozen; sections marked **[Today]** describe the
repository as it currently exists. Migration status is in [§12](#12-migration-status).*

---

## 1. Why this architecture

FlowForge is evolving into an **Enterprise Telecom Revenue Assurance** platform: finding and quantifying revenue
leakage (dropped CDRs, misrated tariffs, orphaned subscription services) by combining heavy-duty data
orchestration with AI-assisted root-cause analysis.

Those two jobs have opposite engineering requirements:

| | Data orchestration | Root-cause analysis |
|---|---|---|
| Behavior | Deterministic, repeatable, auditable | Non-deterministic, probabilistic |
| Failure cost | A missed run = unbilled revenue | A missing diagnosis = a human reads the logs |
| Latency profile | Throughput-bound, large batches | Seconds-to-minutes per request, spiky |
| Dependencies | Databases, files, schedulers | Third-party model APIs, prompts, quotas |
| Change rate | Slow, regression-tested | Fast (prompts and models change weekly) |

Mixing them puts an unpredictable, rate-limited, externally-hosted dependency inside the revenue-critical path.
So we separate them completely:

- **The Muscle** — FlowForge Core (this repository): deterministic ETL, SQL audits, scheduling, alerting.
- **The Brain** — FlowForge Intelligence (separate repository/service): the AI diagnostic engine.
- **The Frontend** — one React UI that speaks to both.

---

## 2. System overview

```
                        ┌───────────────────────────────┐
                        │   React frontend (unified UI) │
                        │   "single pane of glass"      │
                        └───────┬───────────────┬───────┘
          operational data,     │               │   AI diagnostics
          charts, config, runs  │               │   (HTTP, optional)
                                ▼               ▼
        ┌──────────────────────────────┐   ┌──────────────────────────────┐
        │  MUSCLE — FlowForge Core     │   │  BRAIN — FlowForge           │
        │  (this repo)                 │   │  Intelligence (separate repo)│
        │                              │   │                              │
        │  • ingestion (bulk/data load)│   │  • FastAPI (Python)          │
        │  • SQL audits / reconcil.    │   │  • Gemini via Vertex AI /    │
        │  • scheduler, DAG engine     │   │    AI Studio                 │
        │  • alert rules & notifiers   │   │  • structured-output prompts │
        │  • run history, audit log    │   │  • owns prompts, keys,       │
        │  • ZERO AI / LLM code        │   │    diagnoses                 │
        └───────┬───────────▲──────────┘   └───────────▲──────────────────┘
                │           │                          │
   anonymized   │           │ (optional signed         │
   evidence     │           │  callback: "case ready") │
   (async,      └───────────┼──────────────────────────┘
   fire-and-forget)        ▼
        ┌──────────────────────────────┐
        │ PostgreSQL / Oracle / files  │   CDRs, mediation logs, CRM,
        │ (customer & telco systems)   │   HLR, billing, provisioning
        └──────────────────────────────┘
```

**Dependency direction is one-way:** Core may *send* evidence to Brain and *remember a case id*. Brain never
reads Core's databases, and Core never imports, embeds, or waits on Brain.

---

## 3. The Muscle — FlowForge Core

**Role:** the deterministic data orchestrator and ETL pipeline. It must stay fast, predictable and highly
available, with or without the Brain.

**Stack [Today]:** Python 3.11+, Flask + SQLAlchemy (REST API), PostgreSQL (FlowForge's own config/history),
PostgreSQL / Oracle / MySQL / MSSQL / ODBC / Snowflake / BigQuery / Redshift (customer data via a pluggable
`BaseConnection`), APScheduler (jobstore in PostgreSQL), optional Celery + Redis for distributed execution,
React + Vite + TypeScript frontend. *The original brief for this pivot mentioned Node.js; the repository is, and
remains, Python — we are not rewriting the backend.*

**Responsibilities:**
1. **Ingestion at volume** — CDRs, mediation/switch logs, CRM extracts via `bulk_load` / `data_load` /
   `sftp_transfer` (PostgreSQL `COPY`, Oracle SQL\*Loader, chunked inserts).
2. **Complex SQL audits** — ordered, parameterized steps (`db_query`, `db_procedure`) that compare systems
   (e.g. Network HLR status vs. Billing status) and persist discrepancy sets.
3. **Orchestration** — scheduling, retries, step-level DAG dependencies, concurrency limits, run history,
   run-to-run diffing and statistical (non-AI) anomaly detection.
4. **Alerting** — notify people and systems when a threshold is crossed (`notification`, `email`, failure
   webhooks).
5. **Evidence preparation** — when a finding warrants diagnosis, assemble a *minimal, anonymized* evidence
   package and hand it to the Brain asynchronously ([§6](#6-integration-flows)).

**Hard constraint — zero AI/LLM logic.** See [§8](#8-hard-rules).

---

## 4. The Brain — FlowForge Intelligence

**Role:** the non-deterministic AI diagnostic engine. Lives in its own repository, deploys and scales
independently, and can be absent without breaking anything in Core.

**Stack [Proposed]:** FastAPI (Python); Google Gemini through Vertex AI or AI Studio. The **model is
configuration, not code** — the original vision named Gemini 1.5 Pro; confirm that model is still available on
the chosen platform before building, and pin whatever is current in Brain's own config.

**Responsibilities:**
- **Root-cause analysis (RCA):** given an evidence package (e.g. "5,000 dropped sessions" represented as grouped
  error signatures with counts and a small anonymized sample), parse the unstructured logs using
  **structured-JSON-schema prompts** and return a plain-English diagnosis plus a recommended remediation step.
- **Own the AI surface entirely:** prompts, model/provider selection, API keys and quotas, retries, caching,
  evaluation, and the diagnosis store (Brain is the system of record for diagnoses; Core keeps only a `case_id`).
- Advisory output only: **Brain never executes remediation** and has no write access to Core or customer systems.

Logic extracted from the legacy in-repo AI code is preserved for rebuilding Brain in `extracted_ai_logic.md`
(see [`docs/BRAIN_DECOUPLING_PLAN.md`](docs/BRAIN_DECOUPLING_PLAN.md)).

---

## 5. The Frontend — one UI, two backends

The React app remains the single pane of glass for the enterprise user.

- **Operational data** (pipelines, runs, charts, discrepancy results, audit log) → Core's REST API, as today.
- **AI diagnostics** (RCA text, remediation, confidence) → Brain's HTTP API.

**[Proposed] bridging design:**

1. **Discovery.** Core's `GET /api/setup/status` reports `brain: { enabled, url }`. The frontend never hardcodes
   Brain's address. If Brain is not attached (`enabled: false`), **no AI UI renders** — no buttons, no panels,
   no requests. The default is *off*, including while the status call is loading or has failed.
2. **Two API clients.** `lib/api.ts` (Core) and a separate `lib/brainApi.ts` (Brain) with independent base URLs,
   timeouts, error handling and React Query keys. A Brain failure can never break a Core page.
3. **Authentication.** The UI must not hold Brain credentials. Recommended: Core mints a **short-lived,
   audience-scoped token** (`POST /api/brain/token`, no AI logic) that the browser presents to Brain; Brain
   verifies it with Core's **public key** (asymmetric signing, e.g. RS256/EdDSA). Sharing today's HS256
   `FLOWFORGE_JWT_SECRET` with Brain is **not** recommended — any holder could forge Core sessions.
4. **Isolation.** Brain panels are lazy-loaded, wrapped in their own error boundary, show skeleton/"unavailable"
   states, and never block page render. CORS on Brain allows only the configured UI origin.
5. **Linking.** A Core run/alert record stores `brain_case_id`; the UI uses it to fetch the diagnosis from Brain
   and renders it beside the operational data it explains.

---

## 6. Integration flows

### 6.1 Detection → diagnosis (Core initiates) **[Proposed]**
```
1. Scheduled pipeline runs the audit SQL.            (Muscle, deterministic)
2. A rule trips (e.g. 5,000 dropped sessions > threshold).
3. Core builds an evidence package:                  (Muscle, deterministic)
     • group errors into signatures + counts
     • take a small, capped, ANONYMIZED sample
     • attach context: pipeline, run_id, time window, system, thresholds
4. Core enqueues a background job (Celery / thread) — the pipeline run does NOT wait for it.
5. Job POSTs the package to Brain with a short timeout and an idempotency key.
6. Brain returns 202 {case_id}. Core stores case_id on the alert/run. Done.
7. Brain analyzes asynchronously (seconds–minutes), stores the structured diagnosis.
8. UI shows "Diagnosing…" then fetches GET /v1/cases/{case_id} from Brain when ready
   (poll with backoff, or Brain sends a signed "case ready" callback to Core which the UI refreshes on).
```
If steps 4–6 fail (Brain down, timeout, 5xx) the job records the failure and retries with backoff; the alert
itself has already fired through Core's own notifiers. **Nothing in Core waits on or depends on Brain.**

### 6.2 On-demand (user initiates) **[Proposed]**
User clicks "Diagnose" on a failed run or discrepancy → UI calls Brain with the `run_id` / case reference →
Brain pulls nothing from Core; it receives only what Core (or the UI via Core) already prepared as an evidence
package. Same async/`202` model; same "feature absent when Brain unattached" rule.

### 6.3 Proposed Brain API contract (draft — freeze before building)
```
POST /v1/cases              → 202 { case_id, status: "queued" }        (Idempotency-Key header)
GET  /v1/cases/{case_id}    → 200 { case_id, status, diagnosis? }
GET  /health                → 200

Request evidence package (schema_version "1"):
{
  "schema_version": "1",
  "source": { "system": "flowforge-core", "pipeline": "...", "run_id": "...", "step": "..." },
  "window": { "from": "ISO-8601", "to": "ISO-8601" },
  "finding": { "type": "dropped_sessions", "count": 5000, "threshold": 100 },
  "signatures": [ { "pattern": "ERR_0x4F timeout on mediation node <ID>", "count": 3120 } ],
  "sample": [ "anonymized log line", "..." ],        // capped, e.g. <= 50 lines / <= 64 KB
  "context": { "network_element_types": ["HLR","MSC"], "notes": "" }
}

Diagnosis (structured JSON enforced by schema):
{
  "case_id": "...", "status": "completed",
  "root_cause": "plain-English diagnosis",
  "evidence": ["signature A explains ~62% of drops", "..."],
  "remediation": "recommended next step",
  "confidence": 0.0-1.0, "model": "config-provided", "schema_version": "1"
}
```

---

## 7. Telecom Revenue Assurance mapping

An honest view of where the product stands against the target use cases. **Nothing below is a shipped telecom
feature unless marked "Building blocks exist"; it is the direction, not a feature list.**

| Use case | What it needs | Today in Core | Gap |
|---|---|---|---|
| **Dropped / lost CDRs** (switch vs. mediation vs. billing counts) | High-volume file/DB ingestion, count + sum reconciliation across stages | Building blocks exist: `bulk_load`, `data_load`, `sftp_transfer`, `db_query` | Streaming/chunked large-file handling for all formats (only CSV streams end-to-end); CDR format parsers; reconciliation as a first-class step with tolerances |
| **Misrated tariffs** | Re-rate usage against the rate plan, diff vs. billed amount | Building blocks exist: SQL steps, run diff | Rating-engine-style SQL libraries, tariff reference data management |
| **Orphaned subscriptions** (HLR/network active, billing inactive or vice-versa) | Cross-system status comparison | Building blocks exist: multi-connection SQL, staging loads | Cross-database comparison step; scheduled discrepancy snapshots |
| **Threshold alerting** ("only alert if leakage > X") | Conditional execution | Failure propagation only | **Conditional/branching steps — not built** (tracked in `docs/TASKS.md`) |
| **Leakage KPIs / $ impact** | Money-valued findings, trends, dashboards | Run history, charts | Leakage case model, value attribution, KPI dashboard |
| **Case management** | Assign, track, close findings | None | Not started |
| **RCA** | The Brain | None in Core by design | Brain service + contract ([§6.3](#63-proposed-brain-api-contract-draft--freeze-before-building)) |

Domain data is highly sensitive (subscriber identifiers, call records). Treat compliance claims carefully: do not
advertise regulatory compliance (GDPR/CPNI/lawful-intercept handling, data-residency) that has not been reviewed
for a telecom deployment.

---

## 8. Hard rules

These are architectural invariants. A change that violates one needs an explicit architecture decision, not a
code review comment.

1. **Core never imports an LLM SDK.** No `anthropic`, `openai`, `google-generativeai`, `google-genai`,
   `vertexai`, `langchain`, `llama-index`, `ollama`, or equivalent — directly or transitively through a
   FlowForge-owned module — anywhere in `flowforge/`. Core contains **no prompts, no model names, no provider
   keys, and no AI-provider HTTP clients.** *Enforcement [Proposed]:* a CI test that scans `flowforge/**/*.py`
   imports and `pyproject.toml` dependencies for a deny-list and fails the build.
2. **Core never makes long-running or long-polling AI calls**, and never blocks on the Brain. The API
   workers (Gunicorn/gevent), the scheduler thread, pipeline execution threads and Celery workers must not sit
   waiting on an AI response. Any Core→Brain traffic is **asynchronous, off the pipeline's critical path,
   fire-and-forget with a stored `case_id`**, using short connect/read timeouts (seconds), bounded retries with
   backoff, and a circuit breaker.
3. **Core is fully functional with the Brain absent, slow, or wrong.** No pipeline, schedule, alert or page
   depends on Brain availability. AI UI is hidden when Brain is not attached.
4. **Brain output is advisory.** It never triggers writes, remediation, or pipeline changes automatically.
5. **Evidence leaves Core only after deterministic anonymization**, minimized and capped ([§9](#9-security--privacy)).
6. **One-way dependency.** Brain holds no credentials to Core's or the customer's databases.
7. **Template and secret hygiene stays in Core:** provider keys live only in Brain's environment; Core retains the
   `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` names in its template-secret blocklist purely as a leak guard.

---

## 9. Security & privacy

- **Anonymize in Core, before egress** — deterministic, testable, auditable. Tokenize or hash subscriber
  identifiers (MSISDN, IMSI, IMEI), mask IPs and free-text fields, drop everything not on an explicit
  per-signature allowlist. Prefer **aggregates and grouped signatures over raw rows**: send counts + a capped
  sample, never a raw 5,000-row dump.
- **Data minimization & caps:** maximum lines and bytes per package; configurable per deployment.
- **Transport & auth:** TLS (or mTLS) between Core and Brain; service-to-service credential for Core→Brain;
  short-lived audience-scoped tokens for UI→Brain; no long-lived secrets in the browser.
- **Audit:** every evidence submission is recorded in Core's audit log (who/what/when/size/`case_id`), never the
  content itself.
- **Untrusted input:** logs are attacker-influenced text. Brain must treat them as data (prompt-injection
  aware), enforce a JSON output schema, give the model **no tools** and no network, and never follow
  instructions found in logs.
- **Third-party model provider:** Brain sends data to Google (Vertex AI / AI Studio). Choose region and data-use
  terms deliberately (Vertex AI offers enterprise terms; free AI Studio tiers may allow training on inputs).
  Decide per customer whether telecom data may leave their boundary at all — Brain must be deployable with a
  customer-approved model endpoint.
- **SSRF / config:** `FLOWFORGE_BRAIN_URL` is admin-set; validate scheme, don't follow redirects blindly, and
  reuse Core's existing outbound-URL guard.

---

## 10. Failure modes

| Failure | Behavior |
|---|---|
| Brain down / unreachable | Alerts still fire from Core; evidence job retries with backoff then records "diagnosis unavailable"; UI shows an unavailable state on the AI panel only. |
| Brain slow | Core already returned (`202`); UI shows "Diagnosing…"; Core threads are never held. |
| Brain returns invalid/low-confidence output | Rejected against schema or shown with confidence; never acted on automatically. |
| Model provider outage / quota | Contained inside Brain (its own retries/fallback); Core unaffected. |
| Evidence package too large / unsanitized | Core refuses to send (fails closed) and logs why. |
| Brain not configured | `brain.enabled=false`; zero AI UI, zero outbound AI traffic. |
| Core down | Brain keeps serving already-stored diagnoses; no new cases. |

---

## 11. Deployment topology

- **Core:** as documented in [`docs/deployment.md`](docs/deployment.md) — API + scheduler + optional Celery
  workers + PostgreSQL (+ Redis for scale-out).
- **Brain:** separate repository, container and release cadence; its own scaling (stateless workers + its own
  store). Can be deployed in a different network zone/region than Core.
- **Network:** UI → Core and UI → Brain are separate origins (CORS configured on Brain); Core → Brain uses a
  service credential; Brain has **no inbound path from customer data systems** and no outbound path to them.
- **Config in Core:** `FLOWFORGE_BRAIN_URL` (enables the integration; empty = detached) and a service credential
  for Core→Brain submissions. No AI-provider settings exist in Core.

---

## 12. Migration status

*As of 2026-10-27 — update this section as work lands.*

| Item | Status |
|---|---|
| Architecture decision (this document) | Adopted |
| Legacy in-repo AI code (`flowforge/api/routes/ai.py`, `flowforge/steps/ai_analyze.py`, frontend AI UI, `claude` extra) | **Still present** — removal planned in [`docs/BRAIN_DECOUPLING_PLAN.md`](docs/BRAIN_DECOUPLING_PLAN.md) (phases A0–A8, ~3–4 days) |
| `extracted_ai_logic.md` (prompts/logic to rebuild Brain) | Not yet written (phase A1) |
| CI deny-list guard for LLM imports | Not yet written |
| Brain API contract | Draft only ([§6.3](#63-proposed-brain-api-contract-draft--freeze-before-building)) |
| Brain service | Not started |
| Telecom RA features ([§7](#7-telecom-revenue-assurance-mapping)) | Direction only — building blocks exist, domain features do not |

**Note on the earlier decoupling plan:** it kept thin `/ai/*` shells inside Core that returned `503` when Brain was
unattached. Under this architecture the UI talks to Brain directly, so those shells should be **removed outright**
rather than kept (Core then has no AI routes at all). The detached/attached switch becomes the `brain` block in
`/api/setup/status`. The plan document carries the amended steps.

**Open questions**
1. Brain API contract sign-off (§6.3), including sync vs. callback delivery of "case ready".
2. Token model for UI→Brain (§5.3) and who owns Core's signing-key rotation.
3. Anonymization rules per telecom data class, and whether a customer-hosted model endpoint is required.
4. Whether pipelines may also call Brain through a generic HTTP step, or only through the evidence-job path.
5. Positioning/licensing: MIT open-source core vs. an enterprise telecom offering.
