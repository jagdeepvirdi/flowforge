# Getting Started with FlowForge

This guide walks you through installing FlowForge, connecting a database, and running your first pipeline.

## Prerequisites

- Python 3.11 or newer
- PostgreSQL 14+ (for FlowForge's config database)
- A terminal

## Installation

```bash
git clone https://github.com/jagdeepvirdi/flowforge.git
cd flowforge
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

**Optional extras:**

```bash
pip install -e .[pdf]     # PDF report generation (WeasyPrint)
pip install -e .[oracle]  # Oracle database support (cx_Oracle)
pip install -e .[dev]     # Development tools (pytest, ruff)
```

## Configuration

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

Minimum required variables:

```env
FLOWFORGE_DB_URL=postgresql://flowforge:changeme@localhost:5432/flowforge
FLOWFORGE_SECRET_KEY=<generate below>
```

Generate a secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Database Setup

Create the FlowForge config database in PostgreSQL, then apply migrations and seed the admin user:

```bash
createdb flowforge
flowforge db upgrade
flowforge db seed
```

`flowforge db seed` reads `FLOWFORGE_USERNAME` and `FLOWFORGE_PASSWORD` from your `.env` and creates the admin account. It is safe to run more than once — it skips if a user already exists.

> **Upgrading from an older version?** If your database was created before Alembic was introduced, run `flowforge db stamp head` once instead of `flowforge db upgrade`. See [RUNBOOK.md](../RUNBOOK.md#32-existing-database) for details.

## Start FlowForge

The easiest way to start everything is with the startup script — it launches the API, scheduler, and frontend dev server together:

```powershell
# Windows
.\flowforge.ps1 start
```

```bash
# macOS / Linux
./flowforge.sh start
```

Open `http://localhost:5000` in your browser. The scheduler starts automatically alongside the API, so any pipelines with a cron schedule will fire without any additional setup.

To stop all three processes: press **Ctrl+C** in the same terminal, or run `.\flowforge.ps1 stop` / `./flowforge.sh stop` from another terminal.

**Running components individually (advanced):**

```bash
# Web server only
flowforge web

# Scheduler only (in a separate terminal)
flowforge schedule

# Run a specific pipeline directly from the CLI
flowforge run "My Pipeline Name"
```

## Setting Up Email

### Gmail

```bash
flowforge setup gmail
```

Follow the OAuth2 consent flow. The refresh token is saved to your `.env` automatically.

### Microsoft 365

1. Register an app in [Azure Active Directory](https://portal.azure.com)
2. Grant `Mail.Send` permission (application, not delegated)
3. Add `MICROSOFT_TENANT_ID`, `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`, and `MICROSOFT_SENDER_EMAIL` to `.env`

```bash
flowforge setup microsoft365
```

### SMTP

Configure directly in the Email Designer UI — host, port, username, password, TLS/SSL settings.

## Setting Up Google Drive

Shares OAuth2 credentials with Gmail if you're using the same Google account. Run:

```bash
flowforge setup gmail
```

Then set `GOOGLE_DRIVE_FOLDER_ID` to the ID of the folder where files should be uploaded by default.

**Service account alternative:**

```bash
# Save your service account JSON as service_account.json (gitignored)
export GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json
```

## Your First Pipeline

In the web UI:

1. Go to **Connections** — add your database connection and test it
2. Go to **Report Designer** — write a SQL query, pick a format (Excel, CSV, PDF, or JSON), set an output filename like `report_{{ current_month }}.xlsx`. The file extension updates automatically when you change the format.
3. Go to **Email Designer** — configure recipients, subject, body; link to your email provider
4. Go to **Pipeline Builder** — create a pipeline, add a `report` step and an `email` step; set `on_error: stop` or `continue` per step
5. Click **Run Now**

Or import a pipeline YAML exported from another instance:

```bash
flowforge import pipelines/example_pipeline.yaml
```

## Variable Reference

All step config fields are rendered as Jinja2 templates. Key variables:

**Dates (YYYY-MM-DD)**

| Variable | Example |
|---|---|
| `{{ current_date }}` | `2026-05-23` |
| `{{ yesterday }}` | `2026-05-22` |
| `{{ month_start }}` / `{{ month_end }}` | `2026-05-01` / `2026-05-31` |
| `{{ prev_month_start }}` / `{{ prev_month_end }}` | `2026-04-01` / `2026-04-30` |
| `{{ quarter_start }}` / `{{ quarter_end }}` | `2026-04-01` / `2026-06-30` |
| `{{ current_month }}` | `2026-05` |
| `{{ current_year }}` | `2026` |

**Timestamp boundaries (YYYYMMDDHHmmSS — for SQL `WHERE` clauses)**

| Variable | Example |
|---|---|
| `{{ day_start_ts }}` / `{{ day_end_ts }}` | `20260523000000` / `20260523235959` |
| `{{ yesterday_start_ts }}` / `{{ yesterday_end_ts }}` | `20260522000000` / `20260522235959` |
| `{{ month_start_ts }}` / `{{ month_end_ts }}` | `20260501000000` / `20260531235959` |
| `{{ prev_month_start_ts }}` / `{{ prev_month_end_ts }}` | `20260401000000` / `20260430235959` |

**Delta**

| Variable | Notes |
|---|---|
| `{{ last_success_at }}` | `YYYYMMDDHHmmSS` of the last successful run; empty on first run |
| `{{ last_success_date }}` | Same in `YYYY-MM-DD` format |

**Run metadata & pipeline variables**

| Variable | Notes |
|---|---|
| `{{ run_id }}` | UUID of the current run |
| `{{ pipeline_name }}` | Name of the running pipeline |
| `{{ env.MY_VAR }}` | Any OS environment variable |
| `{{ my_var }}` / `{{ vars.my_var }}` | Pipeline variable (set in Pipeline Builder → Variables card) |
| `{{ steps.my_step.output_path }}` | File path from a previous `report` step |
| `{{ steps.my_step.drive_url }}` | Drive URL from a previous `drive_upload` or `email` step |

See [Step Types Reference](step-types.md#variable-reference) for the full variable list including `bulk_load` output variables.

## Smart Attachments

If a report file exceeds `attachment_max_mb` (default: 10 MB), FlowForge automatically:

1. Uploads the file to Google Drive
2. Creates a shareable link
3. Replaces the direct attachment with a link in the email body

Configure the threshold and Drive folder in the Email Designer under **Smart Attachment Settings**.

## Scheduler Diagnostics

If a scheduled pipeline isn't firing, run the built-in diagnostic script from the project root:

```bash
python scripts/check_scheduler.py
```

This script tests each layer independently — env vars, database connectivity, pipeline discovery, worker-thread app context, a live direct job fire, run history, and APScheduler job registration — and prints a clear PASS/FAIL at each step.

## Running Tests

```bash
pip install -e .[dev]
pytest
```

## Next Steps

- [Step Types Reference](step-types.md)
- [Email Providers](email-providers.md)
- [Database Connections](connections.md)
