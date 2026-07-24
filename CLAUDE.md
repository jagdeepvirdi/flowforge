# CLAUDE.md — FlowForge

## Project Overview
FlowForge is a lightweight, database-driven data pipeline orchestrator. Users configure pipelines, reports, email templates, and schedules entirely through a web frontend — no YAML editing required. Pipelines execute ordered steps: calling database stored procedures/packages, running SQL queries, generating reports (Excel/PDF/CSV), sending emails (Gmail, Microsoft 365, SMTP), and uploading files to Google Drive. Smart attachment handling: if a report exceeds a configured size threshold, it is automatically uploaded to Drive and a shareable link is sent in the email instead.

**Key principle**: All configuration lives in the database. The frontend is the primary interface for creating and managing everything.

**Origin**: Evolved from an internal reporting automation tool (Perl/Python, Oracle/PostgreSQL). Fully scrubbed, generalized, and open-sourced after code review and refactor.

**GitHub tagline**: "Database-driven pipeline orchestrator. Configure everything from the UI — DB procedures, reports, email (Gmail/M365/SMTP), Google Drive, smart attachments, scheduling. No YAML. No Airflow complexity."

**Target users**: Solo developers, small teams, data analysts who need lightweight pipeline orchestration without enterprise tool complexity.

---

## CRITICAL: Code Review Before Anything

Before any code is written or changed, Claude Code must:
1. Read all existing code in the project directory
2. Produce a full structured review (see Session Zero prompt in docs/TASKS.md)
3. Save review to `docs/code-review.md`
4. Only then proceed with scrub and refactor

The existing code has working implementations of: email sending (Gmail), Google Drive upload, report generation, and database queries. These must be understood before being refactored — not rewritten blindly.

---

## Tech Stack

### Backend
- **Language**: Python 3.11+
- **Web Framework**: Flask + Flask-SQLAlchemy
- **API**: Flask REST API (JSON) — consumed by frontend
- **Database (FlowForge config)**: PostgreSQL — stores all pipeline/report/email config + run history
- **Database (User data)**: PostgreSQL + Oracle (equal support, pluggable)
- **ORM**: SQLAlchemy (FlowForge internal tables only)
- **Scheduler**: APScheduler with PostgreSQL job store
- **Async execution (optional)**: Celery + Redis — `flowforge worker` runs pipeline execution on a
  Celery worker instead of the default in-process threading, when `FLOWFORGE_REDIS_URL` is set;
  Flower available for worker monitoring. See `flowforge/celery_app.py`, `flowforge/tasks.py`,
  `docker-compose.yml`. Purely additive — a deployment with no Redis configured is unaffected.
- **Templating**: Jinja2 (email bodies, report titles, variable resolution)

### Email Providers
- **Gmail**: OAuth2 via `google-auth` + `google-auth-oauthlib`
- **Microsoft 365**: OAuth2 via `msal` (Microsoft Authentication Library)
- **Generic SMTP**: `smtplib` stdlib — any SMTP server (fallback, covers Outlook, Yahoo, custom)

### Report Generation
- **Excel**: `openpyxl` + `xlsxwriter`
- **PDF**: `weasyprint` (HTML template → PDF, optional dependency)
- **CSV**: Python stdlib `csv`

### Google Drive
- `google-api-python-client` — upload files, create shareable links
- Smart attachment: if file > `EMAIL_ATTACHMENT_MAX_MB` (default 10MB) → upload to Drive → share link in email

### Frontend
- **Framework**: React + Vite + TypeScript
- **Styling**: Tailwind CSS + design tokens (see Design System section)
- **State**: React Query (server state) + Zustand (UI state)
- **Forms**: React Hook Form + Zod validation
- **Code editor**: CodeMirror 6 (SQL editor in report designer, Jinja2 in email designer)
- **Charts**: Recharts (run history dashboard)

### CLI
- `Click` — `flowforge run`, `flowforge schedule`, `flowforge web`, `flowforge setup`

### Tests
- `pytest` + `pytest-mock` + `responses` (mock HTTP)

---

## Architecture: Database-Driven Config

