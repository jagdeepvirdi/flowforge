# TASKS.md — FlowForge

---

## Current Status (as of 2026-05-18)

### ✅ Done
- DB schema, SQLAlchemy models, all 11 tables
- AES-256 credential encryption (`crypto.py`)
- Flask API — all REST routes wired
- JWT auth, admin user seeding from env
- DB connections — PostgreSQL + Oracle + factory + test endpoint
- Frontend — all pages scaffolded and wired (Dashboard, Pipelines, Run History, Run Detail, Connections, Reports, Emails, Recipients, Settings, Login)
- Report preview (SQL → first 20 rows)
- Add/Edit Connection modal with Test-before-save
- `server_start` / `server_stop` scripts (.ps1 + .sh)

### ⚠️ Exists but Untested End-to-End
- Pipeline runner (`engine/runner.py`, `engine/context.py`)
- All step types (db_procedure, db_query, report, email, drive_upload)
- Email providers (Gmail OAuth2, M365, SMTP)
- Report generators (Excel, CSV, PDF)
- Scheduler (APScheduler with cron)
- Pipeline Builder step config saving

### ❌ Not Yet Done
- Settings page OAuth setup wizards (buttons are stubs)
- CLI commands (`flowforge run`, `flowforge list`, etc.)
- Google Drive folder picker in UI (text input only)
- Email body preview (render-in-modal)
- Automated test suite
- Docs: `step-types.md`, `email-providers.md`, `connections.md`, `cli-reference.md`
- GitHub public release (README polish, topics, v0.1.0 tag)
- AI analyze step (v2 backlog)

---

## Immediate Action Items

### 1 — End-to-End Pipeline Test
- [ ] Create a DB connection in the UI → run Test → verify "Connected"
- [ ] Create a report config with a simple `SELECT` query → run Preview → verify rows appear
- [ ] Create a pipeline with one `report` step → click Run Now → check Run History for success/failure logs
- [ ] Add an `email` step after the report step → run the pipeline → verify email received
- [ ] Check that `{{ current_date }}` resolves correctly in output filename and email subject

### 2 — Fix Any Runner Bugs Found Above
- [ ] Diagnose and fix any step execution errors from the test run
- [ ] Verify `StepResult.output_path` flows from report step → email step attachments
- [ ] Verify `duration_ms` and `rows_affected` are written to `ff_step_runs`

### 3 — Scheduler Smoke Test
- [ ] Create a pipeline with a cron schedule (e.g. `* * * * *` = every minute)
- [ ] Start the scheduler — verify run appears in Run History automatically
- [ ] Disable the pipeline — verify no more runs triggered

### 4 — Settings OAuth Wiring
- [ ] Wire "Set up Gmail" button in Settings to redirect to `/api/setup/gmail`
- [ ] Wire "Set up Drive" button similarly
- [ ] Show current OAuth status (connected / not connected) per provider

### 5 — Test Suite (Missing Tests)

#### Already Written ✅
- [x] `test_crypto.py` — encrypt/decrypt, unique nonces, bad key
- [x] `test_auth.py` — login, JWT, protected routes
- [x] `test_connections.py` — DB connection CRUD + live test + raw test
- [x] `test_pipelines.py` — pipeline CRUD + step CRUD
- [x] `test_reports.py` — report config CRUD + preview + semicolon fix
- [x] `test_recipients.py` — recipient group CRUD
- [x] `test_runs.py` — run history filters + disabled pipeline guard

#### Written ✅ (all 168 tests pass)
- [x] `test_email_configs.py` — email config CRUD (create, get, update, delete)
- [x] `test_email_providers.py` — email provider CRUD + mocked SMTP send (SSL, TLS, CC/BCC, attachments, failure handling)
- [x] `test_context.py` — Jinja2 variable resolution: `current_date`, `current_month`, `current_year`, `yesterday`, `run_id`, `pipeline_name`, `env.VAR`, `steps.x.output_path`, `steps.x.drive_url`
- [x] `test_runner.py` — pipeline executor with mocked steps: step ordering, on_error stop, on_error continue, context passing between steps
- [x] `test_steps_db.py` — db_query and db_procedure steps with mocked connections: rows returned, rows_affected, output_table, param variable resolution
- [x] `test_report_generators.py` — Excel headers/data/bold/sheet name; CSV header row, delimiter, encoding
- [x] `test_smart_attachments.py` — file under limit → direct attach; file over limit → Drive upload + link in body; missing file skipped; threshold edge cases
- [x] `test_jwt_expiry.py` — expired/bad-secret/malformed/empty/no-header/wrong-scheme all → 401

#### Still To Write
- [ ] `test_pipeline_variables.py` — pipeline variables stored encrypted if `is_secret=True`; available in context as `{{ vars.key }}`

