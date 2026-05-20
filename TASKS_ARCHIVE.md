# TASKS_ARCHIVE.md — FlowForge
*Completed tasks moved here from TASKS.md. Ordered newest-first.*

---

## Completed: Phase 4 Docs (May 2026)

- **`docs/step-types.md`** — Full config spec for all 5 step types (`db_procedure`, `db_query`, `report`, `email`, `drive_upload`) with YAML examples, field tables, output variable docs, and complete variable reference table including all date-range vars.
- **`docs/email-providers.md`** — SMTP setup (with presets for Outlook, Yahoo, SendGrid, Gmail app password), Microsoft 365 step-by-step Azure AD app registration + admin consent + token refresh notes, provider comparison table.
- **`CONTRIBUTING.md`** — Dev setup (venv, DB, env, frontend), running tests (real-DB rationale), project structure, how to add a new step type, PR checklist.
- **`.github/ISSUE_TEMPLATE/bug_report.md`** and **`feature_request.md`** — GitHub issue templates with environment fields, reproduction steps, log paste sections, and affected-area checkboxes.
- **`CHANGELOG.md`** — Fully rewritten v0.1.0 entry covering all shipped features (engine, steps, connections, reports, email providers, variable system, scheduler, frontend, security, DevOps, CLI, docs); `[Unreleased]` stub added; GitHub URL corrected to `jagdeepvirdi/flowforge`.

---

## Completed: Phase 1 Bug Fix (May 2026)

- **Report columns col0/col1/col2** — Added `execute_query_with_columns()` to `BaseConnection`, `PostgreSQLConnection`, and `OracleConnection` returning `(rows, column_names)` from `cursor.description`. `ReportStep` now uses it; explicit `report_cfg['columns']` still overrides when set. (commit `df2f63e`)

---

## Completed: Phase 4 Code Items (May 2026)

- **Visual cron builder** — `PipelineEdit.tsx` — frequency picker (none/minutely/hourly/daily/weekly/monthly/custom) with contextual controls, live cron expression preview, next-5-runs via `GET /api/pipelines/cron-next`. `FieldTooltip` clipping fixed: flips downward when within 220px of viewport top. (commit `aeffc2f`)
- **TopBar refresh button** — `RefreshCw` icon in `TopBar.tsx` calls targeted or global `queryClient.invalidateQueries()`. (commit `aeffc2f`)
- **Help discovery indicator** — Orange pulse dot (`.ff-help-dot`) on `?` button; cleared to `localStorage ff_help_seen` on first open. `@keyframes ff-accent-pulse` added to `index.css`. (commit `aeffc2f`)
- **Run history: log resolved variable values** — `runner.py` appends a "Variables resolved:" block to every `ff_step_runs.logs` entry. Secret vars masked as `***`. `loader.py` now returns `secret_keys: set[str]` as 3rd value; all call-sites updated. (commit `aeffc2f`)
- **Validate cron expressions** — `_validate_cron()` in `pipelines.py` uses APScheduler's `CronTrigger.from_crontab()`; called on pipeline create and update. (commit `aeffc2f`)

---

## Completed: Phase 2 Features (May 2026)

- **Built-in smart date-range variables** — Added `{{ week_start }}`, `{{ week_end }}`, `{{ month_start }}`, `{{ month_end }}`, `{{ quarter_start }}`, `{{ quarter_end }}` to `flowforge/engine/context.py`. ISO week Mon–Sun; quarter Q1=Jan–Mar etc. Tooltip in `helpContent.ts` updated with all new vars and examples. (commit `938459e`)
- **db_query scalar output variable** — Optional `output_variable` field on `db_query` step config captures first column of first row into top-level pipeline context (e.g. `{{ subscription_count }}`). `StepResult.output_variables` dict added; runner propagates it. `StepEditor.tsx` shows the field with inline usage hint. (commit `938459e`)

---

## Completed: Phase 1 Fixes + Phase 2 Tests + Phase 3 Help System (May 2026)

### Phase 1 — Core Stability
- **Database Migrations (Alembic)** — Replaced `db.create_all()` with Alembic; baseline migration in `flowforge/db/migrations/`.
- **M365 Token Refresh** — Token re-acquired via MSAL before each `send()` call in `flowforge/email_providers/microsoft365.py`.
- **CLI Parity: `flowforge import`** — YAML → pipeline + steps via DB (mirrors `flowforge export` in reverse).