All FlowForge configuration is stored in PostgreSQL. The frontend reads and writes via REST API. There are no YAML files required for normal operation (YAML import/export is available for power users).

### FlowForge Internal Database Schema

```sql
-- Email provider configurations
CREATE TABLE email_providers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL,           -- "Company Gmail", "Team M365"
    provider_type   VARCHAR(20) NOT NULL,            -- 'gmail' | 'microsoft365' | 'smtp'
    config          JSONB NOT NULL,                  -- provider-specific settings (encrypted)
    is_default      BOOLEAN DEFAULT false,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- Database connection configurations
CREATE TABLE db_connections (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL,           -- "Production DB", "Oracle Billing"
    db_type         VARCHAR(20) NOT NULL,            -- 'postgresql' | 'oracle' | 'mysql'
    config          JSONB NOT NULL,                  -- host, port, db, user, password (encrypted)
    is_default      BOOLEAN DEFAULT false,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- Pipeline definitions
CREATE TABLE pipelines (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    schedule        VARCHAR(100),                    -- cron expression or NULL
    enabled         BOOLEAN DEFAULT true,
    timeout_minutes INTEGER DEFAULT 60,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- Ordered steps within a pipeline
CREATE TABLE pipeline_steps (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id     UUID REFERENCES pipelines(id) ON DELETE CASCADE,
    step_order      INTEGER NOT NULL,
    name            VARCHAR(255) NOT NULL,
    step_type       VARCHAR(50) NOT NULL,            -- see Step Types below
    config          JSONB NOT NULL,                  -- step-specific config
    on_error        VARCHAR(20) DEFAULT 'stop',      -- 'stop' | 'continue'
    enabled         BOOLEAN DEFAULT true
);

-- Report configurations (referenced by report steps)
CREATE TABLE report_configs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    connection_id   UUID REFERENCES db_connections(id),
    query           TEXT NOT NULL,                   -- SQL query
    format          VARCHAR(20) NOT NULL,            -- 'excel' | 'pdf' | 'csv'
    template_path   VARCHAR(500),                    -- optional Excel template file path
    output_filename VARCHAR(500) NOT NULL,           -- supports Jinja2 vars: report_{{ current_month }}.xlsx
    title           VARCHAR(255),
    sheet_name      VARCHAR(100),                    -- Excel only
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- Email configurations (referenced by email steps)
CREATE TABLE email_configs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    provider_id     UUID REFERENCES email_providers(id),
    from_name       VARCHAR(255),                    -- display name
    subject         VARCHAR(500) NOT NULL,           -- supports Jinja2 vars
    header_text     VARCHAR(500),                    -- email header/banner text
    body_template   TEXT NOT NULL,                   -- HTML Jinja2 template
    recipient_group_id UUID REFERENCES recipient_groups(id),
    to_addresses    TEXT[],                          -- direct addresses OR use group
    cc_addresses    TEXT[],
    bcc_addresses   TEXT[],
    -- Smart attachment config
    attachment_max_mb   INTEGER DEFAULT 10,          -- threshold for Drive upload
    drive_folder_id     VARCHAR(255),               -- Drive folder for large attachments
    drive_share_message TEXT,                        -- message when link sent instead
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- Recipient groups (reusable across email configs)
-- `addresses` is the group's To list from the original design; `cc_addresses`/`bcc_addresses`
-- have since shipped so a group can also supply CC/BCC — see docs/step-types.md's `email` step.
CREATE TABLE recipient_groups (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL,           -- "Finance Team", "Management"
    description     TEXT,
    addresses       TEXT[] NOT NULL,                 -- To
    cc_addresses    TEXT[],
    bcc_addresses   TEXT[],
    created_at      TIMESTAMP DEFAULT NOW()
);

-- Pipeline run history
CREATE TABLE pipeline_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id     UUID REFERENCES pipelines(id),
    pipeline_name   VARCHAR(255) NOT NULL,           -- denormalized for history
    status          VARCHAR(20) NOT NULL,            -- 'running'|'success'|'failed'|'cancelled'
    started_at      TIMESTAMP NOT NULL,
    finished_at     TIMESTAMP,
    duration_ms     INTEGER,
    triggered_by    VARCHAR(50),                     -- 'scheduler'|'cli'|'web_ui'|'api'
    error_step      VARCHAR(255),
    error_message   TEXT
);

-- Step-level run details
CREATE TABLE step_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_run_id UUID REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    step_name       VARCHAR(255) NOT NULL,
    step_type       VARCHAR(50) NOT NULL,
    step_order      INTEGER NOT NULL,
    status          VARCHAR(20) NOT NULL,
    started_at      TIMESTAMP NOT NULL,
    finished_at     TIMESTAMP,
    duration_ms     INTEGER,
    rows_affected   INTEGER,
    output_path     VARCHAR(500),                    -- generated file path
    drive_url       VARCHAR(500),                    -- Drive link if uploaded
    email_sent_to   TEXT[],                          -- recipients if email step
    logs            TEXT,
    error_message   TEXT
);

-- Pipeline variables (custom vars set at pipeline level)
CREATE TABLE pipeline_variables (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id     UUID REFERENCES pipelines(id) ON DELETE CASCADE,
    var_key         VARCHAR(100) NOT NULL,
    var_value       TEXT NOT NULL,
    is_secret       BOOLEAN DEFAULT false            -- masked in UI if true
);

-- Audit log (append-only security/compliance record)
CREATE TABLE ff_audit_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),  -- indexed
    action          VARCHAR(50) NOT NULL,             -- e.g. LOGIN_SUCCESS, PIPELINE_RUN, CONNECTION_CREATED
    username        VARCHAR(255) NOT NULL,            -- actor (indexed)
    user_id         UUID,                            -- nullable for system/legacy events (indexed)
    ip_address      VARCHAR(45),                     -- IPv6 max len
    details         JSONB NOT NULL DEFAULT '{}'      -- e.g. pipeline_name, run_id, etc.
);
-- Indexes: timestamp, action, username (all indexed for fast filtering)
```

