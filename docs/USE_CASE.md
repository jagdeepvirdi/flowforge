# FlowForge — Use Cases

Who uses FlowForge, what problem it solves for them, and why it fits better than the alternatives.

---

## The Core Problem FlowForge Solves

At almost every mid-size company there is a person — usually a data analyst, BI developer, or finance analyst — who:

- Manually exports Oracle or PostgreSQL data to Excel every Monday morning
- Emails it to 15 people from their own Gmail account
- Has been doing this for 3 years
- Is one resignation away from the whole process breaking

They know SQL. They don't know Python, don't run servers, and don't want to learn Airflow. They need automation that works the same way they do: databases, Excel, and email.

FlowForge replaces that entirely — with scheduling, run history, and zero infrastructure expertise required.

---

## Who This Is For

**Primary:** Data analysts, BI developers, and reporting engineers at companies with 10–500 employees.

**Secondary:** Solo developers and small engineering teams automating data movements between systems.

**Not for:** Data engineering platforms (use Airflow/Dagster), event-driven microservices (use Temporal/Conductor), or no-code business automation (use Zapier/n8n).

---

## Use Cases by Industry

### Finance & Accounting

| Pipeline | Steps | Why FlowForge |
|---|---|---|
| Monthly P&L report | Oracle query → Excel report → email to CFO + board | Oracle first-class, M365 email, recurring schedule |
| Weekly cash flow summary | PostgreSQL query → Excel → email finance team | `{{ week_start }}` / `{{ week_end }}` built-in |
| Daily reconciliation check | DB query → capture rows → email with result table if mismatch | Query-results-in-email: no attachment needed |
| Month-end close | Call Oracle stored procedure → generate summary → email confirmation | `db_procedure` + `email` step |
| Accounts receivable aging | AR query → Excel (multi-sheet template) → email collections team | Excel template support |

### Human Resources

| Pipeline | Steps | Why FlowForge |
|---|---|---|
| Weekly headcount report | HRIS query → CSV → email to all managers | Simple, recurring, no code |
| New hire onboarding data load | CSV drop from HR system → `bulk_load` to DB | Directory watching + bulk load |
| Monthly attrition report | Query → Excel → email HR director | `{{ current_month }}` in filename |
| Payroll audit extract | Sensitive query → encrypted report → email payroll team | Secret pipeline vars for credentials |

### Operations & Logistics

| Pipeline | Steps | Why FlowForge |
|---|---|---|
| Daily dispatch summary | Route query → PDF report → email dispatch team at 6am | PDF format, scheduled at dawn |
| Inventory reorder alert | Stock query → capture low-stock rows → email if any rows returned | Conditional email via query capture |
| End-of-day load confirmation | `db_procedure` (close day) → query results → email ops manager | Procedure + audit email in one pipeline |
| Supplier data sync | Supplier DB query → `data_load` to internal PostgreSQL | Cross-DB ETL without writing Python |

### IT & Data Engineering

| Pipeline | Steps | Why FlowForge |
|---|---|---|
| Legacy Oracle → modern PostgreSQL | Oracle query → `data_load` to PostgreSQL | Unique Oracle support is a real differentiator |
| Nightly staging refresh | `db_procedure` (truncate) → `db_query` (populate) → email confirmation | Chained steps, one pipeline |
| Data quality monitoring | Quality check query → capture failing rows → email alert with rows in body | Query-results-in-email for inline alerting |
| ETL pipeline audit | Run procedure → capture counts → email reconciliation report | Full audit trail in Run History |

### Sales & Marketing

| Pipeline | Steps | Why FlowForge |
|---|---|---|
| Weekly pipeline report | CRM DB query → Excel → email sales managers | `{{ week_start }}` built-in |
| Monthly campaign performance | Analytics query → Excel + Drive upload → share link in email | Smart attachment for large reports |
| Customer segment extract | Query → CSV → email marketing team | Fast, repeatable |
| Investor metrics report | KPI query → Excel → Google Drive (shareable) → email investors | Drive-first workflow |
| AI-generated insight digest | `ai_analyze` on sales data → email body includes an AI-generated summary (Ollama, Claude, or Gemini) | No LLM coding required; zero API cost with Ollama |

### Small SaaS / Startups