### Phase 2 — Tests & Settings OAuth
- **`test_pipeline_variables.py`** — Secret var encrypted on write, decrypted at runtime, `{{ vars.key }}` available in context, plaintext non-secret var unaffected.
- **Settings OAuth Wiring** — "Set up Gmail" button wired to `/api/setup/gmail`; "Set up Drive" button wired; current OAuth status (connected / not connected) shown per provider.

### Phase 3 — In-App Help System (fully complete)

#### HelpDrawer component
- `frontend/src/components/shared/HelpDrawer.tsx` — right-side sliding panel (400px), `?` button in TopBar
- Context-sensitive content based on current route
- Keyboard shortcut: `?` key opens/closes
- Zustand store `useHelp` — `{ open, topic, openHelp(topic?), closeHelp() }`
- Close on Escape + overlay click; smooth slide-in animation

#### Page intro cards
Collapsible "What is this?" card at top of each page (dismissed via `localStorage` flag `ff_help_dismissed_<page>`):
- **Dashboard** — "Your pipeline control center. See last run status, trigger runs manually, monitor active jobs."
- **Pipelines** — "A pipeline is an ordered list of steps. Steps run in sequence: query a DB, generate a report, send an email."
- **Reports** — "Report configs define a SQL query + output format (Excel/PDF/CSV). A report step runs this query and writes the file."
- **Emails** — "Email configs define the subject, body, and recipients. They reference an Email Provider (Gmail/M365/SMTP)."
- **Connections** — "DB Connections store credentials for your databases. Credentials are encrypted at rest."
- **Recipients** — "Recipient groups are named lists of email addresses. Assign a group to an email config instead of typing addresses every time."
- **Run History** — "Every pipeline execution is recorded here. Click a run to see step-by-step timing, logs, and errors."
- **Settings** — "Connect FlowForge to Gmail or Microsoft 365 via OAuth2. Configure system-wide defaults."

#### Field-level tooltips
`(?)` icon → small popover with explanation + example:
- **Cron schedule field** — 5-part format, examples (`0 8 * * 1-5` = weekdays 8am), link to crontab.guru
- **`{{ variable }}` syntax fields** — list all vars: `current_date`, `current_month`, `current_year`, `yesterday`, `run_id`, `pipeline_name`, `steps.step_name.output_path`
- **DB Connection host/port/database** — PostgreSQL vs Oracle example values
- **Drive Folder ID** — "The ID is the last part of the Drive folder URL: `.../folders/THIS_PART`"
- **Attachment max MB** — explain smart attachment threshold behavior
- **Email body template** — note Jinja2 support
- **on_error field** — `stop` vs `continue` behavior
- **Oracle connection string** — both formats: `host:port/service` and TNS alias

#### Empty state guidance
- **Pipelines** — "No pipelines yet…" + Create Pipeline button
- **Connections** — "No connections yet…" + Add Connection button
- **Emails** — "No email configs yet… You'll also need an Email Provider set up first." + links to both
- **Reports** — "No report configs yet…"
- **Run History** — "No runs yet. Trigger a pipeline from the Pipelines page."

#### Concept glossary (HelpDrawer "Glossary" tab)
- Defines: Pipeline, Step, Step Type, Report Config, Email Config, Email Provider, Recipient Group, Smart Attachments, Run, Step Run, Pipeline Variable, on_error
- Each definition: 2-sentence plain English + "Where to find it" link

#### Step editor contextual help
- **db_procedure** — Oracle `package.procedure` syntax note, params support `{{ variables }}`
- **db_query** — `replace` vs `append` mode explanation
- **report** — output path available as `{{ steps.this_step_name.output_path }}`
- **email** — use `{{ steps.report_step.output_path }}` in attachments field
- **drive_upload** — link available as `{{ steps.this_step_name.drive_url }}`

---

## Completed: Score-Driven Roadmap Items (May 2026)

### 🔴 Deployment & DevOps
- **Docker Orchestration** — `docker-compose.yml` bundling Flask, React (Nginx), and PostgreSQL. (commit `66220d0`)
- **GitHub Actions CI** — `.github/workflows/test.yml` running pytest on every push/PR. (commit `57f5222`)

