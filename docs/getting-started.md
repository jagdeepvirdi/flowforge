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
pip install -e .[oracle]  # Oracle database support (python-oracledb — thin mode, no Oracle Instant Client needed)
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

# Celery worker (only needed when FLOWFORGE_REDIS_URL is set)
flowforge worker --concurrency 2

# Run a specific pipeline directly from the CLI
flowforge run "My Pipeline Name"
```

`flowforge worker` is only required when `FLOWFORGE_REDIS_URL` is configured for async task execution. For single-server deployments, the scheduler and API run pipelines directly without Celery.

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

## Setting Up Microsoft OneDrive

OneDrive upload uses the same Azure AD app registration as Microsoft 365 email. If you already configured M365, no additional registration is needed — just add the `Files.ReadWrite.All` application permission to your existing app.

1. In your Azure AD app registration, go to **API permissions → Add a permission → Microsoft Graph → Application permissions**
2. Search for and add: `Files.ReadWrite.All`
3. Click **Grant admin consent**

The same environment variables are used for both OneDrive and M365 email:

```env
MICROSOFT_TENANT_ID=...
MICROSOFT_CLIENT_ID=...
MICROSOFT_CLIENT_SECRET=...
MICROSOFT_SENDER_EMAIL=sender@yourcompany.com   # OneDrive owner
```

Add an `onedrive_upload` step to any pipeline, or configure `onedrive_folder_id` in the Email Designer to automatically route oversized attachments to OneDrive instead of Google Drive.

See [Step Types Reference → onedrive_upload](step-types.md#onedrive_upload) for the full config reference.

## AI Features (Optional)

FlowForge ships with six AI-powered features. By default these run through [Ollama](https://ollama.com) locally — no data leaves your machine and there is no API cost. The `ai_analyze` pipeline step also supports the **Claude API** as an alternative provider (set `USE_CLAUDE=true` and `ANTHROPIC_API_KEY` in `.env`).

| Feature | Where | What it does |
|---|---|---|
| AI Chart Generator | Report Preview panel | Suggests the best chart type and axes for your query result |
| SQL Explainer | SQL editor | Explains tables, joins, filters, and potential issues in plain English |
| SQL Optimizer | SQL editor | Rewrites queries for better performance; shows a side-by-side diff |
| Pipeline Failure Diagnosis | Run Detail → Logs tab | Explains a failed step error and suggests a fix |
| Data Profiler | Report Preview panel | Summarises value ranges, nulls, and outliers in your data sample |
| Run History Anomaly Alerts | Run Detail page | Flags steps whose row counts or durations are statistical outliers |

### Enabling AI

Install Ollama from [ollama.com](https://ollama.com), then pull a model:

```bash
ollama pull llama3.2:3b
```

AI is enabled by default. To disable all AI features (hides buttons in the UI):

```env
FLOWFORGE_AI_ENABLED=false
```

### Configuring models

```env
OLLAMA_URL=http://localhost:11434          # default
OLLAMA_CHART_MODEL=llama3.2:3b            # chart suggestions + data profiling
OLLAMA_QUERY_MODEL=llama3.2:3b            # SQL tasks + failure diagnosis
```

Use `mistral:7b` for better SQL quality if you have enough RAM. Use `phi3:mini` if RAM is constrained.

All AI calls are best-effort: if Ollama is unreachable the AI buttons show *"AI unavailable — is Ollama running?"* and the rest of the UI is unaffected.

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

## API / Webhook Triggers

Any pipeline can be triggered externally via an HTTP `POST` request. Generate a token in the Pipeline Builder (the **Webhook / API Trigger** card appears when editing an existing pipeline):

1. Open a pipeline → **Webhook / API Trigger** card → enter a label → click **Generate token**
2. Copy the full trigger URL shown — it is only displayed once:
   ```
   POST /api/pipelines/{pipeline-id}/trigger?token=<token>
   ```
3. Call it from any external system (GitHub Actions, cron job, monitoring alert, etc.):
   ```bash
   curl -X POST "https://your-flowforge/api/pipelines/abc123/trigger?token=flwf_xxx"
   ```

Tokens can be revoked individually without affecting the pipeline or other tokens. All webhook trigger events are recorded in the audit log.

---

## Variable Reference

All step config fields are rendered as Jinja2 templates. Key variables:

**Dates (YYYY-MM-DD)**

| Variable | Example |
|---|---|
| `{{ current_date }}` | `2026-05-23` |
| `{{ yesterday }}` | `2026-05-22` |
| `{{ week_start }}` / `{{ week_end }}` | `2026-05-18` / `2026-05-24` |
| `{{ month_start }}` / `{{ month_end }}` | `2026-05-01` / `2026-05-31` |
| `{{ prev_month_start }}` / `{{ prev_month_end }}` | `2026-04-01` / `2026-04-30` |
| `{{ quarter_start }}` / `{{ quarter_end }}` | `2026-04-01` / `2026-06-30` |
| `{{ current_month }}` | `2026-05` |
| `{{ current_year }}` | `2026` |
| `{{ mon_year }}` | `MAY-2026` |

**Timestamp boundaries (YYYYMMDDHHmmSS — for SQL `WHERE` clauses)**

| Variable | Example |
|---|---|
| `{{ day_start_ts }}` / `{{ day_end_ts }}` | `20260523000000` / `20260523235959` |
| `{{ yesterday_start_ts }}` / `{{ yesterday_end_ts }}` | `20260522000000` / `20260522235959` |
| `{{ month_start_ts }}` / `{{ month_end_ts }}` | `20260501000000` / `20260531235959` |
| `{{ prev_month_start_ts }}` / `{{ prev_month_end_ts }}` | `20260401000000` / `20260430235959` |
| `{{ now_ts }}` | `20260523143022` (YYYYMMDDHHmmSS — sortable, for filenames) |
| `{{ timestamp }}` | `23052026143022` (DDMMYYYYHHmmSS — human-readable, for filenames) |

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
| `{{ steps.my_step.drive_url }}` | Drive URL from a previous `drive_upload`, `onedrive_upload`, or `email` step |
| `{{ ai_summary }}` | LLM response from a previous `ai_analyze` step |
| `{{ steps.my_step.ai_summary }}` | Same, using the step namespace |

See [Step Types Reference](step-types.md#variable-reference) for the full variable list including `bulk_load` and `ai_analyze` output variables.

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