#### Manual / Live Tests (in `tests/manual/`)
- [x] `check_api.py` — full API smoke test against live server
- [x] `check_email.py` — send a real Gmail test email
- [x] `check_runner.py` — trigger a real pipeline run via API, poll until complete, assert success
- [x] `check_scheduler.py` — enable a 1-minute cron pipeline, wait, confirm run appeared

### 6 — Documentation
- [ ] Review `docs/gmail-oauth2-setup.md` — add screenshots, verify steps still match Google UI
- [ ] Write `docs/email-providers.md` (SMTP + M365 sections)
- [ ] Write `docs/step-types.md`

---

## Session Zero — Code Review (MANDATORY FIRST STEP)

**Do this before any other session. No code changes. Review only.**

### Claude Code Prompt for Session Zero
```
Read ALL existing code in this project directory carefully.
Do NOT make any changes.

Produce a structured code review saved to docs/code-review.md covering:

1. INVENTORY
   - List every file with a one-line description of what it does
   - Identify all entry points (scripts that are run directly)
   - Map how files import and call each other

2. EXISTING CAPABILITIES — for each, describe HOW it currently works:
   - Email sending: which library, which provider, how configured?
   - Google Drive upload: which library, how authenticated?
   - Report generation: which formats, which libraries?
   - Database connections: which DBs, how connection strings stored?
   - Stored procedure/package calls: how are these currently invoked?
   - Scheduling: how are jobs currently triggered?
   - Configuration: what is hardcoded vs file-based vs DB-stored?

3. DATABASE SCHEMA
   - List every table the code reads from or writes to
   - For each table: what is it used for?
   - Identify config tables vs data/staging tables
   - List all stored procedures or packages called by name

4. CODE QUALITY ASSESSMENT
   - Which modules are clean and reusable as-is?
   - Which are tightly coupled to internal systems?
   - Where is error handling missing or insufficient?
   - Where are credentials or sensitive values hardcoded?
   - Any SQL built by string formatting (security risk)?
   - Any large monolithic functions that need breaking up?

5. SCRUB PRIORITY LIST
   - Every company/telecom reference found (file + line number)
   - Every hardcoded credential (file + line number)
   - Every internal hostname, URL, email address
   - Every internal table name that reveals business context
   - Ranked: MUST REMOVE before GitHub / SHOULD REMOVE / OPTIONAL

6. REUSE PLAN
   - Which existing functions map directly to FlowForge step types?
   - What can be wrapped vs what needs rewriting?
   - Any existing DB schema tables that become FlowForge config tables?

Save the complete review to docs/code-review.md.
Stop here. Do not make any code changes.
```

### After Session Zero — Review the Output
- [ ] Read `docs/code-review.md` fully before proceeding
- [ ] Verify the scrub list is complete — add anything missed
- [ ] Note which existing capabilities are reusable — update this TASKS.md if needed
- [ ] Upload `docs/code-review.md` to DevBrain as a FlowForge document
- [ ] Only then proceed to Scrub Sessions

---

## Pre-Phase: Scrub Existing Code (4 Claude Code Sessions)

### Session 1 — Cleanup & Consolidation

**Goal**: Produce a smaller, cleaner codebase before any scrubbing begins.
Dead files deleted. Duplicate logic merged. Bloated functions split.
Do NOT scrub company references yet. Do NOT restructure into FlowForge
folders yet. Cleanup only — every change must be reversible via git.

**Why cleanup before scrub**: Scrubbing dead code wastes effort. Merging
duplicates after scrubbing means scrubbing the same logic twice. Clean
first, scrub second, restructure third.