### 🟡 Security & Stability
- **Security Hardening** — `flask-limiter` on `/api/auth/login` (10/min per IP). (commit `57f5222`)
- **Output TTL Cleanup** — `flowforge cleanup` CLI command + daily scheduler job to prune `./output/`. (commit `ecfe8de`)
- **Context Sync** — `{{ run_id }}` in Jinja2 context now matches the actual `ff_pipeline_runs.id`. (commit `66220d0`)

### 🔵 Technical Debt & Polish
- **SDK Extras** — `google-api-python-client`, `google-auth`, `google-auth-oauthlib`, `msal` moved to optional extras (`[gmail]`, `[drive]`, `[microsoft365]`). (commit `167fd9e`)
- **Python 3.12 Compliance** — `utcnow()` replaced with `datetime.now(timezone.utc)` across all models. (commit `66220d0`)
- **GitHub repo URLs** — Placeholder `YOUR_GITHUB_USERNAME` replaced with `jagdeepvirdi/flowforge`. (commit `b975bf1`)
- **OneDrive backlog entry** — Implementation notes added to v2 backlog. (commit `291a13a`)

---

## Completed: All 8 GitHub Release Blockers (commit `c749de7`)

1. Legacy `code/` directory removed from git tracking
2. CLI setup commands print actionable instructions
3. `xlsxwriter` removed, `requests` added, `cx_Oracle` corrected in deps
4. Async pipeline execution — `POST /run` returns 202 + `run_id` immediately
5. DB credentials + email provider configs encrypted (AES-256-GCM)
6. Secret pipeline variables masked in UI and encrypted at rest
7. JWT auth hardened (expired/bad-secret/malformed all → 401)
8. Admin user seeded from env vars on startup

---

## Completed: Pre-Phase — Scrub & Refactor Sessions

- **Session Zero** — Full structured code review saved to `docs/code-review.md`
- **Session 1** — Dead code removed, duplicate logic consolidated, debug prints cleaned
- **Session 2** — All company/telecom/internal references scrubbed
- **Session 3** — Refactored into FlowForge package layout (`engine/`, `steps/`, `connections/`, `email_providers/`, `reports/`, `storage/`)
- **Session 4** — GitHub release files created: README, .gitignore, pyproject.toml, .env.example, LICENSE, CHANGELOG.md, getting-started.md

---

## Completed: Phase 1 — Database Schema & API Foundation

- Full PostgreSQL schema: `email_providers`, `db_connections`, `pipelines`, `pipeline_steps`, `pipeline_variables`, `report_configs`, `email_configs`, `recipient_groups`, `pipeline_runs`, `step_runs` (11 tables)
- SQLAlchemy models for all tables
- `flowforge/crypto.py` — AES-256-GCM encrypt/decrypt, key from `FLOWFORGE_SECRET_KEY`
- Flask app factory, JWT auth middleware, CORS, health check, JSON error handler
- All REST routes: pipelines, steps, reports, emails, recipients, connections, providers, runs (full CRUD + test endpoints)

---

## Completed: Phase 2 — Core Engine

- `flowforge/engine/context.py` — Jinja2 variable resolution: `current_month`, `current_date`, `current_year`, `yesterday`, `run_id`, `pipeline_name`, `failed_step`, `env.VAR`, `steps.x.output_path`, `steps.x.drive_url`, `{{ timestamp }}`
- `flowforge/engine/runner.py` — step ordering, `on_error: stop/continue`, context passing, `pipeline_run` + `step_run` DB records, async daemon thread execution
- `flowforge/engine/scheduler.py` — APScheduler with PostgreSQL job store, hot reload, misfire grace

---

## Completed: Phase 3 — Step Implementations

- `flowforge/steps/base.py` — `BaseStep` ABC + `StepResult` dataclass
- `flowforge/steps/db_procedure.py` — PostgreSQL + Oracle stored procedures/packages
- `flowforge/steps/db_query.py` — SQL query → output table (replace/append/truncate_insert)
- `flowforge/steps/report.py` — dispatches to Excel/PDF/CSV generators, output path in context
- `flowforge/steps/email_step.py` — smart attachment logic, provider dispatch
- `flowforge/steps/drive_upload.py` — Drive upload, shareable link in context