| Pipeline | Steps | Why FlowForge |
|---|---|---|
| Weekly user metrics to investors | Query → Excel → Drive upload → email | Drive link in email; no attachment size worry |
| Subscription churn alert | Churn query → capture rows → daily email to founders | Query capture + inline table in email |
| Usage data extract for support | Query → CSV → email support team | Straightforward data export |
| SFTP data ingest | `sftp_transfer` download from partner SFTP → `bulk_load` to DB | No scripting; password or key auth |
| OneDrive report distribution | Report → `onedrive_upload` → shareable link in email | Microsoft 365 shops; no Google Drive needed |

### AI-Assisted Pipelines (Ollama by default — zero cost, data stays local; Claude/Gemini optional)

| Pipeline | Steps | Why FlowForge |
|---|---|---|
| Monthly narrative summary | `ai_analyze` → plain-English summary injected into email body | `{{ ai_summary }}` available to downstream steps |
| Anomaly alerting | Run History Anomaly Alerts flag outlier steps; AI narrative explains the deviation (Ollama, falling back to Claude/Gemini if configured) | Statistical detection + optional narrative |
| SQL optimisation in report designer | SQL Optimizer rewrites slow queries; side-by-side diff shown | No DBA required for basic index hints |
| Chart suggestion | AI Chart Generator picks chart type from query columns | One click from preview to visualisation |

---

## What Makes FlowForge Different

### vs. Cron + Scripts
You get: a UI to configure everything, run history with step-level logs, scheduling without editing crontab, email/Drive built in, and no Python required. The "script person" can leave and someone else can maintain it.

### vs. Apache Airflow
Airflow is built for data engineers writing Python DAGs. FlowForge is built for SQL people. Airflow requires a cluster (Celery workers, Redis, PostgreSQL, Flower) just to get started. FlowForge runs on one server with `docker compose up` — the same Celery/Redis/Flower stack exists in FlowForge too, but only as an opt-in for horizontal scaling (`flowforge worker`, `FLOWFORGE_REDIS_URL`); a default install never touches it. Setup is minutes vs. hours.

### vs. Prefect / Dagster
Same issue — code-first, Python-first, engineer-first. Great tools for the right audience. FlowForge's audience doesn't write Python flows.

### vs. n8n
n8n is a visual workflow builder great for API-to-API automation and business process flows. FlowForge is SQL-native: the core actions are database procedures, SQL queries, and report generation. n8n treats databases as a connector; FlowForge treats them as the primary source of truth.

### vs. Zapier / Make
SaaS, expensive at volume, not SQL-native, no Oracle, no custom report generation. FlowForge is self-hosted, $0/month, and purpose-built for data workflows.

---

## The Unique Oracle Advantage

Almost every major enterprise runs some Oracle. Most orchestrators treat Oracle as an afterthought — a JDBC connector if you're lucky. FlowForge has:

- First-class `package.procedure` syntax (`pkg_revenue.populate_monthly_summary`)
- LOB column handling
- Oracle-specific type coercion (DATE, TIMESTAMP, NUMBER)
- `python-oracledb` in thin mode — no Oracle Instant Client required

For any company migrating from Oracle to PostgreSQL, FlowForge is uniquely positioned as the bridge: query from Oracle, load to PostgreSQL, email a reconciliation report.

---

## Limitations to Be Honest About

| Limitation | Implication |
|---|---|
| No conditional branching | Can't say "only send email if row count > 0" — workaround: always send, filter in query |

---

## Real-World Sizing

FlowForge runs comfortably on a single small server or VM for:

- Up to ~100 pipelines
- Up to ~500 runs/day
- Up to ~20 simultaneous runs
- Report files up to ~500MB (larger → auto-uploaded to Drive)

Beyond single-server scale, FlowForge already ships a horizontal-scaling path: `flowforge worker`
dispatches pipeline runs to Celery workers instead of in-process threads, backed by a
Redis-distributed concurrency lock (`FLOWFORGE_REDIS_URL`) that holds `FLOWFORGE_MAX_CONCURRENT_RUNS`
correctly across multiple Gunicorn/Celery processes — see `docs/deployment.md` and `docs/RUNBOOK.md`
for setup.

---

*See also: `docs/TASKS.md` (v2 multi-user + high-concurrency roadmap), `docs/CODEBASE_REVIEW.md` (market comparison section)*