```
Read D:\Project\flowforge\docs\code-review.md carefully.
Read ALL existing code in D:\Project\flowforge.
Also read D:\Project\flowforge\CLAUDE.md for planned architecture.

Do NOT scrub company or telecom references yet.
Do NOT restructure into FlowForge package folders yet.
Do NOT change any business logic.
This session is cleanup and consolidation only.

Work through these tasks in order.
Commit after each task so every change is reversible.

─────────────────────────────────────────
TASK 1 — DELETE DEAD CODE AND UNUSED FILES
─────────────────────────────────────────
Identify and delete:
- Files that are never imported or called by anything
- Functions that are defined but never called anywhere
- Large blocks of commented-out old code (10+ lines)
- Duplicate files — same logic existing in two places
- Old or backup files: anything named with suffix
  _old, _bak, _v1, _v2, _copy, _backup, _temp, _test,
  or prefixed with old_, bak_, temp_, draft_
- One-off scripts that were clearly used once and abandoned
- Empty files (0 lines or only comments/whitespace)

Before deleting any file — confirm it is truly unused:
check ALL import statements and ALL function calls
across the entire codebase. If unsure — keep it and
flag it in the cleanup report instead.

Commit: git commit -m "cleanup: remove dead code and unused files"

─────────────────────────────────────────
TASK 2 — CONSOLIDATE DUPLICATE LOGIC
─────────────────────────────────────────
Using the duplication analysis from code-review.md,
consolidate each category of duplication:

DB Connections:
- If multiple files open DB connections separately,
  merge ALL connection logic into one file: db.py
  or connections.py (do not use FlowForge folder
  names yet — just consolidate into one place)
- Update all other files to import from this one file
- Delete the duplicate connection code from each file

Email Sending:
- If multiple files contain email sending logic,
  merge ALL email logic into one file: email.py
  or mailer.py
- Update all callers to import from this one file
- Delete the duplicate email code from each file

Report Generation:
- If report building logic is repeated or scattered,
  consolidate into one file per format
  (excel.py, pdf.py, csv.py or a single reports.py)
- Delete duplicate report code

Drive Upload:
- If Drive upload logic exists in more than one place,
  merge into one file: drive.py
- Update all callers, delete duplicates

Any other duplications flagged in the review:
- Apply the same pattern: consolidate → update
  callers → delete duplicates

After each consolidation run the code mentally to
confirm the callers still work with the merged version.

Commit after each category:
git commit -m "cleanup: consolidate {category} into single module"

─────────────────────────────────────────
TASK 3 — SPLIT FUNCTIONS THAT DO TOO MUCH
─────────────────────────────────────────
From the code review, any function flagged as doing
more than one thing must be split into focused
single-purpose functions.

Common patterns to fix:
  generate_and_send_report(params)
  → generate_report(params) → returns file_path
  → send_email(file_path, recipients) → returns bool

  fetch_data_and_build_excel(params)
  → fetch_data(query, params) → returns rows
  → build_excel(rows, output_path) → returns file_path

Rules for splitting:
- Each new function does exactly one thing
- Function name describes what it does, not when
- Update the original caller to call both functions
  in sequence — do not change the caller's behavior
- If the original function is called in multiple
  places, update all call sites

Commit after each split:
git commit -m "cleanup: split {function_name} into focused functions"

─────────────────────────────────────────
TASK 4 — REMOVE OBVIOUS JUNK
─────────────────────────────────────────
Across all surviving files:

- Remove all print() debug statements
  Replace with logging.debug() where the output
  is genuinely useful, remove entirely otherwise
- Remove unused imports at the top of each file
  (imported but never referenced in the file)
- Remove large blocks of commented-out old code
  that were not caught in Task 1
- Remove stale TODO and FIXME comments that
  reference internal systems, old tickets, or
  people's names
- Remove any hardcoded test data or example
  values embedded in non-test files

Do NOT remove logging statements that are currently
active and useful — only print() calls.

Commit: git commit -m "cleanup: remove debug prints, unused imports, stale comments"

─────────────────────────────────────────
TASK 5 — FLATTEN UNNECESSARY STRUCTURE
─────────────────────────────────────────
Look at the folder structure:
- If a folder contains only one file and exists
  purely for organization that adds no clarity,
  move the file up and delete the folder
- If __init__.py files are importing things that
  nothing outside uses, simplify them
- If config is split across many small files that
  logically belong together, merge them into one
- If there are nested utils/helpers/common folders
  inside other folders, flatten where sensible

Do NOT flatten if the structure is intentional and
clear — only flatten genuinely confusing nesting.

Commit: git commit -m "cleanup: flatten unnecessary folder structure"

─────────────────────────────────────────
TASK 6 — FINAL CLEANUP REPORT
─────────────────────────────────────────
After all tasks are done, produce a summary and
save it to docs/cleanup-report.md:

## Cleanup Report

### File Count
- Files before cleanup: X
- Files after cleanup:  Y
- Files deleted:        Z

### Deleted Files
List every deleted file and why it was deleted:
| File | Reason |
|------|--------|
| old_report.py | Unused — never imported |

### Consolidated Modules
List every consolidation made:
| What | From (files) | Into (file) |
|------|-------------|-------------|
| DB connections | db_utils.py, helpers.py | connections.py |

### Functions Split
List every function that was split:
| Original | Split Into |
|----------|-----------|
| generate_and_send() | generate_report() + send_email() |

### Remaining Files
Brief description of every file that survived:
| File | Purpose |
|------|---------|
| main.py | Entry point |
| connections.py | All DB connection logic |

### Code Volume
- Approximate lines before cleanup: X
- Approximate lines after cleanup:  Y
- Reduction: Z%

### Flagged Items (kept but uncertain)
List anything you were unsure about deleting:
| File/Function | Reason kept | Recommendation |

Save to docs/cleanup-report.md

─────────────────────────────────────────
STRICT RULES FOR THIS SESSION
─────────────────────────────────────────
✅ Delete unused files and functions
✅ Merge duplicate logic into single files
✅ Split functions that do more than one thing
✅ Remove print() and unused imports
✅ Commit after each task
✅ Save cleanup-report.md at the end

❌ Do NOT rename variables or functions
❌ Do NOT scrub company or telecom references
❌ Do NOT restructure into FlowForge package folders
❌ Do NOT change business logic
❌ Do NOT delete anything you are unsure about
   — flag it in the report instead
```

