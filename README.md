# FlowForge

**Database-driven pipeline orchestrator. Configure everything from the UI — DB procedures, reports, email (Gmail/M365/SMTP), Google Drive, smart attachments, scheduling. No YAML. No Airflow complexity.**

---

## What is FlowForge?

FlowForge runs ordered data pipelines: call database procedures, run queries, generate reports (Excel/PDF/CSV), send emails with smart attachment handling, and upload files to Google Drive. Everything is configured through a web frontend — no config files to edit.

Designed for solo developers, data analysts, and small teams who need lightweight automation without the overhead of enterprise orchestration tools.

---

## Features

- **No-YAML config** — pipelines, reports, email templates, and schedules are all managed via UI
- **Step types**: `db_procedure`, `db_query`, `report`, `email`, `drive_upload`
- **Database support**: PostgreSQL and Oracle (pluggable `BaseConnection` interface)
- **Email providers**: Gmail (OAuth2), Microsoft 365 (MSAL + Graph API), SMTP (any server)
- **Smart attachments**: files over a configurable size threshold are automatically uploaded to Google Drive; the email body gets a shareable link instead
- **Report formats**: Excel (openpyxl, optional template), CSV, PDF (WeasyPrint)
- **Google Drive**: upload, download, folder management; service account or OAuth2
- **Jinja2 variable system**: `{{ current_date }}`, `{{ run_id }}`, `{{ steps.prev.output_path }}`, `{{ env.MY_VAR }}`, and more
- **Scheduling**: APScheduler with cron expressions, managed from the UI
- **Run history**: step-level logs, timing, Drive links, and email recipients per run

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
| `db_query` | Run a SQL query and write results to a table |
| `report` | Generate Excel / CSV / PDF from a SQL query |
| `email` | Send email with smart attachment handling |
| `drive_upload` | Upload a file to Google Drive |
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

### 1. Prerequisites

- Python 3.11+
- PostgreSQL (for FlowForge's own config database)

### 2. Install

```bash
pip install -e .
# With PDF support:
pip install -e .[pdf]
# With Oracle support:
pip install -e .[oracle]
```

### 3. Configure

```bash
cp .env.example .env
# Edit .env — set FLOWFORGE_DB_URL and FLOWFORGE_SECRET_KEY at minimum
```

### 4. Initialize the database

```bash
# Coming in Phase 2 — for now, apply schema.sql manually:
psql -U flowforge -d flowforge -f flowforge/db/schema.sql
```

### 5. Run

```bash
# Start the web server
flowforge web

# Run a pipeline from the CLI
flowforge run "Monthly Revenue Report"

# Start the scheduler
flowforge schedule

# Set up Gmail / Google Drive OAuth2
flowforge setup gmail

# Set up Microsoft 365
flowforge setup microsoft365
```

---

## Variable System

Available in all config strings rendered via Jinja2:

| Variable | Example |
|---|---|
| `{{ current_date }}` | `2026-05-17` |
| `{{ current_month }}` | `2026-05` |
| `{{ current_year }}` | `2026` |
| `{{ yesterday }}` | `2026-05-16` |
| `{{ run_id }}` | UUID of current run |
| `{{ pipeline_name }}` | `Monthly Revenue Report` |
| `{{ env.MY_VAR }}` | Any environment variable |
| `{{ steps.name.output_path }}` | Output file path from a previous step |
| `{{ steps.name.drive_url }}` | Drive URL from a previous step |

---

## Example Pipeline (YAML import)

See [`pipelines/example_pipeline.yaml`](pipelines/example_pipeline.yaml) for a complete example.

---

## Project Structure

```
flowforge/
├── flowforge/          # Python package
│   ├── cli.py          # Click CLI
│   ├── engine/         # Pipeline runner + context + scheduler
│   ├── steps/          # Step type implementations
│   ├── connections/    # PostgreSQL + Oracle
│   ├── email_providers/# Gmail, M365, SMTP
│   ├── reports/        # Excel, CSV, PDF
│   ├── storage/        # Google Drive
│   ├── crypto.py       # AES-256 credential encryption
│   ├── db/             # SQLAlchemy models + migrations
│   └── api/            # Flask REST API
├── frontend/           # React + Vite + TypeScript
├── docs/
├── pipelines/          # Example YAML configs
├── tests/
├── .env.example
├── pyproject.toml
└── requirements.txt
```

---

## Roadmap

- **v0.2**: Flask REST API, SQLAlchemy models, full CLI, APScheduler integration
- **v0.3**: React frontend — Dashboard, Pipeline Builder, Report Designer, Email Designer
- **v0.4**: Credential encryption (AES-256), authentication
- **v1.0**: Stable API, full documentation, Docker image
- **v2**: Multi-user auth, Slack/Teams notifications, S3/Azure Blob, ai_analyze step

---

## License

MIT — see [LICENSE](LICENSE).
