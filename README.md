# FlowForge

**Database-driven pipeline orchestrator. Configure everything from the UI — DB procedures, reports, email (Gmail/M365/SMTP), Google Drive, OneDrive, SFTP, smart attachments, scheduling. No YAML. No Airflow complexity.**

[![Tests](https://github.com/jagdeepvirdi/flowforge/actions/workflows/test.yml/badge.svg)](https://github.com/jagdeepvirdi/flowforge/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/jagdeepvirdi/flowforge/graph/badge.svg)](https://codecov.io/gh/jagdeepvirdi/flowforge)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=jagdeepvirdi_flowforge&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=jagdeepvirdi_flowforge)
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/13002/badge)](https://www.bestpractices.dev/projects/13002)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/jagdeepvirdi/flowforge/badge)](https://securityscorecards.dev/viewer/?uri=github.com/jagdeepvirdi/flowforge)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## What is FlowForge?

FlowForge runs ordered data pipelines: call database procedures, run queries, generate reports (Excel/PDF/CSV/JSON), send emails with smart attachment handling, upload files to Google Drive or OneDrive, and transfer files over SFTP. Everything is configured through a web frontend — no config files to edit, no Python DAGs to write.

Designed for solo developers, data analysts, and small teams who need lightweight automation without the overhead of enterprise orchestration tools.

---

## Features

### Pipeline Engine
- **No-YAML config** — pipelines, reports, email templates, and schedules are all managed in the UI
- **Multi-project workspace** — organize resources by team or department in one instance, with team-scoped project membership
- **17 step types** — db_procedure, db_query, report, email, drive_upload, onedrive_upload, s3_upload, azure_blob_upload, data_load, bulk_load, sftp_transfer, ssh_command, ssh_health_check, db_health_check, data_report, notification (Slack/Teams/Telegram), ai_analyze
- **Plugin system** — drop a custom `BaseStep` subclass into `FLOWFORGE_PLUGIN_DIR` to add community/internal step types without forking
- **Pipeline dependencies** — chain pipelines so a downstream one launches automatically after all its upstreams succeed; cycle detection included
- **Parallel step execution** — group steps with `parallel_group` to run them concurrently in a pipeline
- **Environment promotion** — clone a pipeline (steps + non-secret variables) into another project
- **Run diff view** — compare a run against the previous successful run: row count, duration, and file size deltas per step
- **Step retry** — configurable retry count (0–10) and backoff delay per step
- **On-error control** — per-step `stop` or `continue` on failure
- **Failure webhook** — POST notification to any URL when a pipeline fails
- **Pipeline clone** — duplicate a pipeline with one click
- **YAML import/export** — from UI or CLI; useful for version control and migration

### Databases & Storage
- **Database support**: PostgreSQL, Oracle (`python-oracledb`, thin mode — no Instant Client), MySQL / MariaDB, MSSQL, generic ODBC, Snowflake, BigQuery, Redshift
- **Google Drive**: upload files, create shareable links, smart attachment fallback
- **OneDrive / SharePoint**: upload files via Microsoft Graph API, chunked upload for large files, shareable links
- **AWS S3 / Azure Blob Storage**: upload step for either, alongside Drive/OneDrive smart-attachment fallback
- **SFTP**: download or upload files; password or private-key auth (RSA / ECDSA / Ed25519)
- **SSH**: run remote commands or collect health metrics (load, memory, disk, top processes) over a single SSH session

### Email & Reports
- **Email providers**: Gmail (OAuth2), Microsoft 365 (MSAL + Graph API), SMTP (any server), SendGrid, AWS SES, Mailgun
- **Chat notifications**: Slack, Microsoft Teams, and Telegram via the `notification` step
- **Smart attachments**: files over a configurable size threshold are automatically uploaded to Drive, OneDrive, S3, or Azure Blob; the email body gets a shareable link instead
- **Query results in email**: embed live SQL query results — HTML table, key-value summary, or custom Jinja2 — directly in email bodies
- **Report formats**: Excel (openpyxl, optional template, conditional column formatting), CSV, PDF (WeasyPrint), JSON

### Multi-User & Access Control
- **Roles**: `admin`, `editor`, `viewer` — enforced on every API route and in the UI
- **User management**: admin UI to create users, change roles, delete accounts
- **MFA**: TOTP-based two-factor auth with QR code enrollment and 10 backup codes
- **SSO**: Google OAuth2, Microsoft OAuth2, and SAML 2.0 (Okta, Azure AD, PingFederate)
- **Self-service password reset**: email-based reset flow, plus self-service password change for any authenticated user
- **IP allowlisting**: restrict `/api/*` to a configured CIDR list
- **JWT with revocation**: server-side token blocklist; `POST /api/auth/logout` invalidates the current token immediately

### Scheduling & Reliability
- **APScheduler** with PostgreSQL jobstore — scheduled jobs survive restarts
- **Visual cron builder**: frequency presets, live expression preview, next-5-runs display
- **Hot reload**: schedule changes sync to the scheduler automatically every 60 seconds
- **Celery / Redis task queue** (optional): when `FLOWFORGE_REDIS_URL` is set, pipeline runs are dispatched as Celery tasks; falls back to background threads without Redis
- **Distributed concurrency lock**: Redis-backed run-limit lock so multiple API/worker instances can be scaled horizontally without over-running a pipeline
- **Graceful shutdown**: SIGTERM handler drains in-flight runs before exit

### Observability & Production Ops
- **Prometheus metrics**: `GET /api/metrics` exposes run totals, active runs, and queue depth in plain-text exposition format
- **Celery Flower dashboard**: optional `--profile monitoring` Docker Compose service for worker/task visibility
- **Gunicorn + Nginx deployment guide**: gevent workers, systemd units, TLS termination — see `docs/deployment.md` / `RUNBOOK.md`
- **SQLAlchemy pool tuning**: pool size/overflow/timeout/recycle configurable via env vars, with PgBouncer guidance for 100+ concurrent pipelines

### AI Features (Ollama or Claude API)
- **AI chart generator**: "Visualize" button on Report Preview — sends column names + sample rows to Ollama; renders result with Recharts (bar, line, area, pie, scatter)
- **SQL Explainer**: "Explain" button in the SQL editor — plain-English summary of what a query does
- **SQL Optimizer**: "Optimize" button — side-by-side diff of original vs AI-suggested rewrite; accept with one click
- **Pipeline failure diagnosis**: "Explain this error" on failed step logs — 2–4 sentence cause and fix
- **Data Profiler**: one-click narrative summary of query result (structure, ranges, nulls, outliers)
- **Run history anomaly alerts**: statistical outlier detection (>2σ) on row counts and durations; Ollama narrative when anomaly is detected

### Security
- **AES-256-GCM** credential encryption for all DB and email provider configs stored in the database
- **Report encryption at rest** — optional (`FLOWFORGE_ENCRYPT_OUTPUT=true`); files decrypted transparently on download
- **bcrypt** admin password hashing; separate JWT signing secret from encryption key
- **GDPR data export & purge** — admin endpoints to export a user's profile/audit/run history, or anonymise-and-delete
- **Login rate limiting** (10/min per IP) and manual trigger rate limiting
- **Jinja2 SandboxedEnvironment** — no arbitrary code execution in templates
- **Env var allowlist** (`FLOWFORGE_TEMPLATE_ENV_VARS`) — restrict which env vars are accessible in templates
- **Path containment** check on report file download — prevents directory traversal
- **Procedure name validation** — blocks SQL injection via stored procedure names
- **SSRF guard** on outbound webhook/notification URLs — rejects internal/private-network targets
- **SFTP strict host key checking** (`FLOWFORGE_SFTP_STRICT_HOSTKEYS=true`)
- **Audit log** — every login, pipeline run, config change, and webhook trigger logged with username attribution; file (rotating 10 MB × 5) + structured JSON stdout
- **SAST in CI** — `bandit` (Python) + `npm audit` on every push; TruffleHog secrets scan; property-based fuzz tests (Hypothesis)
- **Signed releases** — SLSA build provenance attestation on tagged releases; PyPI publish via OIDC trusted publishing

### Developer Experience
- **In-app help**: context-sensitive help drawer, page intro cards, field tooltips, concept glossary
- **Webhook / API trigger**: `POST /pipelines/{id}/trigger?token=...` for external integration; per-pipeline tokens with audit trail
- **Output cleanup**: CLI command + daily scheduler job to prune old report files by TTL
- **Docker Compose**: one-command local stack (API + frontend + PostgreSQL + scheduler + Redis + Celery worker)
- **GitHub Actions CI**: full pytest suite + SAST + frontend audit on every push and PR

---

## Comparison

| Feature | FlowForge | Airflow | Prefect | Cron + Scripts |
|---|---|---|---|---|
| Setup time | Minutes | Hours | Minutes | Minutes |
| Config interface | Web UI | Python DAGs | Python flows | Edit files |
| Email sending | Built-in | Plugin | Plugin | DIY |
| Report generation | Built-in | DIY | DIY | DIY |
| Google Drive / OneDrive | Built-in | DIY | DIY | DIY |
| Smart attachments | Built-in | DIY | DIY | DIY |
| Multi-user roles | Built-in | Built-in | Built-in | DIY |
| AI analysis | Built-in (Ollama/Claude) | DIY | DIY | DIY |
| Scheduling | Built-in UI | Built-in | Built-in | OS cron |
| Run history / logs | Built-in UI | Built-in | Built-in | DIY |
| SFTP transfer | Built-in | Plugin | Plugin | DIY |
| Target users | Solo / small teams | Data engineers | Data engineers | Any |

---

## Step Types

| Step | What it does |
|---|---|
| `db_procedure` | Call a stored procedure or Oracle package |
| `db_query` | Run a SQL query and write results to a table; capture a scalar or full rows into pipeline context |
| `report` | Generate Excel / CSV / PDF / JSON from a SQL query |
| `email` | Send email with smart attachment handling (Drive, OneDrive, S3, or Azure Blob fallback) |
| `drive_upload` | Upload a file to Google Drive; get a shareable link |
| `onedrive_upload` | Upload a file to OneDrive / SharePoint via Microsoft Graph API |
| `s3_upload` | Upload a file to an AWS S3 bucket |
| `azure_blob_upload` | Upload a file to Azure Blob Storage |
| `data_load` | Bulk-load data from a file (CSV/Excel) or SQL query into any configured DB; replace or append |
| `bulk_load` | Scan a directory for files, load to DB, archive after load; PostgreSQL COPY or chunked fallback |
| `sftp_transfer` | Download or upload files over SFTP; password or private-key auth; glob patterns |
| `ssh_command` | Run a remote command over SSH; optionally save stdout/stderr to a file |
| `ssh_health_check` | Collect load/memory/disk/process metrics over one SSH session; outputs a report file |
| `db_health_check` | Collect DB health metrics (sessions, cache hit ratio, replication lag, etc.); outputs a report file |
| `data_report` | Run an arbitrary script and turn its output into a report |
| `notification` | Send a message to Slack, Microsoft Teams, or Telegram |
| `ai_analyze` | Run a SQL query, summarize results with Claude or Ollama; result available as `{{ ai_summary }}` |

Custom step types can also be added via the [plugin system](docs/plugins.md) without forking FlowForge.

---

## Supported Technologies

| Category | Technologies |
|---|---|
| Databases | PostgreSQL, Oracle (python-oracledb, thin mode), MySQL / MariaDB, MSSQL, generic ODBC, Snowflake, BigQuery, Redshift |
| Email | Gmail (OAuth2), Microsoft 365 (MSAL + Graph API), SMTP (any server), SendGrid, AWS SES, Mailgun |
| Chat notifications | Slack, Microsoft Teams, Telegram |
| Cloud Storage | Google Drive, OneDrive / SharePoint, AWS S3, Azure Blob Storage |
| File Transfer | SFTP, SSH |
| Report formats | Excel (.xlsx), CSV, PDF (WeasyPrint), JSON |
| Scheduling | APScheduler (cron, PostgreSQL jobstore) |
| Task queue | Celery + Redis (optional — threads used when Redis is not configured) |
| Auth | Username/password + JWT, MFA (TOTP), SSO (Google, Microsoft, SAML 2.0) |
| Monitoring | Prometheus metrics endpoint, Celery Flower dashboard |
| AI (optional) | Claude API (Anthropic), Ollama (local, zero cost) |

---

## Quick Start

### Option A — Docker Compose (recommended)

```bash
git clone https://github.com/jagdeepvirdi/flowforge.git
cd flowforge
cp .env.example .env
# Edit .env — set FLOWFORGE_SECRET_KEY and FLOWFORGE_PASSWORD at minimum
docker compose up
```

Open `http://localhost:5000`. The stack starts the API, frontend (Nginx), PostgreSQL, scheduler, Redis, and a Celery worker.

For Oracle support:

```bash
docker compose -f docker-compose.yml -f docker-compose.oracle.yml up
```

### Option B — Local Development

#### 1. Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL (for FlowForge's own config database)

#### 2. Install

```bash
pip install -e .
# Optional extras:
pip install -e ".[pdf]"           # PDF report generation (WeasyPrint)
pip install -e ".[oracle]"        # Oracle database support (python-oracledb)
pip install -e ".[gmail]"         # Gmail email provider + Google Drive
pip install -e ".[microsoft365]"  # Microsoft 365 email + OneDrive
pip install -e ".[mysql]"         # MySQL / MariaDB support
pip install -e ".[mssql]"         # MSSQL / SQL Server support (pyodbc)
pip install -e ".[snowflake]"     # Snowflake connector
pip install -e ".[bigquery]"      # BigQuery connector
pip install -e ".[ses]"           # AWS SES email provider + S3 upload
pip install -e ".[azure_blob]"    # Azure Blob Storage upload
pip install -e ".[sftp]"          # SFTP transfer step (paramiko)
pip install -e ".[sso]"           # SSO: Google, Microsoft, SAML 2.0
pip install -e ".[claude]"        # ai_analyze step via Claude API
pip install -e ".[all]"           # Everything above
```

#### 3. Configure

```bash
cp .env.example .env
# Set FLOWFORGE_DB_URL, FLOWFORGE_SECRET_KEY, and FLOWFORGE_PASSWORD at minimum
```

#### 4. Initialize the database and create the admin user

```bash
flowforge db upgrade
flowforge db seed
```

#### 5. Start

**Windows:**
```powershell
.\flowforge.ps1 dev start
```

**macOS / Linux:**
```bash
./flowforge.sh dev start
```

Both scripts start the Flask API, APScheduler, and Vite frontend together. Open `http://localhost:5173`.

Other actions: `stop`, `restart`, and `status` (e.g. `.\flowforge.ps1 dev status`).

#### 6. Production mode (serves built frontend from Flask)

```powershell
.\flowforge.ps1 prod start   # Windows
./flowforge.sh prod start    # macOS/Linux
```

#### 7. With Celery task queue (optional)

```bash
# Start Redis, then run a worker alongside the web server:
flowforge worker --concurrency 4
# Or: celery -A flowforge.celery_app worker --concurrency 4 --loglevel info
```

When `FLOWFORGE_REDIS_URL` is set in `.env`, pipeline runs are dispatched to the Celery worker automatically. Without it, runs execute in background threads.

---

## CLI Reference

```bash
# Server
flowforge web                           # start Flask dev server
flowforge schedule                      # start APScheduler daemon
flowforge worker [--concurrency N]      # start Celery worker (requires FLOWFORGE_REDIS_URL)

# Pipelines
flowforge run "Monthly Revenue Report"  # run a pipeline by name
flowforge list                          # list all pipelines with schedule and status
flowforge validate "Pipeline Name"      # validate pipeline config and connections
flowforge export "Pipeline Name"        # export pipeline as YAML
flowforge import pipeline.yaml          # import pipeline from YAML (--overwrite to replace)

# Database
flowforge db upgrade [revision]         # apply Alembic migrations (default: head)
flowforge db downgrade <revision>       # revert migrations
flowforge db current                    # show current migration revision
flowforge db stamp <revision>           # mark DB at revision without running migrations
flowforge db seed                       # create admin user from env vars (run once after upgrade)

# Maintenance
flowforge cleanup [--days N] [--dry-run]  # remove output files older than N days

# OAuth2 setup wizards
flowforge setup gmail
flowforge setup microsoft365
```

---

## Variable System

Available in every config field rendered via Jinja2:

| Variable | Example value |
|---|---|
| `{{ current_date }}` | `2026-05-25` |
| `{{ current_month }}` | `2026-05` |
| `{{ current_year }}` | `2026` |
| `{{ yesterday }}` | `2026-05-24` |
| `{{ week_start }}` | `2026-05-18` (Monday) |
| `{{ week_end }}` | `2026-05-24` (Sunday) |
| `{{ month_start }}` | `2026-05-01` |
| `{{ month_end }}` | `2026-05-31` |
| `{{ quarter_start }}` | `2026-04-01` |
| `{{ quarter_end }}` | `2026-06-30` |
| `{{ timestamp }}` | `20260525142304` |
| `{{ run_id }}` | UUID of the current pipeline run |
| `{{ pipeline_name }}` | `Monthly Revenue Report` |
| `{{ env.MY_VAR }}` | Any allowed environment variable |
| `{{ steps.name.output_path }}` | Output file path from a previous step |
| `{{ steps.name.drive_url }}` | Drive / OneDrive URL from a previous step |
| `{{ steps.name.rows_affected }}` | Row count from a previous step |
| `{{ steps.name.table_html }}` | HTML table of captured query rows |
| `{{ steps.name.ai_summary }}` | AI narrative from an `ai_analyze` step |
| `{{ my_var }}` / `{{ vars.my_var }}` | Pipeline-level variable (secrets encrypted at rest) |

---

## Multi-User Roles

| Role | Permissions |
|---|---|
| `admin` | Full access — manage users, connections, providers, all pipeline operations |
| `editor` | Create / edit / delete pipelines, reports, emails, recipients; run pipelines |
| `viewer` | Read-only — view pipelines, run history, reports; no write operations |

Role is set per user by an admin. The UI automatically hides write actions for viewers. Users can also sign in via MFA (TOTP), SSO (Google, Microsoft, or SAML 2.0), or reset a forgotten password via emailed link — see the [Security](#security) features above.

---

## API Trigger (Webhook)

Pipelines can be triggered externally without a UI login:

```bash
# Create a token in the UI (Settings → Pipeline → Webhook Tokens)
# Then trigger via HTTP:
curl -X POST "https://your-flowforge/api/pipelines/{id}/trigger?token=flwf_..."
```

Returns `{ run_id, status, pipeline_name }` with HTTP 202. The token is audited on every use.

---

## Project Structure

```
flowforge/
├── flowforge/               # Python package
│   ├── cli.py               # Click CLI
│   ├── celery_app.py        # Celery instance + Flask context wiring
│   ├── tasks.py             # Celery task definitions
│   ├── audit.py             # Audit log (file + JSON stdout)
│   ├── engine/              # runner, scheduler, launcher, loader (+ plugins), context, shutdown
│   ├── steps/               # db_procedure, db_query, report, email, drive_upload, onedrive_upload,
│   │                        #   s3_upload, azure_blob_upload, data_load, bulk_load, sftp_transfer,
│   │                        #   ssh_command, ssh_health_check, db_health_check, script_report,
│   │                        #   notification, ai_analyze
│   ├── connections/         # PostgreSQL, Oracle, MySQL, MSSQL, ODBC, Snowflake, BigQuery, Redshift + factory
│   ├── email_providers/     # Gmail, M365, SMTP, SendGrid, SES, Mailgun + factory
│   ├── reports/             # Excel, CSV, PDF, JSON generators
│   ├── storage/             # Google Drive, OneDrive, S3, Azure Blob clients
│   ├── crypto.py            # AES-256-GCM credential + file encryption
│   ├── net_guard.py         # SSRF guard for outbound webhook/notification URLs
│   ├── db/                  # SQLAlchemy models + Alembic migrations
│   └── api/                 # Flask REST API (routes, auth, mfa, sso, validators, serializers)
├── frontend/                # React + Vite + TypeScript
│   └── src/
│       ├── pages/           # Dashboard, Pipelines, Reports, Emails, Connections, Recipients,
│       │                    #   RunHistory, Settings, Users, BulkLoads, Projects, Login, AuditLog
│       ├── components/      # pipeline/, email/, report/, runs/, shared/
│       └── lib/             # api.ts, auth.ts, types.ts, store.ts
├── docs/                    # Guides and runbook
├── tests/                   # pytest suite (1,800+ tests)
├── .github/workflows/       # GitHub Actions CI
├── docker-compose.yml       # API + frontend + PostgreSQL + scheduler + Redis + worker
├── docker-compose.oracle.yml  # Oracle 23c overlay
├── flowforge.ps1            # Windows dev/prod startup script
├── flowforge.sh             # macOS/Linux dev/prod startup script
├── pyproject.toml
├── .env.example
└── CHANGELOG.md
```

---

## Documentation

- [`docs/getting-started.md`](docs/getting-started.md) — end-to-end setup walkthrough
- [`docs/step-types.md`](docs/step-types.md) — full config reference for all step types
- [`docs/email-providers.md`](docs/email-providers.md) — SMTP, M365, Gmail, SendGrid, SES, and Mailgun setup guides
- [`docs/plugins.md`](docs/plugins.md) — writing a custom plugin step type
- [`docs/deployment.md`](docs/deployment.md) — production deployment (Docker Compose or Gunicorn + Nginx + systemd)
- [`docs/security.md`](docs/security.md) / [`docs/threat-model.md`](docs/threat-model.md) / [`docs/data-flow.md`](docs/data-flow.md) — security model, threat model, and compliance reference
- [`docs/RUNBOOK.md`](docs/RUNBOOK.md) — database migrations, startup sequence, production ops
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — dev setup, running tests, PR process
- [`CHANGELOG.md`](CHANGELOG.md) — version history
- [`ROADMAP.md`](ROADMAP.md) / [`docs/TASKS.md`](docs/TASKS.md) — current status and active work (source of truth over the table below)

---

## Roadmap

> [`ROADMAP.md`](ROADMAP.md) and [`docs/TASKS.md`](docs/TASKS.md) are the continuously-updated
> source of truth for what's shipped — treat the table below as a summary snapshot, not the
> latest word.

| Version | Status | What shipped |
|---|---|---|
| v0.1.0 | ✅ | Pipeline engine, all core step types, all email providers, reports, Drive, scheduler, React frontend, Docker, CI, Alembic, AES-256 encryption, JWT auth |
| v0.1.3 | ✅ | Oracle Docker, `data_load` step, `python-oracledb` migration, JSON report format, scheduler sync fix, email provider `test()` |
| v0.1.4 | ✅ | Email preview modal, quick-attach Jinja2, docs from API, UI polish |
| v1.0.0 | ✅ | Pipeline variables (secrets), `bulk_load` step, multi-project support, query results in email, visual cron builder, run history pagination, loading skeletons, React Hook Form + Zod, error boundaries, CSS design tokens |
| v1.1.0 | ✅ | MySQL / MariaDB, OneDrive / SharePoint upload, SFTP transfer step, AI features (chart generator, SQL explainer/optimizer, failure diagnosis, data profiler, anomaly alerts), pipeline clone, YAML import/export, step retry + backoff, failure webhook, webhook/API trigger, JWT revocation, RBAC guards, SAST in CI |
| v1.2.0 | ✅ | Multi-user roles (admin / editor / viewer), user management UI, role-based frontend visibility, Celery / Redis task queue, `flowforge worker` CLI, responsive mobile layout, audit log username attribution |
| Since v1.2.0 | ✅ | SSH steps (command, health check) + DB health check + script reports; Gunicorn/Nginx production hardening, connection-pool tuning, Prometheus metrics, Celery Flower; MFA (TOTP), SSO (Google/Microsoft/SAML 2.0), GDPR export/purge, IP allowlisting, report encryption at rest, secrets scanning, password reset; MSSQL/ODBC/Snowflake/BigQuery/Redshift connectors; SendGrid/SES/Mailgun providers + Slack/Teams/Telegram notification step; S3/Azure Blob upload; plugin step-type system; pipeline dependencies + parallel step execution; run diff view; report column formatting; environment promotion; team-scoped project membership; distributed Redis concurrency lock; fuzzing (Hypothesis), signed releases (SLSA), PyPI publish; full Tailwind CSS frontend migration |
| **Not yet built** | — | Visual drag-and-drop pipeline canvas (biggest gap vs. Airflow/n8n/Dagster); OSS-Fuzz registration; cosign-signed release artifacts |

---

## Contributing

**Obtain:** Install via Docker Compose (`docker compose up`) or locally — see [Quick Start](#quick-start) above.

**Feedback:** Use [GitHub Issues](https://github.com/jagdeepvirdi/flowforge/issues) to report bugs or request features. Please include your FlowForge version, Python version, OS, steps to reproduce, and any relevant log output from `ff_step_runs.logs`.

**Contribute:** See [`CONTRIBUTING.md`](CONTRIBUTING.md) for dev setup, running tests, adding step types, and the PR process. All contributions welcome — bug fixes, new step types, documentation improvements, and test coverage.

---

## License

MIT — see [LICENSE](LICENSE).