### After Session 1 — Review the Output
- [ ] Read `docs/cleanup-report.md`
- [ ] Check the "Flagged Items" section — decide what to delete
- [ ] Upload `docs/cleanup-report.md` to DevBrain as a FlowForge document
- [ ] Note the file count and line reduction — update CLAUDE.md if architecture assumptions changed
- [ ] Only then proceed to Session 2 (Scrub)

### Session 2 — Apply Scrub
```
Read docs/code-review.md and the scrub mapping.

Apply ALL scrub changes:
- Company/telecom names → generic equivalents
- Internal email addresses → {{ env.RECIPIENT }} pattern  
- Hardcoded credentials → os.environ.get('VAR_NAME')
- Internal table names → agreed generic names
- Internal hostnames/URLs → env vars
- Remove all comments referencing internal systems

Commit after each file:
git commit -m "scrub: remove company references from {filename}"

Run grep scan after all files done — confirm zero remaining references.
```

### Session 3 — Refactor & Restructure
```
Read docs/code-review.md and scrubbed code.

Restructure into FlowForge package layout as defined in CLAUDE.md.

Priority:
1. Extract email sending → flowforge/email_providers/ (Gmail, SMTP classes)
2. Extract Drive upload → flowforge/storage/google_drive.py
3. Extract report generation → flowforge/reports/ (excel, pdf, csv)
4. Extract DB connections → flowforge/connections/ (postgres, oracle)
5. Wrap each in BaseStep subclass → flowforge/steps/
6. Add type hints, docstrings, proper logging throughout
7. Parameterize all SQL (no f-string or % formatting)
8. Add connection pooling to PostgreSQL connection

Do NOT change what the code does — only restructure how it is organized.
Commit after each major module extraction.
```

### Session 4 — GitHub Ready
```
Create all GitHub release files:
- README.md (see Phase 7 for content spec)
- .gitignore (Python + .env + output/ + *.log + connections.yaml)
- requirements.txt (pip freeze with pinned versions)
- pyproject.toml
- .env.example (all variables with inline comments)
- LICENSE (MIT)
- CHANGELOG.md (v0.1.0 — initial public release)
- docs/getting-started.md
- pipelines/ directory with example_pipeline YAML

Final verification — scan every file:
- Zero company/telecom references
- Zero hardcoded credentials  
- Zero internal hostnames or email addresses
- All TODO comments that reference internal systems removed

Report any found. Do not push until confirmed clean.
```

---

## Phase 1 — Database Schema & API Foundation (Week 1–2)

### FlowForge Internal DB Schema
- [ ] Create full schema from CLAUDE.md:
  - [ ] `email_providers` table (Gmail, M365, SMTP configs — encrypted JSONB)
  - [ ] `db_connections` table (PostgreSQL, Oracle configs — encrypted JSONB)
  - [ ] `pipelines` table
  - [ ] `pipeline_steps` table (ordered, JSONB config per step type)
  - [ ] `pipeline_variables` table (key/value with is_secret flag)
  - [ ] `report_configs` table
  - [ ] `email_configs` table (full email config including smart attachment fields)
  - [ ] `recipient_groups` table
  - [ ] `pipeline_runs` table
  - [ ] `step_runs` table (output_path, drive_url, email_sent_to columns)
- [ ] Enable pgvector extension (for future AI features)
- [ ] Write migration scripts
- [ ] SQLAlchemy models for all tables
- [ ] Seed: default admin user

### Encryption
- [ ] Build `flowforge/crypto.py`:
  - [ ] AES-256-GCM encrypt/decrypt using `cryptography` library
  - [ ] Key from `FLOWFORGE_SECRET_KEY` env var
  - [ ] `encrypt_config(dict) → str` — encrypts sensitive JSONB fields
  - [ ] `decrypt_config(str) → dict` — decrypts on read
  - [ ] Apply to: `db_connections.config`, `email_providers.config`, secret pipeline variables

### Flask API Setup
- [ ] Flask app factory in `flowforge/api/app.py`
- [ ] JWT auth middleware (single user v1)
- [ ] CORS configured for frontend dev server
- [ ] Health check: `GET /api/health`
- [ ] Error handler: returns JSON error responses consistently