---

## Step Types

> The six types below are the original core set from this doc's initial design. Many more have
> shipped since — `bulk_load`, `sftp_transfer`, `onedrive_upload`, `s3_upload`, `azure_blob_upload`,
> `ssh_command`, `ssh_health_check`, `db_health_check`, `data_report`, `notification` (Slack/Teams/
> Telegram), and a plugin system for community-defined types. See [`docs/step-types.md`](docs/step-types.md)
> for the complete, current reference and [`README.md`](README.md) for the up-to-date summary table.

### db_procedure
Call a stored procedure or package in any configured database.
```json
{
  "connection_id": "uuid",
  "procedure": "pkg_revenue.populate_monthly_summary",
  "params": {
    "period": "{{ current_month }}",
    "run_id": "{{ run_id }}"
  }
}
```
Supports: PostgreSQL procedures (created via `CREATE PROCEDURE`, invoked with `CALL` — a `CREATE FUNCTION` will fail with "is not a procedure"), Oracle packages (`package.procedure` syntax).

### db_query
Run a SQL query and write results to a table.
```json
{
  "connection_id": "uuid",
  "query": "SELECT ...",
  "output_table": "staging.customer_extract",
  "mode": "replace"
}
```
Modes: `replace` (truncate + insert), `append`, `truncate_insert`.

### report
Generate a report file from a configured report_config.
```json
{
  "report_config_id": "uuid"
}
```
Report config (stored in `report_configs` table) contains: connection, query, format, template, output filename.

### email
Send an email using a configured email_config.
```json
{
  "email_config_id": "uuid",
  "attachments": ["{{ steps.generate_report.output_path }}"]
}
```
Smart attachment logic runs automatically based on `attachment_max_mb` in the email config.

### drive_upload
Upload a file to Google Drive.
```json
{
  "file_path": "{{ steps.generate_report.output_path }}",
  "folder_id": "{{ env.DRIVE_FOLDER_ID }}",
  "rename_to": "Report_{{ current_month }}.xlsx"
}
```