---

## Completed: Phase 4 — Email Providers

- `flowforge/email_providers/base.py` — `EmailProvider` ABC
- `flowforge/email_providers/gmail.py` — OAuth2 via `google-auth` + Gmail API
- `flowforge/email_providers/microsoft365.py` — MSAL client credentials + Graph API (token refresh still has 1h bug — see remaining tasks)
- `flowforge/email_providers/smtp.py` — `smtplib`, covers STARTTLS/SSL, Outlook/Yahoo/corporate

---

## Completed: Phase 5 — Database Connections

- `flowforge/connections/base.py` — `BaseConnection` ABC
- `flowforge/connections/postgres.py` — `psycopg2` ThreadedConnectionPool, parameterized queries, bulk insert
- `flowforge/connections/oracle.py` — `cx_Oracle`, package.procedure syntax, LOB/DATE/TIMESTAMP handling, arraysize
- Connection factory: `get_connection(id)` → decrypts config, instantiates correct class

---

## Completed: Phase 6 — Report Generators

- `flowforge/reports/excel_report.py` — optional template, headers, auto-width columns, bold headers
- `flowforge/reports/pdf_report.py` — Jinja2 HTML → weasyprint (optional dep)
- `flowforge/reports/csv_report.py` — UTF-8 BOM option, configurable delimiter

---

## Completed: Phase 7 — Scheduler & CLI (partial)

- `flowforge schedule` — APScheduler daemon with PostgreSQL job store
- `flowforge run`, `flowforge list`, `flowforge validate`, `flowforge connections test`
- `flowforge setup gmail`, `flowforge setup microsoft365`, `flowforge setup drive`
- `flowforge web` — start Flask + React frontend
- `flowforge export <pipeline>` — export pipeline as YAML
- `flowforge cleanup` — prune output files older than N days
- `server_start.ps1` / `server_start.sh` scripts

---

## Completed: Phase 8 — Frontend (scaffolded and wired)

- React + Vite + TypeScript scaffold, design tokens applied to `tailwind.config.ts`
- React Query + React Router + JWT auth (login, token storage, API interceptor)
- **Dashboard** — pipeline cards, status badges, live polling, global stats
- **Pipeline Builder** — list, edit, step forms (db_procedure, db_query, report, email, drive_upload), drag-to-reorder, cron builder, on_error toggle
- **Report Designer** — SQL editor (CodeMirror 6), format selector, output filename, Preview (first 20 rows)
- **Email Designer** — provider picker, recipients, CC/BCC, subject, body editor, smart attachment settings, Preview modal
- **Recipient Groups** — create/edit groups, address chip input
- **Connections Manager** — DB connections + email providers tabbed, test button, credential masking
- **Run History** — table with filters, run detail with step timeline + expandable logs
- **Settings** — OAuth setup buttons, defaults, YAML export/import
- Report step output file download

---

## Completed: Test Suite (168 tests passing)

| File | Coverage |
|---|---|
| `test_crypto.py` | encrypt/decrypt, unique nonces, bad key |
| `test_auth.py` | login, JWT, protected routes |
| `test_connections.py` | DB connection CRUD + live test + raw test |
| `test_pipelines.py` | pipeline CRUD + step CRUD |
| `test_reports.py` | report config CRUD + preview + semicolon fix |
| `test_recipients.py` | recipient group CRUD |
| `test_runs.py` | run history filters + disabled pipeline guard |
| `test_email_configs.py` | email config CRUD |
| `test_email_providers.py` | mocked SMTP send (SSL, TLS, CC/BCC, attachments, failure) |
| `test_context.py` | Jinja2 variable resolution (all vars) |
| `test_runner.py` | step ordering, on_error stop/continue, context passing |
| `test_steps_db.py` | db_query + db_procedure with mocked connections |
| `test_report_generators.py` | Excel headers/data/bold; CSV header row, delimiter |
| `test_smart_attachments.py` | under/over limit, Drive upload + link, missing file |
| `test_jwt_expiry.py` | expired/bad-secret/malformed/empty/no-header → 401 |

Manual test scripts in `tests/manual/`: `check_api.py`, `check_email.py`, `check_runner.py`, `check_scheduler.py`