### Core REST API Routes
- [ ] `GET/POST /api/pipelines`
- [ ] `GET/PUT/DELETE /api/pipelines/:id`
- [ ] `GET/POST /api/pipelines/:id/steps`
- [ ] `PUT/DELETE /api/pipeline-steps/:id`
- [ ] `POST /api/pipelines/:id/run` — trigger pipeline run
- [ ] `GET /api/pipelines/:id/runs` — run history for pipeline
- [ ] `GET/POST /api/report-configs`
- [ ] `GET/PUT/DELETE /api/report-configs/:id`
- [ ] `GET/POST /api/email-configs`
- [ ] `GET/PUT/DELETE /api/email-configs/:id`
- [ ] `GET/POST /api/recipient-groups`
- [ ] `GET/PUT/DELETE /api/recipient-groups/:id`
- [ ] `GET/POST /api/db-connections`
- [ ] `PUT/DELETE /api/db-connections/:id`
- [ ] `POST /api/db-connections/:id/test`
- [ ] `GET/POST /api/email-providers`
- [ ] `PUT/DELETE /api/email-providers/:id`
- [ ] `POST /api/email-providers/:id/test`
- [ ] `GET /api/runs` — all run history with filters
- [ ] `GET /api/runs/:id` — run detail with step runs

---

## Phase 2 — Core Engine (Week 2)

### Pipeline Loader
- [ ] Build `flowforge/engine/loader.py`:
  - [ ] Load pipeline from DB (not YAML — DB is source of truth)
  - [ ] Validate step configs at load time
  - [ ] Return typed `Pipeline` dataclass with ordered steps

### Variable Context
- [ ] Build `flowforge/engine/context.py`:
  - [ ] Built-in vars: `current_month`, `current_date`, `current_year`, `yesterday`, `run_id`, `pipeline_name`, `failed_step`
  - [ ] `{{ env.VAR }}` → os.environ
  - [ ] `{{ steps.step_name.output_path }}` → from step results
  - [ ] `{{ steps.step_name.drive_url }}` → from step results
  - [ ] `{{ ai_summary }}` → from ai_analyze step result
  - [ ] Jinja2 render all string config values before step execution

### Pipeline Runner
- [ ] Build `flowforge/engine/runner.py`:
  - [ ] Load pipeline config from DB
  - [ ] Create `pipeline_run` record (status: running)
  - [ ] Execute steps in `step_order` order
  - [ ] Pass context between steps
  - [ ] `on_error: stop` → abort, run on_failure steps
  - [ ] `on_error: continue` → log, continue
  - [ ] Run on_success or on_failure steps at end
  - [ ] Write `step_run` record after each step
  - [ ] Update `pipeline_run` to success/failed + duration on completion
  - [ ] Stream logs to SSE endpoint during run (frontend polls this)

---

## Phase 3 — Step Implementations (Week 2–3)

### Base Step
- [ ] `flowforge/steps/base.py` — `BaseStep` abstract + `StepResult` dataclass

### db_procedure Step
- [ ] Load connection from `db_connections` table (decrypt config)
- [ ] Route to PostgreSQL or Oracle connection class
- [ ] Build params dict from config + context variable resolution
- [ ] PostgreSQL: `CALL procedure_name(params)` or `SELECT function_name(params)`
- [ ] Oracle: `BEGIN package_name.procedure_name(params); END;`
- [ ] Log: procedure name, params (mask secrets), duration, success/error

### db_query Step
- [ ] Load connection from DB
- [ ] Render SQL through Jinja2 context
- [ ] Execute query → fetch all rows
- [ ] Write to output_table (replace/append/truncate_insert modes)
- [ ] Log: rows fetched, rows written, duration

### report Step
- [ ] Load `report_config` from DB
- [ ] Load connection from report_config
- [ ] Execute report query
- [ ] Dispatch to excel/pdf/csv report generator
- [ ] Ensure `output/` directory exists
- [ ] Render output filename through Jinja2
- [ ] Store output path in StepResult → available to downstream steps

### email Step (with smart attachment)
- [ ] Load `email_config` from DB (decrypt provider config)
- [ ] Resolve recipient list (group or direct addresses)
- [ ] Resolve attachment paths through Jinja2 (file paths from previous steps)
- [ ] **Smart attachment logic**:
  - [ ] For each attachment: check file size vs `attachment_max_mb`
  - [ ] If over limit: upload to Drive → get shareable link → add to drive_links list
  - [ ] If under limit: add to direct attachments list
  - [ ] Render `drive_share_message` template with drive_links → append to email body
- [ ] Render subject, header, body through Jinja2
- [ ] Dispatch to correct email provider (Gmail/M365/SMTP)
- [ ] Log: provider, recipients, subject, attachment count, drive uploads, duration

### drive_upload Step
- [ ] Resolve file path through Jinja2
- [ ] Upload via `google_drive.py`
- [ ] Get shareable link
- [ ] Store drive_url in StepResult

---