### ai_analyze
```json
{
  "connection_id": "uuid",
  "query": "SELECT ...",
  "prompt": "Summarize the top trends in this data in 3 sentences.",
  "output_variable": "ai_summary",
  "provider": "ollama"
}
```
`provider` also accepts `"claude"` (Anthropic API) or `"gemini"` (Google Gemini API — has a free tier).

---

## Email Provider Implementations

> Three providers shown below from the original design. SendGrid, AWS SES, and Mailgun have
> since shipped as additional providers behind the same `EmailProvider` interface — see
> `flowforge/email_providers/` and [`docs/email-providers.md`](docs/email-providers.md).

### Abstract Base
```python
class EmailProvider(ABC):
    @abstractmethod
    def send(self, to: list[str], cc: list[str], bcc: list[str],
             subject: str, html_body: str,
             attachments: list[Path]) -> EmailResult:
        pass
```

### Gmail (OAuth2)
```python
class GmailProvider(EmailProvider):
    # Uses google-auth + gmail API
    # OAuth2 tokens stored encrypted in email_providers.config
    # flowforge setup gmail → OAuth2 consent flow → saves refresh token
```

### Microsoft 365 (OAuth2 via MSAL)
```python
class Microsoft365Provider(EmailProvider):
    # Uses msal library
    # App registration in Azure AD required
    # Client credentials flow (app-to-app) OR delegated (user login)
    # flowforge setup microsoft365 → MSAL device code flow
    # Sends via Microsoft Graph API: POST /v1.0/users/{userId}/sendMail
```

### SMTP (Generic)
```python
class SMTPProvider(EmailProvider):
    # Uses smtplib
    # Covers: custom SMTP, Outlook (smtp.office365.com:587),
    #         Yahoo, any corporate mail server
    # Config: host, port, username, password, use_tls, use_ssl
```

---

## Smart Attachment Logic

```python
def handle_attachments(
    attachments: list[Path],
    email_config: EmailConfig,
    context: PipelineContext
) -> tuple[list[Path], str]:
    """
    Returns: (files_to_attach, extra_body_text)
    Large files are uploaded to Drive; link added to body.
    """
    max_bytes = email_config.attachment_max_mb * 1024 * 1024
    direct_attachments = []
    drive_links = []

    for file_path in attachments:
        if file_path.stat().st_size > max_bytes:
            # Upload to Drive
            drive_url = google_drive.upload(
                file_path,
                folder_id=email_config.drive_folder_id,
                make_shareable=True
            )
            drive_links.append({
                "filename": file_path.name,
                "url": drive_url,
                "size_mb": round(file_path.stat().st_size / 1024 / 1024, 1)
            })
        else:
            direct_attachments.append(file_path)

    extra_text = ""
    if drive_links:
        extra_text = render_template(
            email_config.drive_share_message or DEFAULT_DRIVE_MESSAGE,
            {"drive_links": drive_links}
        )

    return direct_attachments, extra_text
```

Default drive share message template (stored in DB, editable in UI):
```
The following report(s) were too large to attach directly and have been
uploaded to Google Drive for your convenience:

{% for link in drive_links %}
• {{ link.filename }} ({{ link.size_mb }}MB) — {{ link.url }}
{% endfor %}
```

---

## Database Connection Support

> PostgreSQL and Oracle shown below from the original design. MySQL/MariaDB, MSSQL, generic ODBC,
> Snowflake, BigQuery, and Redshift have since shipped as additional connections behind the same
> `BaseConnection` interface — see `flowforge/connections/`.

### PostgreSQL
```python
class PostgreSQLConnection(BaseConnection):
    # psycopg2-binary with ThreadedConnectionPool
    # Supports: procedures (CALL), queries, bulk operations
```

### Oracle
```python
class OracleConnection(BaseConnection):
    # cx_Oracle (requires Oracle Instant Client)
    # Supports: packages (pkg.proc syntax), procedures, queries
    # Handles Oracle-specific types: LOB, DATE, TIMESTAMP, NUMBER
    # Bulk fetch via arraysize for performance
```

Both implement the same `BaseConnection` interface — pipelines don't know which DB they're talking to.

---

## Frontend Pages

