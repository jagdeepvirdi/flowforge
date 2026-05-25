# FlowForge

**Database-driven pipeline orchestrator. Configure everything from the UI — DB procedures, reports, email (Gmail/M365/SMTP), Google Drive, OneDrive, SFTP, smart attachments, scheduling. No YAML. No Airflow complexity.**

[![Tests](https://github.com/jagdeepvirdi/flowforge/actions/workflows/test.yml/badge.svg)](https://github.com/jagdeepvirdi/flowforge/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/jagdeepvirdi/flowforge/graph/badge.svg)](https://codecov.io/gh/jagdeepvirdi/flowforge)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=jagdeepvirdi_flowforge&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=jagdeepvirdi_flowforge)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/jagdeepvirdi/flowforge/badge)](https://securityscorecards.dev/viewer/?uri=github.com/jagdeepvirdi/flowforge)

---

## What is FlowForge?

FlowForge runs ordered data pipelines: call database procedures, run queries, generate reports (Excel/PDF/CSV/JSON), send emails with smart attachment handling, upload files to Google Drive or OneDrive, and transfer files over SFTP. Everything is configured through a web frontend — no config files to edit, no Python DAGs to write.

Designed for solo developers, data analysts, and small teams who need lightweight automation without the overhead of enterprise orchestration tools.

---

## Features

### Pipeline Engine
- **No-YAML config** — pipelines, reports, email templates, and schedules are all managed in the UI
- **Multi-project workspace** — organize resources by team or department in one instance
- **10 step types** — db_procedure, db_query, report, email, drive_upload, onedrive_upload, data_load, bulk_load, sftp_transfer, ai_analyze
- **Step retry** — configurable retry count (0–10) and backoff delay per step
- **On-error control** — per-step `stop` or `continue` on failure
- **Failure webhook** — POST notification to any URL when a pipeline fails
- **Pipeline clone** — duplicate a pipeline with one click
- **YAML import/export** — from UI or CLI; useful for version control and migration

### Databases & Storage
- **Database support**: PostgreSQL, Oracle (`python-oracledb`, thin mode — no Instant Client), MySQL / MariaDB
- **Google Drive**: upload files, create shareable links, smart attachment fallback
- **OneDrive / SharePoint**: upload files via Microsoft Graph API, chunked upload for large files, shareable links
- **SFTP**: download or upload files; password or private-key auth (RSA / ECDSA / Ed25519)

### Email & Reports
- **Email providers**: Gmail (OAuth2), Microsoft 365 (MSAL + Graph API), SMTP (any server)
- **Smart attachments**: files over a configurable size threshold are automatically uploaded to Drive or OneDrive; the email body gets a shareable link instead
- **Query results in email**: embed live SQL query results — HTML table, key-value summary, or custom Jinja2 — directly in email bodies
- **Report formats**: Excel (openpyxl, optional template), CSV, PDF (WeasyPrint), JSON

### Multi-User & Access Control
- **Roles**: `admin`, `editor`, `viewer` — enforced on every API route and in the UI
- **User management**: admin UI to create users, change roles, delete accounts
- **Self-service password change**: any authenticated user can change their own password
- **JWT with revocation**: server-side token blocklist; `POST /api/auth/logout` invalidates the current token immediately

### Scheduling & Reliability
- **APScheduler** with PostgreSQL jobstore — scheduled jobs survive restarts
- **Visual cron builder**: frequency presets, live expression preview, next-5-runs display
- **Hot reload**: schedule changes sync to the scheduler automatically every 60 seconds
- **Celery / Redis task queue** (optional): when `FLOWFORGE_REDIS_URL` is set, pipeline runs are dispatched as Celery tasks; falls back to background threads without Redis
- **Graceful shutdown**: SIGTERM handler drains in-flight runs before exit

### AI Features (Ollama or Claude API)
- **AI chart generator**: "Visualize" button on Report Preview — sends column names + sample rows to Ollama; renders result with Recharts (bar, line, area, pie, scatter)
- **SQL Explainer**: "Explain" button in the SQL editor — plain-English summary of what a query does
- **SQL Optimizer**: "Optimize" button — side-by-side diff of original vs AI-suggested rewrite; accept with one click
- **Pipeline failure diagnosis**: "Explain this error" on failed step logs — 2–4 sentence cause and fix
- **Data Profiler**: one-click narrative summary of query result (structure, ranges, nulls, outliers)
- **Run history anomaly alerts**: statistical outlier detection (>2σ) on row counts and durations; Ollama narrative when anomaly is detected

### Security
- **AES-256-GCM** credential encryption for all DB and email provider configs stored in the database
- **bcrypt** admin password hashing; separate JWT signing secret from encryption key
- **Login rate limiting** (10/min per IP) and manual trigger rate limiting
- **Jinja2 SandboxedEnvironment** — no arbitrary code execution in templates
- **Env var allowlist** (`FLOWFORGE_TEMPLATE_ENV_VARS`) — restrict which env vars are accessible in templates
- **Path containment** check on report file download — prevents directory traversal
- **Procedure name validation** — blocks SQL injection via stored procedure names
- **SFTP strict host key checking** (`FLOWFORGE_SFTP_STRICT_HOSTKEYS=true`)
- **Audit log** — every login, pipeline run, config change, and webhook trigger logged with username attribution; file (rotating 10 MB × 5) + structured JSON stdout
- **SAST in CI** — `bandit` (Python) + `npm audit` on every push

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
| `email` | Send email with smart attachment handling (Drive or OneDrive fallback) |
| `drive_upload` | Upload a file to Google Drive; get a shareable link |
| `onedrive_upload` | Upload a file to OneDrive / SharePoint via Microsoft Graph API |
| `data_load` | Bulk-load data from a file (CSV/Excel) or SQL query into any configured DB; replace or append |
| `bulk_load` | Scan a directory for files, load to DB, archive after load; PostgreSQL COPY or chunked fallback |
| `sftp_transfer` | Download or upload files over SFTP; password or private-key auth; glob patterns |
| `ai_analyze` | Run a SQL query, summarize results with Claude or Ollama; result available as `{{ ai_summary }}` |

---

## Supported Technologies

| Category | Technologies |
|---|---|
| Databases | PostgreSQL, Oracle (python-oracledb, thin mode), MySQL / MariaDB |
| Email | Gmail (OAuth2), Microsoft 365 (MSAL + Graph API), SMTP (any server) |
| Cloud Storage | Google Drive, OneDrive / SharePoint |
| File Transfer | SFTP |
| Report formats | Excel (.xlsx), CSV, PDF (WeasyPrint), JSON |
| Scheduling | APScheduler (cron, PostgreSQL jobstore) |
| Task queue | Celery + Redis (optional — threads used when Redis is not configured) |
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
pip install -e ".[sftp]"          # SFTP transfer step (paramiko)
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
.\flowforge.ps1 start
```

**macOS / Linux:**
```bash
./flowforge.sh start
```

Both scripts start the Flask API, APScheduler, and Vite frontend together. Open `http://localhost:5173`.

#### 6. Production mode (serves built frontend from Flask)

```powershell
.\flowforge.ps1 start -Mode prod   # Windows
./flowforge.sh start prod          # macOS/Linux
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

Role is set per user by an admin. The UI automatically hides write actions for viewers.

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
│   ├── engine/              # runner, scheduler, launcher, context, shutdown
│   ├── steps/               # db_procedure, db_query, report, email, drive_upload,
│   │                        #   onedrive_upload, data_load, bulk_load, sftp_transfer, ai_analyze
│   ├── connections/         # PostgreSQL, Oracle, MySQL + factory
│   ├── email_providers/     # Gmail, M365, SMTP + factory
│   ├── reports/             # Excel, CSV, PDF, JSON generators
│   ├── storage/             # Google Drive, OneDrive clients
│   ├── crypto.py            # AES-256-GCM credential encryption
│   ├── db/                  # SQLAlchemy models + Alembic migrations (0001–0018)
│   └── api/                 # Flask REST API (routes, auth, validators, serializers)
├── frontend/                # React + Vite + TypeScript
│   └── src/
│       ├── pages/           # Dashboard, Pipelines, Reports, Emails, Connections,
│       │                    #   Recipients, RunHistory, Settings, Users
│       ├── components/      # pipeline/, email/, report/, shared/
│       └── lib/             # api.ts, auth.ts, types.ts, store.ts
├── docs/                    # Guides and runbook
├── tests/                   # pytest suite (742+ tests)
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
- [`docs/email-providers.md`](docs/email-providers.md) — SMTP, M365, and Gmail setup guides
- [`RUNBOOK.md`](RUNBOOK.md) — database migrations, startup sequence, production ops
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — dev setup, running tests, PR process
- [`CHANGELOG.md`](CHANGELOG.md) — version history

---

## Roadmap

| Version | Status | What shipped |
|---|---|---|
| v0.1.0 | ✅ | Pipeline engine, all core step types, all email providers, reports, Drive, scheduler, React frontend, Docker, CI, Alembic, AES-256 encryption, JWT auth |
| v0.1.3 | ✅ | Oracle Docker, `data_load` step, `python-oracledb` migration, JSON report format, scheduler sync fix, email provider `test()` |
| v0.1.4 | ✅ | Email preview modal, quick-attach Jinja2, docs from API, UI polish |
| v1.0.0 | ✅ | Pipeline variables (secrets), `bulk_load` step, multi-project support, query results in email, visual cron builder, run history pagination, loading skeletons, React Hook Form + Zod, error boundaries, CSS design tokens |
| v1.1.0 | ✅ | MySQL / MariaDB, OneDrive / SharePoint upload, SFTP transfer step, AI features (chart generator, SQL explainer/optimizer, failure diagnosis, data profiler, anomaly alerts), pipeline clone, YAML import/export, step retry + backoff, failure webhook, webhook/API trigger, JWT revocation, RBAC guards, SAST in CI |
| v1.2.0 | ✅ | Multi-user roles (admin / editor / viewer), user management UI, role-based frontend visibility, Celery / Redis task queue, `flowforge worker` CLI, responsive mobile layout, audit log username attribution |
| **v2** | Planned | Gunicorn docs, Prometheus metrics endpoint, audit log UI, retention policies, MFA (TOTP), SSO / OAuth2 login, report encryption at rest, GDPR export/deletion |
| **v3** | Backlog | S3 / Azure Blob, MSSQL / Snowflake, pipeline dependencies, parallel step execution, plugin system, Slack / Teams notifications |

---

## License

MIT — see [LICENSE](LICENSE).
