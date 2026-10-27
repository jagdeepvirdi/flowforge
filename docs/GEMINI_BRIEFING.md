# FlowForge — briefing for Gemini (alignment on current state and direction)

*Written 2026-10-27 by Claude Code after reading the repository. Facts below were checked against the repo
(`README.md`, `ARCHITECTURE.md`, `CLAUDE.md`, `docs/TASKS.md`, `docs/BRAIN_DECOUPLING_PLAN.md`) unless marked as
opinion. Please plan from the **"what exists"** section, not from the positioning statement.*

## 1. The positioning statement (owner's words)

> FlowForge is a high-performance, self-hostable data pipeline and ETL orchestrator.
> **Enterprise Focus:** While FlowForge can orchestrate any generic data workflow, its architecture is heavily
> optimized for the extreme volume and strict compliance requirements of the Telecom sector. When paired with our
> optional AI diagnostic microservice (`flowforge-brain`), the platform serves as a complete Telecom Revenue
> Assurance Solution, automating root cause analysis for dropped CDRs and orphaned subscriptions.

## 2. What FlowForge is *today* (verified)

A working, self-hostable, **general-purpose** pipeline orchestrator, v1.3.0 (published on PyPI), single maintainer.

- **Stack:** Python 3.11+ / Flask / SQLAlchemy; PostgreSQL for its own config and history; APScheduler;
  optional Celery + Redis; React + Vite + TypeScript UI. (Not Node.js.)
- **Pipelines:** ordered steps plus a step-level DAG engine and a visual canvas; retries, per-step `on_error`,
  parallel groups, pipeline-to-pipeline dependencies, run history with run-to-run diff and **statistical** anomaly
  detection (>2σ on row counts/durations), webhooks/API triggers, YAML import/export, plugin system for new steps.
- **Step types (16 non-AI):** `db_procedure`, `db_query`, `report`, `email`, `drive_upload`, `onedrive_upload`,
  `s3_upload`, `azure_blob_upload`, `data_load`, `bulk_load`, `sftp_transfer`, `ssh_command`, `ssh_health_check`,
  `db_health_check`, `data_report`, `notification` (Slack/Teams/Telegram). Plus a legacy `ai_analyze` (being removed).
- **Databases (customer data):** PostgreSQL, Oracle (thin driver), MySQL/MariaDB, MSSQL, ODBC, Snowflake, BigQuery,
  Redshift. Bulk paths: PostgreSQL `COPY`, Oracle SQL\*Loader, chunked inserts.
- **Email/reports:** Gmail, M365, SMTP, SendGrid, SES, Mailgun; Excel/CSV/PDF/JSON reports; smart attachments
  (large files go to Drive/OneDrive/S3/Azure with a link).
- **Security/ops:** RBAC (admin/editor/viewer), MFA, SSO (Google/Microsoft/SAML), AES-256-GCM credential
  encryption, audit log, GDPR export/purge, IP allowlist, Prometheus metrics, Docker Compose, Gunicorn/Nginx guide,
  Redis-backed concurrency lock, leader election for the scheduler, SLSA-signed releases.
- **Quality:** ~2,150 backend tests (integration-style against real Postgres; almost no mocked unit tests), ~173
  frontend tests. A July 2026 external-style audit scored it 6/10 (Security 3/10 at the time); all its Critical
  items have since been fixed. Repo hygiene: SonarCloud/CodeQL/Scorecard in CI, with two open SonarCloud findings.
- **Legacy AI (to be removed):** Ollama/Claude/Gemini helpers (SQL explain/optimize, failure diagnosis, data
  profiler, chart suggestion, anomaly narrative) and the `ai_analyze` step still exist in the repo today.

## 3. What does **not** exist yet (be careful planning around these)

- **Any telecom-specific feature:** no CDR/mediation/TAP/ASN.1 parsers, no reconciliation step with tolerances,
  no rating/tariff logic, no HLR-vs-billing comparison step, no leakage-value (money) model, no case management,
  no leakage KPI dashboard.
- **Proven volume:** there is no benchmark at telecom scale. Only CSV report generation streams end-to-end;
  Excel/PDF/JSON reports and `bulk_load`/`data_load` read whole files in memory before chunking. No streaming
  ingestion (Kafka, etc.). The "heavy lifting" design is sound (push work into the database), but it is unmeasured.
- **Conditional execution:** a step cannot be gated on a prior step's result ("alert only if drops > X") — needed
  for threshold alerting.
- **Telecom compliance:** MFA, audit log and GDPR tooling exist; nothing has been reviewed against telecom
  requirements (CPNI, lawful-intercept handling, data residency, retention mandates).