> Pages below are the original design set. `Login` (with MFA/SSO/password-reset flows), `Users`
> (admin user management), `Bulk Loads`, and `Projects` (multi-project workspace switcher) have
> since shipped as additional pages under `frontend/src/pages/`.

### Dashboard
- Pipeline cards: name, status badge (Success/Failed/Running/Never Run), last run time, next scheduled run, Run Now button
- Live status updates via polling (every 5s when a pipeline is running)
- Global stats: runs today, success rate, active schedules

### Pipeline Builder
- Create/edit pipeline: name, description, schedule picker (visual cron builder)
- Step list — drag to reorder, add/remove steps
- Per step: type selector → type-specific config form
  - db_procedure: connection picker + procedure name + params editor
  - report: report config picker (or create inline)
  - email: email config picker (or create inline)
  - drive_upload: folder picker
- on_failure steps (separate collapsible section)
- Save + Validate button — tests connections, validates SQL

### Report Designer
- Name, description
- Connection picker
- SQL editor (CodeMirror 6 with SQL syntax highlighting)
- Format selector: Excel / PDF / CSV
- Excel: template upload, sheet name
- Output filename (with variable hints: `report_{{ current_month }}.xlsx`)
- Preview: run query → show first 20 rows in table

### Email Designer
- Name, description
- Provider picker (Gmail / M365 / SMTP)
- From name
- Recipients: select recipient group OR enter addresses directly
- CC, BCC fields
- Subject (with variable hints)
- Header/banner text (shown at top of email)
- Body editor: rich HTML editor OR raw HTML with Jinja2 support
- Smart attachment settings:
  - Max attachment size (MB slider)
  - Drive folder picker (if exceeded)
  - Drive share message template editor
- Preview: render email with sample variables → show in modal

### Recipient Groups
- Create/edit named groups: "Finance Team", "Management", "All Staff"
- Add/remove email addresses
- Referenced by email configs

### Connections Manager
- List all DB connections and email providers
- Add new: type selector → type-specific form
- Test connection button → shows success/latency or error
- Edit, delete (with warning if used by pipeline steps)
- Credentials stored encrypted (AES-256) in JSONB config column

### Schedule Manager
- Visual cron builder (plain English + cron expression)
- Enable/disable schedules without deleting pipelines
- Next 5 run times preview

### Run History
- Table: pipeline, triggered by, started, duration, status, view logs button
- Run Detail: step-by-step timeline, expandable logs per step, Drive links, email recipients

### Settings
- FlowForge system config (attachment threshold default, Drive folder default)
- Google OAuth setup (Gmail + Drive)
- Microsoft 365 setup (MSAL)
- AI / Ollama / Claude / Gemini configuration status (dedicated AI tab)
- Data retention (run history, audit log, output file TTL) — view/edit (admin), DB-backed override
  of `FLOWFORGE_RUN_RETENTION_DAYS` / `FLOWFORGE_AUDIT_RETENTION_DAYS` / `FLOWFORGE_OUTPUT_TTL_DAYS`
- Export all pipeline configs as YAML
- Import pipeline configs from YAML

### Audit Log (`/settings/audit`)
- Admin-only page showing the `ff_audit_log` DB table
- Filters: action type, username
- Paginated table (50 per page, up to 100)
- Export to CSV download
- Events: login/logout, pipeline runs, config creates/updates/deletes, email sends, webhook triggers, report exports

---

## Variable System
Available in all config values rendered via Jinja2:

| Variable | Example Value |
|---|---|
| `{{ current_month }}` | 2026-05 |
| `{{ current_date }}` | 2026-05-16 |
| `{{ current_year }}` | 2026 |
| `{{ yesterday }}` | 2026-05-15 |
| `{{ mon_year }}` | AUG-2026 |
| `{{ now_ts }}` | 20260824223155 |
| `{{ run_id }}` | UUID of current run |
| `{{ pipeline_name }}` | Monthly Revenue Report |
| `{{ failed_step }}` | Generate Excel Report |
| `{{ env.VAR_NAME }}` | Any env variable |
| `{{ steps.step_name.output_path }}` | File path from previous step |
| `{{ steps.step_name.drive_url }}` | Drive URL from previous step |
| `{{ ai_summary }}` | Output from ai_analyze step |