## Phase 4 — Email Providers (Week 3)

### Base Provider
- [ ] `flowforge/email_providers/base.py` — `EmailProvider` ABC

### Gmail Provider
- [ ] `flowforge/email_providers/gmail.py`
- [ ] OAuth2 via `google-auth` + Gmail API
- [ ] Refresh token stored encrypted in `email_providers.config`
- [ ] Build MIME message with HTML body + attachments
- [ ] Handle send errors with retry (3 attempts, exponential backoff)

### Microsoft 365 Provider
- [ ] `flowforge/email_providers/microsoft365.py`
- [ ] `msal` library — client credentials flow
- [ ] Azure AD app registration required (document in setup guide)
- [ ] Send via Microsoft Graph API: `POST /v1.0/users/{sender}/sendMail`
- [ ] Handle attachment as base64 in Graph API payload
- [ ] `flowforge setup microsoft365` — device code flow → saves tokens encrypted
- [ ] Token refresh handled automatically via MSAL token cache

### SMTP Provider
- [ ] `flowforge/email_providers/smtp.py`
- [ ] `smtplib` + `email.mime`
- [ ] Config: host, port, username, password, use_tls (STARTTLS), use_ssl
- [ ] Covers: Outlook (smtp.office365.com:587), Yahoo, corporate mail
- [ ] Connection test: `EHLO` + auth verify

### Provider Factory
- [ ] `get_email_provider(provider_id) → EmailProvider`
- [ ] Loads from DB, decrypts config, instantiates correct class

---

## Phase 5 — Database Connections (Week 3)

### Base Connection
- [ ] `flowforge/connections/base.py` — `BaseConnection` ABC:
  - [ ] `execute_procedure(name, params)` → success/error
  - [ ] `execute_query(sql, params)` → rows
  - [ ] `execute_write(sql, params, output_table, mode)` → rows_affected
  - [ ] `test()` → bool + latency_ms
  - [ ] Context manager (auto-close/pool-return)

### PostgreSQL Connection
- [ ] `flowforge/connections/postgres.py`
- [ ] `psycopg2.pool.ThreadedConnectionPool` (min=1, max=5)
- [ ] `execute_procedure`: `SELECT proc_name(%(param)s)` or `CALL proc_name(%(param)s)`
- [ ] Parameterized queries only — no string formatting
- [ ] `execute_write`: bulk insert via `execute_values` for performance
- [ ] `test()`: simple `SELECT 1`, return latency

### Oracle Connection
- [ ] `flowforge/connections/oracle.py`
- [ ] `cx_Oracle` with connection pool
- [ ] Oracle Instant Client dependency — documented clearly
- [ ] `execute_procedure`: `BEGIN pkg.proc(:param); END;` with named params
- [ ] Handle Oracle package syntax: split `package.procedure` on `.`
- [ ] Handle Oracle types: LOB → read as string, DATE/TIMESTAMP → Python datetime
- [ ] `arraysize = 1000` on cursors for bulk fetch performance
- [ ] `test()`: `SELECT 1 FROM DUAL`, return latency

### Connection Factory
- [ ] `get_connection(connection_id) → BaseConnection`
- [ ] Loads from DB, decrypts config, instantiates correct class

---

## Phase 6 — Report Generators (Week 3–4)

### Excel Report
- [ ] `flowforge/reports/excel_report.py`
- [ ] Optional template: load `.xlsx`, write data starting at configured row
- [ ] No template: create new workbook, write headers + data
- [ ] Auto-width columns (cap at 60 chars)
- [ ] Header row: bold + background color
- [ ] Support multiple sheets (one query result per sheet config)
- [ ] Number/date formatting based on column type

### PDF Report
- [ ] `flowforge/reports/pdf_report.py`
- [ ] Jinja2 HTML template → `weasyprint` → PDF
- [ ] Default template: clean table layout with title, date, data
- [ ] Custom templates: user uploads HTML template to `templates/pdf/`
- [ ] Make `weasyprint` an optional dependency: `pip install flowforge[pdf]`

### CSV Report
- [ ] `flowforge/reports/csv_report.py`
- [ ] UTF-8 BOM encoding option (for Excel CSV compatibility)
- [ ] Configurable delimiter, quoting
- [ ] Optional header row

---

## Phase 7 — Scheduler & CLI (Week 4)

### Scheduler
- [ ] APScheduler with PostgreSQL job store (survives restarts)
- [ ] On start: load all enabled pipelines with `schedule` field → register cron jobs
- [ ] Poll DB every 60s for schedule changes (hot reload)
- [ ] `enabled: false` pipelines automatically unregistered
- [ ] Log next 3 scheduled runs on startup
- [ ] Missed run handling: `misfire_grace_time=300` (5 min grace)