- **The Brain:** not started. Only a draft API contract exists.
- **Users:** zero external users or design partners.

## 4. The architectural decision (adopted 2026-10-27)

**Muscle** = this repo: deterministic ETL, SQL audits, scheduling, alerting — **zero AI/LLM code** (enforced by
rule, CI deny-list planned). **Brain** = separate `flowforge-brain` service: FastAPI + Gemini (Vertex AI / AI
Studio), structured-JSON RCA over anonymized evidence; owns prompts, keys, and stored diagnoses. **One React UI**
pulls operational data from Core and diagnoses from the Brain; with no Brain attached, no AI UI appears.
Core→Brain traffic is asynchronous and off the pipeline's critical path (202 + `case_id`, short timeouts, circuit
breaker). Anonymization happens in Core before data leaves. Brain output is advisory only. Details:
`ARCHITECTURE.md`; execution plan for removing the legacy AI (≈3–4 days): `docs/BRAIN_DECOUPLING_PLAN.md`.

## 5. My assessment (Claude's opinion — please challenge it)

**What I think is right**
- The Muscle/Brain split is the correct call for revenue-critical software: it keeps a non-deterministic,
  third-party, rate-limited dependency out of the path that must be predictable, and it lets prompts/models change
  weekly without regression-testing the engine.
- Pushing bulk work into the database and keeping the orchestrator thin is a legitimate answer to "volume".
- The existing breadth (many DB types, RBAC/SSO/audit, DAG engine, retries, Celery) is a real foundation, not a
  mock-up.

**What worries me**
1. **The positioning outruns the product.** "Heavily optimized for extreme volume and strict compliance" is not
   yet true (§3). If it appears in README/marketing before the proof exists, telecom buyers — who will ask for
   volumes, references and compliance evidence — will find the gap in one meeting. I'd say "built for" or "designed
   toward", or earn the claim with a benchmark and a reviewed compliance posture first.
2. **No validated demand.** One maintainer, no external users, and a pivot from "lightweight, no enterprise
   complexity" to "enterprise telecom". Telecom sales cycles are long and the buyers are risk-averse. A design
   partner (even one operator's RA analyst) should shape the MVP before more platform work.
3. **Data egress is the hard problem, not the architecture.** Subscriber identifiers and call records are
   regulated. Anonymization rules, region/data-use terms of the model provider, and an option for a
   customer-hosted model endpoint decide whether any operator can use the Brain at all.
4. **Brain auth from the browser.** UI→Brain calls need short-lived, audience-scoped, asymmetrically-signed tokens;
   sharing the current HS256 secret would let Brain forge sessions.
5. **Open-source vs. enterprise:** MIT core + proprietary Brain is a workable model, but it needs a deliberate
   licensing/business decision, and the "hosted tier" idea currently contradicts a stated non-goal.
6. **Quality debt matters more for this buyer:** almost no mocked unit tests, two open SonarCloud findings, a
   Scorecard Code-Review score stuck at 0 for a solo maintainer, a React-router security upgrade pending.
7. **The Gemini model:** the brief names Gemini 1.5 Pro; model availability should be verified, and the model must
   stay a Brain configuration value.

## 6. Open items already tracked (`docs/TASKS.md`, 52 open)
AI decoupling (§0); fix local Gmail + two SonarCloud findings (§1); first-run friction, conditional steps,
react-router 7, streaming for large files (§2); mocked unit tests, Sentry, license audit (§3); supply-chain badges
(§4); go-to-market (§6) — **to be rewritten**, since published posts advertise "local AI"; strategic questions (§7).
Estimated ≈ 9–11 weeks full-time for §0–§6.

## 7. Questions I'd like Gemini to help decide (so planning is grounded)

1. **Which one leakage use case proves the product first** — dropped CDRs (count/sum reconciliation across switch →
   mediation → billing) or orphaned subscriptions (HLR vs. billing status)? Which needs the least new code?
2. **Target scale:** CDRs/day, file formats and sources (CSV, TAP3, ASN.1, DB extracts, Kafka?), and whether
   FlowForge ingests them or only audits data already in the operator's databases.
3. **Deployment reality:** on-prem/air-gapped inside the operator vs. managed; what that implies for the Brain
   (customer-hosted model?) and for the "no SaaS" non-goal.
4. **Compliance floor** for a first paying deployment (what an operator's security review will demand).
5. **Business model:** MIT core + proprietary Brain? Support/services? Who is the first customer and how do we reach them?
6. **Sequence:** should telecom-specific steps (reconciliation, conditional alerting, large-file streaming) come
   before the Brain, given the Brain adds value only after a reliable detection layer exists?