---

## Security

### Credential Encryption
- All sensitive config in `db_connections.config` and `email_providers.config` stored encrypted
- AES-256-GCM encryption using `cryptography` library
- Encryption key from `FLOWFORGE_SECRET_KEY` env var (never stored in DB)
- `is_secret` pipeline variables masked in UI

### Authentication
- Multi-user, role-based (`admin`/`editor`/`viewer`), username + password bcrypt-hashed
- JWT session tokens; MFA (TOTP), SSO (Google/Microsoft/SAML) also supported — see `docs/TASKS.md` Phase 8

---

## Environment Variables (.env.example)
```env
# FlowForge system
FLOWFORGE_DB_URL=postgresql://flowforge:flowforge@localhost:5432/flowforge
FLOWFORGE_SECRET_KEY=<generate: python -c "import secrets; print(secrets.token_hex(32))">
FLOWFORGE_PORT=5000
FLOWFORGE_ATTACHMENT_MAX_MB=10

# Auth (single user v1)
FLOWFORGE_USERNAME=admin
FLOWFORGE_PASSWORD=<bcrypt hash>

# Gmail OAuth2 (set via: flowforge setup gmail)
GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=
GMAIL_REFRESH_TOKEN=
GMAIL_SENDER=

# Microsoft 365 OAuth2 (set via: flowforge setup microsoft365)
MICROSOFT_TENANT_ID=
MICROSOFT_CLIENT_ID=
MICROSOFT_CLIENT_SECRET=
MICROSOFT_SENDER_EMAIL=

# Google Drive OAuth2 (shares credentials with Gmail if same account)
GOOGLE_DRIVE_FOLDER_ID=

# AI (optional, for ai_analyze step)
OLLAMA_URL=http://localhost:11434
OLLAMA_QUERY_MODEL=llama3.2:3b    # model for explain/optimize/diagnose
OLLAMA_CHART_MODEL=llama3.2:3b    # model for chart & profile tasks
ANTHROPIC_API_KEY=                # ai_analyze step: provider: "claude"
GEMINI_API_KEY=                   # ai_analyze step: provider: "gemini" (has a free tier)
GEMINI_QUERY_MODEL=gemini-2.5-flash

# Data retention (scheduler prunes daily) — all three below can also be overridden at runtime
# via Settings → System (admin-only), which takes priority over these env vars when set
FLOWFORGE_RUN_RETENTION_DAYS=90       # delete pipeline_runs + step_runs older than N days (0 = keep forever)
FLOWFORGE_AUDIT_RETENTION_DAYS=90     # delete audit log entries older than N days (defaults to RUN_RETENTION_DAYS)
FLOWFORGE_OUTPUT_TTL_DAYS=7           # delete generated report files older than N days (min 1 — see docs/RUNBOOK.md §8a)
FLOWFORGE_OUTPUT_DIR=output           # directory generated reports are written to

# Audit log output (flowforge/audit.py)
FLOWFORGE_LOG_DIR=logs                # directory for audit.log rotating file
FLOWFORGE_AUDIT_STDOUT=false          # emit JSON lines to stdout (for container log aggregators)
FLOWFORGE_AUDIT_FILE=true             # write to logs/audit.log (disable for stdout-only)
```

---