### CLI
- [ ] `flowforge list` — table: name, schedule, last run, status, next run
- [ ] `flowforge run <pipeline_name>` — run now, stream logs
- [ ] `flowforge run <pipeline_name> --step <step_name>` — single step
- [ ] `flowforge schedule start` — start scheduler daemon
- [ ] `flowforge validate <pipeline_name>` — test connections, validate SQL
- [ ] `flowforge connections test <name>` — test DB connection
- [ ] `flowforge setup gmail` — OAuth2 wizard
- [ ] `flowforge setup microsoft365` — MSAL device code flow
- [ ] `flowforge setup drive` — Drive OAuth2 wizard
- [ ] `flowforge web` — start Flask + React frontend
- [ ] `flowforge export <pipeline_name>` — export pipeline as YAML
- [ ] `flowforge import pipeline.yaml` — import YAML → DB

---

## Phase 8 — Frontend (Week 4–6)

### Setup
- [ ] Scaffold React + Vite + TypeScript in `frontend/`
- [ ] Apply design tokens from CLAUDE.md to tailwind.config.ts
- [ ] Set up React Query for all API calls
- [ ] Set up React Router for page navigation
- [ ] JWT auth: login page, token storage, API interceptor

### Dashboard Page
- [ ] Pipeline cards: name, status badge (with pulse animation for running), last run, next run, Run Now button
- [ ] Status badge colors: Success=green, Failed=red, Running=blue pulse, Never=gray
- [ ] Live polling: every 5s when any pipeline is `running`
- [ ] Global stats row: runs today, success rate, active schedules count
- [ ] Recent failures widget

### Pipeline Builder
- [ ] Pipeline list page — table with edit/delete/clone actions
- [ ] Pipeline edit page:
  - [ ] Basic info: name, description, enabled toggle
  - [ ] Visual cron builder → human readable + cron expression
  - [ ] Steps list with drag-to-reorder (dnd-kit)
  - [ ] Add step: type selector → type-specific config form
  - [ ] Step config forms:
    - [ ] `db_procedure`: connection picker, procedure name input, params key/value editor
    - [ ] `db_query`: connection picker, SQL editor (CodeMirror), output table, mode
    - [ ] `report`: report config picker dropdown (or "+ Create New")
    - [ ] `email`: email config picker dropdown (or "+ Create New")
    - [ ] `drive_upload`: file path input, folder picker, rename input
  - [ ] on_failure steps section (collapsible, same step editor)
  - [ ] on_error per step: stop/continue toggle
  - [ ] Save + Validate button

### Report Designer
- [ ] Report configs list
- [ ] Report edit page:
  - [ ] Name, description
  - [ ] Connection picker
  - [ ] SQL editor (CodeMirror 6 with SQL syntax + autocomplete)
  - [ ] Format selector: Excel / PDF / CSV
  - [ ] Excel: template file upload, sheet name input
  - [ ] Output filename input with variable chip hints
  - [ ] **Preview**: "Run Query" button → fetch first 20 rows → show in data table
  - [ ] Row count indicator

### Email Designer
- [ ] Email configs list
- [ ] Email edit page:
  - [ ] Name, description
  - [ ] Provider picker (Gmail / M365 / SMTP)
  - [ ] From name input
  - [ ] Recipients: group picker OR direct address input (chip input)
  - [ ] CC, BCC fields (chip input)
  - [ ] Subject input with variable chip hints
  - [ ] Header/banner text input
  - [ ] Body editor: toggle between rich editor and raw HTML + Jinja2
  - [ ] Smart attachment section:
    - [ ] Max size slider (1–50MB)
    - [ ] Drive folder picker (shows folder tree)
    - [ ] Drive share message editor (Jinja2 template)
  - [ ] **Preview**: renders email with sample variables → shows in modal iframe

### Recipient Groups
- [ ] Groups list
- [ ] Create/edit group: name, description, address chip input
- [ ] Show which email configs use each group

### Connections Manager
- [ ] DB Connections list + Email Providers list (tabbed)
- [ ] Add DB connection form: type selector → PostgreSQL or Oracle fields
- [ ] Add Email provider form: type selector → Gmail / M365 / SMTP fields
- [ ] Test button per connection → shows latency or error inline
- [ ] All credential fields masked (show/hide toggle)

### Run History
- [ ] Table: pipeline name, triggered by badge, started, duration, status badge
- [ ] Filters: pipeline, status, date range, triggered by
- [ ] Run detail page:
  - [ ] Step timeline: step name, type badge, status icon, duration bar, rows affected
  - [ ] Click step → expand logs panel (monospace, scrollable)
  - [ ] Drive URLs shown as clickable links
  - [ ] Email recipients shown as chips
  - [ ] Error highlighted in red with full message

