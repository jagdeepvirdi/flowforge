# Getting Started with FlowForge

This guide walks you through installing FlowForge, connecting a database, and running your first pipeline.

## Prerequisites

- Python 3.11 or newer
- PostgreSQL 14+ (for FlowForge's config database)
- A terminal

## Installation

```bash
git clone https://github.com/your-org/flowforge.git
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

Create the FlowForge config database in PostgreSQL:

```bash
createdb flowforge
psql -U postgres -d flowforge -f flowforge/db/schema.sql
```

## Start FlowForge

```bash
# Web server (default port 5000)
flowforge web

# Or run a specific pipeline directly
flowforge run "My Pipeline Name"
```

Open `http://localhost:5000` in your browser.

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
2. Go to **Report Designer** — write a SQL query, pick a format (Excel/CSV/PDF), set an output filename like `report_{{ current_month }}.xlsx`
3. Go to **Email Designer** — configure recipients, subject, body; link to your email provider
4. Go to **Pipeline Builder** — create a pipeline, add a `report` step and an `email` step; set `on_error: stop` or `continue` per step
5. Click **Run Now**

Or import the example pipeline YAML:

```bash
# Coming in Phase 2
flowforge import pipelines/example_pipeline.yaml
```

## Variable Reference

| Variable | Example value |
|---|---|
| `{{ current_date }}` | `2026-05-17` |
| `{{ current_month }}` | `2026-05` |
| `{{ current_year }}` | `2026` |
| `{{ yesterday }}` | `2026-05-16` |
| `{{ run_id }}` | UUID |
| `{{ pipeline_name }}` | `Monthly Revenue Report` |
| `{{ env.MY_VAR }}` | Any environment variable |
| `{{ steps.my_step.output_path }}` | File path from a previous step |
| `{{ steps.my_step.drive_url }}` | Drive URL from a previous step |

## Smart Attachments

If a report file exceeds `attachment_max_mb` (default: 10 MB), FlowForge automatically:

1. Uploads the file to Google Drive
2. Creates a shareable link
3. Replaces the direct attachment with a link in the email body

Configure the threshold and Drive folder in the Email Designer under **Smart Attachment Settings**.

## Running Tests

```bash
pip install -e .[dev]
pytest
```

## Next Steps

- [Step Types Reference](step-types.md)
- [Email Providers](email-providers.md)
- [Database Connections](connections.md)
