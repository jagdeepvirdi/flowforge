# Changelog

All notable changes to FlowForge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] — 2026-05-20

### Added

#### Pipeline Engine
- Ordered step execution with `on_error: stop | continue` per step
- Step outputs threaded into downstream steps via `{{ steps.<name>.* }}` variables
- Async pipeline execution — `POST /api/pipelines/<id>/run` returns `202 + run_id` immediately; pipeline runs in a background thread
- `{{ run_id }}` in Jinja2 context now matches the actual `ff_pipeline_runs.id`
- Run history with per-step timing, logs, and error capture in `ff_pipeline_runs` / `ff_step_runs`
- Variable logging — resolved variable values (with secrets masked as `***`) appended to every step run log

#### Step Types
- **`db_procedure`** — call stored procedures and Oracle packages (`package.procedure` syntax); PostgreSQL and Oracle
- **`db_query`** — run SQL, write results to a target table (`replace` / `append` / `truncate_insert` modes); optional `output_variable` to capture a scalar result into pipeline context
- **`report`** — generate Excel, CSV, or PDF from a saved report config; output path available as `{{ steps.<name>.output_path }}`
- **`email`** — send email via any configured provider; smart attachment handling built in
- **`drive_upload`** — upload a file to Google Drive; shareable link available as `{{ steps.<name>.drive_url }}`

#### Database Connections
- PostgreSQL via psycopg2 ThreadedConnectionPool
- Oracle via cx_Oracle (optional extra: `pip install flowforge[oracle]`)
- Both implement a shared `BaseConnection` interface — pipelines don't know which DB they're talking to
- `execute_query_with_columns()` returns actual column names from `cursor.description`; no more `col0 / col1 / col2` in report headers

#### Report Generation
- Excel via openpyxl — optional `.xlsx` template support, auto-width columns, bold headers
- CSV via Python stdlib — UTF-8 BOM, configurable delimiter
- PDF via WeasyPrint (optional install: `pip install flowforge[pdf]`)

#### Email Providers
- **SMTP** — any standard mail server (Outlook, Yahoo, corporate), STARTTLS and SSL/TLS support
- **Gmail** — OAuth2 via `google-auth` + Gmail API; `flowforge setup gmail` guided wizard
- **Microsoft 365** — MSAL client credentials + Microsoft Graph API; `flowforge setup microsoft365` wizard; token re-acquired before every send

#### Variable System (Jinja2)
- Built-ins: `{{ current_date }}`, `{{ current_month }}`, `{{ current_year }}`, `{{ yesterday }}`, `{{ timestamp }}`
- Date-range helpers: `{{ week_start }}`, `{{ week_end }}`, `{{ month_start }}`, `{{ month_end }}`, `{{ quarter_start }}`, `{{ quarter_end }}`
- Runtime: `{{ run_id }}`, `{{ pipeline_name }}`, `{{ env.VAR_NAME }}`
- Step outputs: `{{ steps.<name>.output_path }}`, `{{ steps.<name>.drive_url }}`, `{{ steps.<name>.rows_affected }}`
- Pipeline variables: `{{ my_var }}` / `{{ vars.my_var }}` (secret vars encrypted at rest, masked in UI)
- Scalar capture: `output_variable` on `db_query` steps injects first-column first-row value into context

#### Google Drive
- Upload files, create shareable links
- Smart attachment: files over `attachment_max_mb` threshold auto-uploaded to Drive; link added to email body

#### Scheduler
- APScheduler with PostgreSQL job store
- Hot reload — schedule changes apply without restart
- Cron expression validation via APScheduler `CronTrigger.from_crontab()`
- `GET /api/pipelines/cron-next` — returns next N fire times for any cron expression

#### Frontend
- **Dashboard** — pipeline cards with status badges, Run Now button, live polling during active runs, global stats (runs today, success rate)
- **Pipeline Builder** — step list with drag-to-reorder; per-step type config forms; visual cron builder with frequency presets, live expression preview, and next-5-runs display
- **Report Designer** — CodeMirror 6 SQL editor, format selector, output filename with variable hints, 20-row preview
- **Email Designer** — provider picker, recipient groups, CC/BCC, HTML body editor, smart attachment settings, preview modal
- **Run History** — table with filters; run detail with step timeline, expandable logs, Drive links
- **Connections** — DB connections and email providers in tabbed view; test-connection button; credential masking
- **Settings** — OAuth setup buttons for Gmail and Drive; pipeline YAML export/import
- In-app help system: context-sensitive help drawer, collapsible page intro cards, field-level tooltips, step editor hints, concept glossary
- Help discovery pulse indicator on `?` button (cleared after first open)
- TopBar refresh button — invalidates React Query cache for the current page

#### Security
- AES-256-GCM encryption for all DB credentials and email provider config (key from `FLOWFORGE_SECRET_KEY`)
- Secret pipeline variables encrypted at rest; masked in UI and in run logs
- bcrypt password hashing for the admin user
- JWT authentication — expired, invalid-secret, and malformed tokens all return 401
- Rate limiting on `POST /api/auth/login` — 10 requests/minute per IP (flask-limiter)

#### DevOps
- Docker Compose — bundles Flask API, React/Nginx frontend, and PostgreSQL
- GitHub Actions CI — runs the full pytest suite on every push and pull request
- Alembic database migrations — baseline migration included; `alembic upgrade head` to apply
- `flowforge cleanup` CLI command + daily scheduler job — prunes `./output/` files older than N days

#### CLI
- `flowforge web` — starts Flask dev server
- `flowforge schedule` — starts APScheduler daemon
- `flowforge run <name>` — runs a pipeline by name
- `flowforge list` — lists all pipelines with schedule and status
- `flowforge validate <name>` — validates pipeline config
- `flowforge connections test` — tests all configured DB connections
- `flowforge export <name>` — exports pipeline as YAML
- `flowforge import <file>` — imports pipeline from YAML
- `flowforge cleanup [--days N]` — removes output files older than N days
- `flowforge setup gmail / microsoft365 / drive` — guided OAuth2 setup wizards

#### Documentation
- `docs/getting-started.md` — end-to-end setup walkthrough
- `docs/step-types.md` — full config reference for all step types with YAML examples
- `docs/email-providers.md` — SMTP, M365, and Gmail setup guides
- `docs/gmail-oauth2-setup.md` — step-by-step Gmail OAuth2 guide
- `CONTRIBUTING.md` — dev setup, running tests, project structure, PR process
- GitHub issue templates — bug report and feature request

### Dependencies (optional extras)
- `flowforge[gmail]` — `google-api-python-client`, `google-auth`, `google-auth-oauthlib`
- `flowforge[drive]` — same as `[gmail]`
- `flowforge[microsoft365]` — `msal`
- `flowforge[oracle]` — `cx_Oracle`
- `flowforge[pdf]` — `weasyprint`
- `flowforge[dev]` — `pytest`, `pytest-mock`, `responses`, `pytest-cov`

[Unreleased]: https://github.com/jagdeepvirdi/flowforge/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/jagdeepvirdi/flowforge/releases/tag/v0.1.0