### Settings Page
- [ ] OAuth setup: Gmail, Drive, Microsoft 365 — setup wizard buttons
- [ ] Default attachment threshold setting
- [ ] Default Drive folder setting
- [ ] Export/import pipeline YAML

---

## Phase 9 — Documentation & GitHub Release (Week 6–7)

### README.md Content
- [ ] Hero: what FlowForge is, one-line pitch
- [ ] Features list: DB procedures, multi-provider email, reports, Drive, smart attachments, scheduling, web UI
- [ ] Quick start (5 steps)
- [ ] Screenshot: dashboard + pipeline builder + email designer
- [ ] Comparison table: FlowForge vs Airflow vs Prefect vs cron+scripts
- [ ] Step types reference table
- [ ] Supported: PostgreSQL, Oracle | Gmail, M365, SMTP | Excel, PDF, CSV
- [ ] Installation: `pip install flowforge`
- [ ] Contributing + License

### docs/
- [ ] `getting-started.md` — install → first pipeline → schedule → view results
- [ ] `step-types.md` — full spec for each step type
- [ ] `email-providers.md` — Gmail OAuth2, Microsoft 365 MSAL, SMTP setup
- [ ] `database-connections.md` — PostgreSQL, Oracle (Instant Client requirement)
- [ ] `smart-attachments.md` — how Drive fallback works, how to configure
- [ ] `variables.md` — full variable reference
- [ ] `cli-reference.md` — all CLI commands

### Tests
- [ ] `test_runner.py` — step ordering, on_failure trigger, context passing
- [ ] `test_smart_attachments.py` — under limit → direct attach, over limit → Drive + link
- [ ] `test_email_providers.py` — mock Gmail, M365, SMTP send
- [ ] `test_connections.py` — mock PostgreSQL, Oracle connections
- [ ] `test_report_generators.py` — Excel/CSV output verification
- [ ] `test_crypto.py` — encrypt/decrypt round-trip
- [ ] GitHub Actions: run pytest on push

### GitHub
- [ ] Create public repo: `flowforge`
- [ ] Description: "Database-driven data pipeline orchestrator. DB procedures → reports → email (Gmail/M365/SMTP) → Google Drive. Smart attachments, scheduler, full web UI."
- [ ] Topics: `python`, `data-pipeline`, `etl`, `automation`, `reporting`, `postgresql`, `oracle`, `gmail`, `microsoft365`, `scheduler`, `google-drive`
- [ ] First release: v0.1.0

---

## Phase 10 — AI Analysis Step (v2, Post-Launch)

- [ ] `flowforge/steps/ai_analyze.py`
- [ ] Run query → fetch rows (cap 500 for context window safety)
- [ ] Format as markdown table
- [ ] Route to Ollama (default) or Claude API (opt-in via USE_CLAUDE)
- [ ] Store result in context as `output_variable`
- [ ] Available downstream via `{{ ai_summary }}` in email/report steps
- [ ] Frontend: ai_analyze step config form in Pipeline Builder
- [ ] Anomaly detection flag: `detect_anomalies: true`
- [ ] Report integration: Excel cell target for AI summary, PDF text block

---

## Backlog (Post v1)

### More Email Providers
- [ ] SendGrid API
- [ ] AWS SES
- [ ] Mailgun

### More Storage
- [ ] SFTP upload step
- [ ] AWS S3 upload step
- [ ] Azure Blob upload step
- [ ] OneDrive upload step (natural fit given M365 support)

### More DB Support
- [ ] MySQL / MariaDB connection
- [ ] MSSQL / SQL Server connection
- [ ] Generic ODBC connection

### Pipeline Features
- [ ] Pipeline dependencies (run B after A)
- [ ] Parallel step execution
- [ ] Step retry with exponential backoff
- [ ] Pipeline YAML import/export from UI

### Platform
- [ ] Docker image: `docker pull flowforge/flowforge`
- [ ] Multi-user auth with roles (v2)
- [ ] Plugin system for community step types

---

## Known Risks & Mitigations

| Risk | Mitigation |
|---|---|
| cx_Oracle requires Oracle Instant Client | Document clearly; make Oracle optional install: `pip install flowforge[oracle]` |
| M365 requires Azure AD app registration | Step-by-step guide in docs/email-providers.md; flowforge setup microsoft365 wizard |
| Gmail OAuth2 token expiry | MSAL-style refresh token handling; re-auth wizard in settings |
| Drive folder ID opaque to users | Folder picker in frontend fetches Drive tree via API |
| Smart attachment: Drive upload fails after report generated | Fallback: attach directly if Drive upload fails, log warning |
| Scrub misses internal references | Session Zero audit + Session 2 scrub + Session 4 final scan = 3 passes |
| Large report query times out in Preview | Preview uses `LIMIT 20` wrapper around user query |
| Oracle LOB columns break row serialization | OracleConnection reads LOB values explicitly before cursor close |