## Project Structure
```
flowforge/
├── flowforge/                      # Python package
│   ├── __init__.py
│   ├── cli.py                      # Click CLI
│   ├── engine/
│   │   ├── runner.py               # Pipeline executor
│   │   ├── scheduler.py            # APScheduler
│   │   └── context.py              # Jinja2 variable resolution
│   ├── steps/
│   │   ├── base.py                 # BaseStep + StepResult
│   │   ├── db_procedure.py
│   │   ├── db_query.py
│   │   ├── report.py
│   │   ├── email_step.py           # Smart attachment logic here
│   │   ├── drive_upload.py
│   │   └── ai_analyze.py           # v2
│   ├── connections/
│   │   ├── base.py
│   │   ├── postgres.py
│   │   └── oracle.py
│   ├── email_providers/
│   │   ├── base.py                 # EmailProvider ABC
│   │   ├── gmail.py
│   │   ├── microsoft365.py         # MSAL + Graph API
│   │   └── smtp.py
│   ├── reports/
│   │   ├── excel_report.py
│   │   ├── pdf_report.py
│   │   └── csv_report.py
│   ├── storage/
│   │   └── google_drive.py
│   ├── crypto.py                   # AES-256 encrypt/decrypt for credentials
│   ├── db/
│   │   ├── models.py               # SQLAlchemy models
│   │   ├── schema.sql
│   │   └── migrations/
│   └── api/                        # Flask REST API
│       ├── app.py
│       ├── auth.py
│       └── routes/
│           ├── audit.py            # GET /audit-logs, GET /audit-logs/export (admin)
│           ├── pipelines.py
│           ├── steps.py
│           ├── reports.py
│           ├── emails.py
│           ├── connections.py
│           ├── providers.py
│           ├── recipients.py
│           ├── runs.py
│           └── setup.py            # OAuth2 setup endpoints
├── frontend/                       # React + Vite + TypeScript
│   └── src/
│       ├── pages/
│       │   ├── Dashboard.tsx
│       │   ├── PipelineBuilder.tsx
│       │   ├── ReportDesigner.tsx
│       │   ├── EmailDesigner.tsx
│       │   ├── Connections.tsx
│       │   ├── Recipients.tsx
│       │   ├── RunHistory.tsx
│       │   ├── Settings.tsx
│       │   └── AuditLog.tsx        # /settings/audit — admin only
│       ├── components/
│       │   ├── pipeline/
│       │   ├── email/
│       │   ├── report/
│       │   └── shared/
│       └── lib/
│           ├── api.ts
│           └── types.ts
├── docs/
│   ├── code-review.md              # Output of Session Zero
│   ├── getting-started.md
│   ├── step-types.md
│   ├── email-providers.md
│   ├── connections.md
│   └── testing.md                  # Full test runbook (all 5 layers)
├── tests/
├── .env.example
├── pyproject.toml
├── requirements.txt
├── README.md
└── LICENSE
```

---

## Design System (Frontend)
See Claude Design handoff. Key tokens:
- Background: `#0F1117`
- Surface: `#1A1D27`, `#21252F`
- Accent: `#F97316` (orange — "forge" heat)
- Success: `#22C55E`, Failure: `#EF4444`, Running: `#3B82F6` (pulse), Pending: `#6B7280`
- Text primary: `#F1F5F9`, muted: `#64748B`
- Font UI: `Inter`
- Font mono: `JetBrains Mono` (SQL editor, logs, cron expressions)
- Radius: `8px` cards, `4px` badges, `6px` inputs

---

## Cost Summary
| Feature | Cost |
|---|---|
| Pipeline execution | $0 |
| Report generation | $0 |
| Gmail send | $0 (Gmail API free tier) |
| Microsoft 365 send | $0 (Graph API free) |
| Google Drive upload | $0 (Drive API free tier) |
| Scheduler | $0 |
| AI analysis (Ollama) | $0 — local |
| AI analysis (Claude API) | Pay-per-use, opt-in only |
| AI analysis (Gemini API) | Free tier available, opt-in only |
| **Monthly baseline** | **$0** |

---

## Non-Goals
> Multi-user auth, Slack/Teams notifications, S3/Azure Blob upload, a visual pipeline canvas, and
> arbitrary step-to-step DAG editing — all originally listed here as deferred to v2/v3 — have since
> shipped; see [ROADMAP.md](ROADMAP.md) and [docs/TASKS.md](docs/TASKS.md) for current status, which
> is authoritative over this file. Drawing a real dependency edge between two steps on the pipeline
> canvas (`docs/TASKS.md` Phase 14.2, "Option B") routes that pipeline's execution through a
> topological DAG engine instead of the default sequential/parallel-wave engine — branch-scoped
> `on_error: stop` (only a failed step's descendants halt) and ancestors-only `{{ steps.* }}` context
> visibility. A pipeline with zero drawn edges is completely unaffected.

- No Airflow DAG import
- No cloud SaaS version
