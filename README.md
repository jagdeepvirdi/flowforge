# FlowForge

**Database-driven pipeline orchestrator. Configure everything from the UI — DB procedures, reports, email (Gmail/M365/SMTP), Google Drive, smart attachments, scheduling. No YAML. No Airflow complexity.**

[![Tests](https://github.com/jagdeepvirdi/flowforge/actions/workflows/test.yml/badge.svg)](https://github.com/jagdeepvirdi/flowforge/actions/workflows/test.yml)

---

## What is FlowForge?

FlowForge runs ordered data pipelines: call database procedures, run queries, generate reports (Excel/PDF/CSV), send emails with smart attachment handling, and upload files to Google Drive. Everything is configured through a web frontend — no config files to edit.

Designed for solo developers, data analysts, and small teams who need lightweight automation without the overhead of enterprise orchestration tools.

---

## Features

- **No-YAML config** — pipelines, reports, email templates, and schedules are all managed via UI
- **Step types**: `db_procedure`, `db_query`, `report`, `email`, `drive_upload`, `data_load`
- **Database support**: PostgreSQL and Oracle (pluggable `BaseConnection` interface)
- **Email providers**: Gmail (OAuth2), Microsoft 365 (MSAL + Graph API), SMTP (any server)
- **Smart attachments**: files over a configurable size threshold are automatically uploaded to Google Drive; the email body gets a shareable link instead
- **Report formats**: Excel (openpyxl, optional template), CSV, PDF (WeasyPrint)
- **Google Drive**: upload files, create shareable links, smart attachment fallback
- **Jinja2 variable system**: date/range helpers, run context, step outputs, env vars, pipeline vars — available in every config field
- **Scheduling**: APScheduler with cron expressions and hot reload, managed from the UI
- **Visual cron builder**: frequency presets, live expression preview, next-5-runs display
- **Run history**: step-level logs, timing, Drive links, and email recipients per run
- **In-app help**: context-sensitive help drawer, page intro cards, field tooltips, concept glossary
- **Security**: AES-256-GCM credential encryption, bcrypt admin password, JWT auth, login rate limiting
- **Docker Compose**: one-command local stack (API + frontend + PostgreSQL)
- **GitHub Actions CI**: full pytest suite on every push and PR
- **Output cleanup**: CLI command + daily scheduler job to prune old report files

---

## Comparison

| Feature | FlowForge | Airflow | Prefect | Cron + Scripts |
|---|---|---|---|---|
| Setup time | Minutes | Hours | Minutes | Minutes |
| Config interface | Web UI | Python DAGs | Python flows | Edit files |
| Email sending | Built-in | Plugin | Plugin | DIY |
| Report generation | Built-in | DIY | DIY | DIY |
| Google Drive | Built-in | DIY | DIY | DIY |
| Smart attachments | Built-in | DIY | DIY | DIY |
| Scheduling | Built-in UI | Built-in | Built-in | OS cron |
| Run history / logs | Built-in UI | Built-in | Built-in | DIY |
| Target users | Solo / small teams | Data engineers | Data engineers | Any |

---

## Step Types

| Step | What it does |
|---|---|
| `db_procedure` | Call a stored procedure or Oracle package |
| `db_query` | Run a SQL query and write results to a table; optionally capture a scalar into pipeline context |
| `report` | Generate Excel / CSV / PDF / JSON from a SQL query |
| `email` | Send email with smart attachment handling |
| `drive_upload` | Upload a file to Google Drive |
| `data_load` | Bulk-load data into any DB from a file (CSV/Excel) or SQL query; replace or append mode |
| `ai_analyze` | Summarize query results with Claude or Ollama *(v2)* |

---

## Supported Technologies

| Category | Technologies |
|---|---|
| Databases | PostgreSQL, Oracle |
| Email | Gmail (OAuth2), Microsoft 365 (MSAL), SMTP |
| Storage | Google Drive |
| Report formats | Excel (.xlsx), CSV, PDF |
| Scheduling | APScheduler (cron) |
| AI (optional) | Claude API, Ollama (local) |

---

## Quick Start

### Option A — Docker Compose

```bash
git clone https://github.com/jagdeepvirdi/flowforge.git
cd flowforge
cp .env.example .env          # set FLOWFORGE_SECRET_KEY at minimum
docker compose up
```

Open `http://localhost:5000`.

### Option B — Local Development

#### 1. Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL (for FlowForge's own config database)

#### 2. Install

```bash
pip install -e .
# With PDF support:
pip install -e .[pdf]
# With Oracle support:
pip install -e .[oracle]
# With Gmail / Drive support:
pip install -e .[gmail]
# With Microsoft 365 support:
pip install -e .[microsoft365]
```

#### 3. Configure

```bash
cp .env.example .env
# Edit .env — set FLOWFORGE_DB_URL and FLOWFORGE_SECRET_KEY at minimum
```

#### 4. Initialize the database

```bash
alembic upgrade head
```

#### 5. Start the dev server

**Windows:**
```powershell
.\flowforge.ps1 start
```

**macOS / Linux:**
```bash
./flowforge.sh start
```

Both scripts start the Flask API, APScheduler, and Vite frontend together. Open `http://localhost:5173`.

#### 6. Prod mode

**Windows:**
```powershell
.\flowforge.ps1 start -Mode prod
```

**macOS / Linux:**
```bash
./flowforge.sh start prod
```

#### 7. Stop

**Windows:**
```powershell
.\flowforge.ps1 stop
```

**macOS / Linux:**
```bash
./flowforge.sh stop
```

---

## CLI Reference

```bash
flowforge web                          # start Flask dev server
flowforge schedule                     # start APScheduler daemon
flowforge run "Monthly Revenue Report" # run a pipeline by name
flowforge list                         # list all pipelines with schedule and status
flowforge validate "Pipeline Name"     # validate pipeline config
flowforge connections test             # test all configured DB connections
flowforge export "Pipeline Name"       # export pipeline as YAML
flowforge import pipeline.yaml         # import pipeline from YAML
flowforge cleanup [--days N]           # remove output files older than N days

# OAuth2 setup wizards
flowforge setup gmail
flowforge setup microsoft365
flowforge setup drive
```

---

## Variable System

Available in every config field rendered via Jinja2:

| Variable | Example |
|---|---|
| `{{ current_date }}` | `2026-05-20` |
| `{{ current_month }}` | `2026-05` |
| `{{ current_year }}` | `2026` |
| `{{ yesterday }}` | `2026-05-19` |
| `{{ week_start }}` | `2026-05-18` (Monday) |
| `{{ week_end }}` | `2026-05-24` (Sunday) |
| `{{ month_start }}` | `2026-05-01` |
| `{{ month_end }}` | `2026-05-31` |
| `{{ quarter_start }}` | `2026-04-01` |
| `{{ quarter_end }}` | `2026-06-30` |
| `{{ timestamp }}` | `20052026142304` (DDMMYYYYHHmmSS) |
| `{{ run_id }}` | UUID of current run |
| `{{ pipeline_name }}` | `Monthly Revenue Report` |
| `{{ env.MY_VAR }}` | Any environment variable |
| `{{ steps.name.output_path }}` | Output file path from a previous step |
| `{{ steps.name.drive_url }}` | Drive URL from a previous step |
| `{{ steps.name.rows_affected }}` | Row count from a previous step |
| `{{ my_var }}` / `{{ vars.my_var }}` | Pipeline-level variable |

---

## Project Structure

```
flowforge/
├── flowforge/               # Python package
│   ├── cli.py               # Click CLI
│   ├── engine/              # Pipeline runner, scheduler, variable context
│   ├── steps/               # Step type implementations
│   ├── connections/         # PostgreSQL + Oracle
│   ├── email_providers/     # Gmail, M365, SMTP
│   ├── reports/             # Excel, CSV, PDF
│   ├── storage/             # Google Drive
│   ├── crypto.py            # AES-256-GCM credential encryption
│   ├── db/                  # SQLAlchemy models + Alembic migrations
│   └── api/                 # Flask REST API
├── frontend/                # React + Vite + TypeScript
├── docs/                    # Guides: getting-started, step-types, email-providers
├── tests/
├── .github/workflows/       # GitHub Actions CI
├── server.ps1               # Windows dev/prod server script
├── server.sh                # macOS/Linux dev/prod server script
├── docker-compose.yml
├── Dockerfile
├── alembic.ini
├── .env.example
├── pyproject.toml
└── CHANGELOG.md
```

---

## Documentation

- [`docs/getting-started.md`](docs/getting-started.md) — end-to-end setup walkthrough
- [`docs/step-types.md`](docs/step-types.md) — full config reference for all step types
- [`docs/email-providers.md`](docs/email-providers.md) — SMTP, M365, and Gmail setup
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — dev setup, running tests, PR process
- [`CHANGELOG.md`](CHANGELOG.md) — version history

---

## Roadmap

- **v0.1.0** ✅ — Pipeline engine, all step types, all email providers, reports, Drive, scheduler, React frontend, Docker, CI, Alembic migrations, AES-256 encryption, JWT auth
- **v0.1.3** ✅ — Oracle Docker, `data_load` step, `python-oracledb` migration, JSON report format, scheduler sync, email provider fixes, UI screenshots
- **v0.1.4** ✅ — Email provider test(), Gmail scope fix, error messages in UI, quick-attach Jinja2 fix, docs served from API, pipeline builder button wrap
- **v2**: Multi-user auth, Slack/Teams notifications, S3/Azure Blob, `ai_analyze` step, OneDrive upload, `bulk_load` step

---

## License

MIT — see [LICENSE](LICENSE).
