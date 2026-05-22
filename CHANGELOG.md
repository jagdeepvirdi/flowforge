# Changelog

All notable changes to FlowForge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.5] — 2026-05-23

### Added

- **Pipeline variables UI** — New "Pipeline Variables" card in the Pipeline Builder between the Details section and the Steps list. Add any number of key/value pairs (plain or secret). Secret vars are masked as `***` in the UI and API; stored AES-256 encrypted in the database, decrypted at runtime. Both `{{ key }}` and `{{ vars.key }}` Jinja2 notation work in all step configs. `PUT /api/pipelines/:id` now accepts a `variables` array and performs a full replace (delete + re-create), so adds/removes/edits all work in a single save. ([`frontend/src/pages/PipelineEdit.tsx`](frontend/src/pages/PipelineEdit.tsx), [`flowforge/api/routes/pipelines.py`](flowforge/api/routes/pipelines.py))

- **Timestamp boundary built-ins** — Eight new Jinja2 variables in `YYYYMMDDHHmmSS` (14-digit) format for use directly in SQL `WHERE` clauses:

  | Variable | Value |
  |---|---|
  | `{{ day_start_ts }}` | Today 00:00:00 |
  | `{{ day_end_ts }}` | Today 23:59:59 |
  | `{{ yesterday_start_ts }}` | Yesterday 00:00:00 |
  | `{{ yesterday_end_ts }}` | Yesterday 23:59:59 |
  | `{{ month_start_ts }}` | First of month 00:00:00 |
  | `{{ month_end_ts }}` | Last of month 23:59:59 |
  | `{{ prev_month_start_ts }}` | First of previous month 00:00:00 |
  | `{{ prev_month_end_ts }}` | Last of previous month 23:59:59 |

  Also added `{{ prev_month_start }}` and `{{ prev_month_end }}` (YYYY-MM-DD format) to complement the existing `{{ month_start }}` / `{{ month_end }}` vars. ([`flowforge/engine/context.py`](flowforge/engine/context.py))

- **`{{ last_success_at }}` / `{{ last_success_date }}` delta variables** — Injected by the pipeline runner (not built-ins) immediately before each run. `last_success_at` contains the `YYYYMMDDHHmmSS` timestamp of the most recent successful run for this pipeline; `last_success_date` is the same in `YYYY-MM-DD` format. Both are empty strings when no successful run exists (first run). Use with a Jinja2 `{% if last_success_at %}` guard to build delta/incremental SQL queries that only extract data since the last run. ([`flowforge/engine/runner.py`](flowforge/engine/runner.py))

- **`create_if_missing` for `data_load` step** — New boolean config field. When `true`, FlowForge checks the target table's existence via catalog queries (`information_schema.tables` for PostgreSQL, `user_tables`/`all_tables` for Oracle) before loading. If the table does not exist it is created automatically with column types inferred from the data. Type priority: bool → int → float → timestamp → date → text. Supports both Python-typed values (query source) and string values (file source). Step log shows `(table auto-created)` on creation; subsequent runs skip the create silently. Catalog-based check avoids the PostgreSQL aborted-transaction state that a speculative `SELECT` would cause. ([`flowforge/steps/data_load.py`](flowforge/steps/data_load.py))

- **Type inference for auto-created tables** — `_infer_col_type()` maps values to appropriate SQL types per database:

  | Python / string | PostgreSQL | Oracle |
  |---|---|---|
  | bool / "true"/"false" | `BOOLEAN` | `NUMBER(1)` |
  | int / digit string | `BIGINT` | `NUMBER(18)` |
  | float / decimal string | `NUMERIC` | `NUMBER` |
  | datetime object / ISO timestamp string | `TIMESTAMP` | `TIMESTAMP` |
  | date object / YYYY-MM-DD string | `DATE` | `DATE` |
  | anything else / empty | `TEXT` | `VARCHAR2(4000)` |

  Samples up to 1,000 rows; column names are left unquoted so they match the INSERT statement on both databases. ([`flowforge/steps/data_load.py`](flowforge/steps/data_load.py))

- **`db_type` class attribute on connections** — `PostgreSQLConnection.db_type = 'postgresql'` and `OracleConnection.db_type = 'oracle'` allow step code to branch on database type without importing connection classes. ([`flowforge/connections/postgres.py`](flowforge/connections/postgres.py), [`flowforge/connections/oracle.py`](flowforge/connections/oracle.py))

- **`bulk_load` step** — New pipeline step type for directory-scan bulk loading. Scans a source directory for files matching an optional `file_prefix` / `file_prefix_exclude` pattern; strips configurable `header_rows` and `footer_rows`; loads via PostgreSQL `COPY FROM STDIN` (fast path) or chunked `executemany` (Python fallback for any DB). Supports `replace` (TRUNCATE + load) and `append` modes. Archives loaded files to a configurable `archive_directory` (supports `{{ current_date }}`). On no files: configurable `on_no_files` behaviour (`skip` succeeds silently, `fail` marks the step failed). Output variables: `files_found`, `files_loaded`, `files_failed`, `records_loaded`, `records_failed`. Bulk load configs are stored in the `ff_bulk_load_configs` table and referenced by step config (like `report_config_id`), managed via the **Bulk Loads** UI page. ([`flowforge/steps/bulk_load.py`](flowforge/steps/bulk_load.py), [`flowforge/api/routes/steps.py`](flowforge/api/routes/steps.py))

- **Bulk Loads UI page** — New sidebar nav item and page (`/bulk-loads`) for creating, editing, and deleting bulk load configs. Each config holds: connection, source directory, file type, prefix/exclude filter, header/footer rows, delimiter, target table, load mode, archive directory, column mapping, and `on_no_files` behaviour. ([`frontend/src/pages/BulkLoads.tsx`](frontend/src/pages/BulkLoads.tsx))

### Fixed

- **Test suite safety guard** — Running `pytest` against the live application database dropped all tables. Added a hard abort in `conftest.py` if `FLOWFORGE_DB_URL` does not contain `"test"` in the database name, preventing accidental data loss. Tests must target a dedicated `flowforge_test` database. ([`tests/conftest.py`](tests/conftest.py))

### Tests

- `tests/test_bulk_load_configs.py` — 13 tests for Bulk Load config API CRUD (create, read, update, delete, validation, defaults, column_mapping round-trip).
- `tests/test_bulk_load_step.py` — 29 tests for bulk_load step execution (validation, file scanning, prefix filtering, Python fallback replace/append modes, StepResult fields, archive, config resolution, runner context propagation).
- `tests/test_context.py` — 20 new tests for timestamp boundary vars (format, prefix cross-checks, Jinja2 renderability), `prev_month_start`/`end`, and confirmation that `last_success_at` is runner-injected (not a built-in).
- `tests/test_pipeline_variables.py` — 7 new tests for PUT variable replace semantics (add, remove, modify, clear all), `_get_last_success_ts` empty-on-first-run and correct-value-after-success.
- `tests/test_data_load_create.py` — 33 new tests for `_infer_col_type` (all type levels, both PostgreSQL and Oracle), `_table_exists` catalog queries (pg/oracle, with/without schema, exception handling), `_create_table` DDL generation (no double-quotes, type accuracy, 1,000-row sample cap), and end-to-end `create_if_missing` with mocked connection factory.

## [0.1.4] — 2026-05-22

### Fixed

- **Email provider `test()` missing** — The Test button on Connections always showed FAILED with `AttributeError` because `test()` was never implemented on any provider. Added `test()` to `EmailProvider` base class and all three providers: Gmail (token refresh), SMTP (connect + login with 10s timeout), Microsoft 365 (MSAL token acquisition). ([`flowforge/email_providers/base.py`](flowforge/email_providers/base.py), [`flowforge/email_providers/gmail.py`](flowforge/email_providers/gmail.py), [`flowforge/email_providers/smtp.py`](flowforge/email_providers/smtp.py), [`flowforge/email_providers/microsoft365.py`](flowforge/email_providers/microsoft365.py))
- **Gmail `test()` scope error** — Initial implementation called `users().getProfile()` which requires `gmail.readonly`, exceeding the `gmail.send` scope. Replaced with a token refresh call that works within the existing scope and confirms credentials are valid. ([`flowforge/email_providers/gmail.py`](flowforge/email_providers/gmail.py))
- **Test error message silently discarded in UI** — Email and DB provider test failures showed only "FAILED" with no detail. Error message from the API is now captured and displayed directly under the Failed badge. Browser console also receives a `console.error` log. ([`frontend/src/pages/Connections.tsx`](frontend/src/pages/Connections.tsx))
- **Quick-attach invalid Jinja2 for step names with spaces** — Quick-attach buttons generated `{{ steps.my step.output_path }}` which is invalid Jinja2 dot notation. Now uses bracket notation `{{ steps['my step'].output_path }}` when the step name contains spaces. Applies to both email and data_load forms. ([`frontend/src/components/pipeline/StepEditor.tsx`](frontend/src/components/pipeline/StepEditor.tsx))
- **Documentation links showed no content** — Settings page doc links pointed to `/docs/*.md` which nothing served. Added a Flask `/api/docs/<filename>` route that serves markdown files from the `docs/` directory as plain text; links updated to `/api/docs/` and open in a new tab. ([`flowforge/api/app.py`](flowforge/api/app.py), [`frontend/src/pages/Settings.tsx`](frontend/src/pages/Settings.tsx))
- **`data load` step button hidden in pipeline builder** — With 6 step type buttons in a row, `data load` overflowed off the right edge on narrower screens. Fixed by adding `flexWrap: wrap` to the button container. ([`frontend/src/pages/PipelineEdit.tsx`](frontend/src/pages/PipelineEdit.tsx))

### Added

- **UI screenshots** — 9 screenshots added to `docs/screenshots/`: dashboard, pipeline-builder, run-detail-steps, pipeline-run-now-success, scheduler-auto-run-history, scheduler-pipeline-disabled, connection-test-success, report-preview-rows, email-setup. ([`docs/screenshots/`](docs/screenshots/))

## [0.1.3] — 2026-05-22

### Added

- **Oracle 23c Free in Docker** — `gvenzl/oracle-free:23-slim` service added to `docker-compose.yml`. Docker project renamed to `flowforge-oracle`. App user `oracle` created automatically via `APP_USER` env var. Data persisted in `oracle_data` named volume. ([`docker-compose.yml`](docker-compose.yml))
- **`data_load` step type** — New pipeline step for bulk-loading data into any configured database connection (Oracle or PostgreSQL).
  - **File source** — reads CSV or Excel files; `file_path` supports Jinja2 variables (e.g. `{{ steps.generate_report.output_path }}`); format auto-detected from extension or set explicitly; optional `sheet_name` for Excel.
  - **SQL Query source** — executes a query on any configured source connection and loads the result set into the target; enables cross-database ETL without intermediate files.
  - **Target modes** — `replace` (TRUNCATE then bulk INSERT) and `append` (INSERT only).
  - **Chunked bulk insert** — configurable `chunk_size` (default 1000); PostgreSQL uses `psycopg2.extras.execute_batch` for true multi-row batching; Oracle uses positional bind vars (`:1, :2, ...`) via `oracledb.executemany`.
  - **Column mapping** — optional `column_map` JSON object to rename source columns to match target schema.
  - ([`flowforge/steps/data_load.py`](flowforge/steps/data_load.py), [`flowforge/connections/base.py`](flowforge/connections/base.py), [`flowforge/connections/postgres.py`](flowforge/connections/postgres.py), [`flowforge/connections/oracle.py`](flowforge/connections/oracle.py), [`flowforge/engine/loader.py`](flowforge/engine/loader.py), [`flowforge/api/routes/steps.py`](flowforge/api/routes/steps.py))
- **`data_load` pipeline builder form** — Source type toggle (File / SQL Query), quick-attach buttons for preceding report steps, target connection picker, table input with Jinja2 variable support, mode selector, and collapsible Advanced panel (chunk size + column map JSON editor). Amber `Load` badge added to the step type design system. ([`frontend/src/components/pipeline/StepEditor.tsx`](frontend/src/components/pipeline/StepEditor.tsx))
- **`execute_many` and `make_placeholders`** added to `BaseConnection` (abstract), `PostgreSQLConnection`, and `OracleConnection` — shared interface for the DataLoader bulk insert path.
- **`scripts/test_oracle.py`** — Smoke test script: waits for Oracle container readiness, prints version banner, exercises the full DataLoader path (`execute_many` + `make_placeholders`), verifies replace mode.

### Changed

- **Oracle driver: `cx_Oracle` → `python-oracledb`** — Migrated to the official successor driver. Thin mode enabled by default — pure Python, no Oracle Instant Client installation required. DSN format simplified to `host:port/service_name`. `pyproject.toml` and `requirements.txt` updated to `oracledb>=2.0`. ([`flowforge/connections/oracle.py`](flowforge/connections/oracle.py))

### Fixed

- **TypeScript TS6133 — unused imports in test files** — Removed unused `React`, `beforeEach`, and `vi` imports from `Dashboard.test.tsx`, `Pipelines.test.tsx`, and `TopBarSearch.test.tsx`. `npx tsc --noEmit` now exits with zero errors.

## [0.1.2] — 2026-05-22

### Fixed

- **Scheduler stale jobs** — Clearing or disabling a pipeline schedule in the UI had no effect; the old APScheduler job persisted in the PostgreSQL jobstore across restarts. `_load_pipeline_jobs()` only ever added jobs, never removed them. Replaced with `_sync_pipeline_jobs()` which diffs existing `pipeline_*` job IDs against the current active set and calls `remove_job()` for anything stale. Restart the scheduler once to flush any jobs orphaned before this fix. ([`flowforge/engine/scheduler.py`](flowforge/engine/scheduler.py))
- **Scheduler auto-sync** — Schedule changes made in the UI now apply within 60 seconds without restarting, via a new `_pipeline_sync` interval job that calls `_sync_pipeline_jobs()` every minute.
- **PowerShell `$PID` reserved variable** — `.\flowforge.ps1 stop` crashed with `Cannot overwrite variable PID because it is read-only or constant`. `$PID` is a read-only automatic variable in PowerShell. Renamed local variable to `$procId`. ([`flowforge.ps1`](flowforge.ps1))

### Added

- **Quick-attach report steps in email config** — When an email step has preceding report steps in the same pipeline, each report step appears as a one-click button above the attachments field, showing the step name and the output filename from its report config. Clicking inserts `{{ steps.<name>.output_path }}` automatically. Already-added steps show a green checkmark. Manual path entry still works as before. ([`frontend/src/components/pipeline/StepEditor.tsx`](frontend/src/components/pipeline/StepEditor.tsx))

### Changed

- **Email body template editor** — Height increased from 14 rows to 28 rows (420px minimum) in the Email Config editor. Still resizable. ([`frontend/src/pages/EmailEdit.tsx`](frontend/src/pages/EmailEdit.tsx))

## [0.1.1] — 2026-05-21

### Fixed

- **Scheduler critical bug** — Scheduled pipelines silently never fired. Root cause: APScheduler fires jobs in background threads, which have no Flask application context. `current_app` is a thread-local proxy and raises `RuntimeError: Working outside of application context` when accessed from a worker thread. The exception was swallowed by the outer `except Exception` handler, so no error was visible. Fixed by storing the Flask `app` object at module level in `scheduler.py` (bypasses pickling and thread-locality constraints) and pushing a fresh app context per job run with `with _app.app_context()`. ([`flowforge/engine/scheduler.py`](flowforge/engine/scheduler.py))
- **CLI schedule command** — Removed erroneous `with app.app_context()` wrapper from the `schedule` CLI command; `start_scheduler()` now takes the `app` object directly and manages its own context lifetime. ([`flowforge/cli.py`](flowforge/cli.py))
- **Login failure** — Fixed `FLOWFORGE_USERNAME` typo in `.env` (`testadmind` → `testadmin`).

### Added

- **JSON report format** — New `json` output option in the Report Designer generates a JSON array of objects (one per row, column names as keys). Added across: `flowforge/reports/json_report.py`, `flowforge/steps/report.py`, `flowforge/api/routes/reports.py`, `flowforge/db/models.py`. Alembic migration `0004_json_report_format.py` drops and recreates the `ck_report_format` check constraint.
- **Dashboard next run time** — Pipeline cards now show when the next scheduled run will fire (e.g. "in 23 min", "tomorrow at 02:00"). Computed server-side using `APScheduler.CronTrigger.from_crontab()` and returned as `next_run` in the pipeline API response.
- **Scheduler auto-start in startup scripts** — `flowforge.ps1` and `flowforge.sh` now start the scheduler alongside the API and UI. In dev mode all three run in parallel with `[api]`, `[sched]`, and `[ui]` log prefixes; Ctrl+C stops all three. The `stop` action also terminates the scheduler process.
- **Scheduler diagnostic script** — `check_scheduler.py` at the project root runs a 7-step end-to-end diagnostic (env vars → DB → pipeline discovery → worker-thread context → direct job fire → run history → APScheduler job registration). Run with `python check_scheduler.py`.

### Changed

- **Report Designer** — Selecting a format (Excel/CSV/PDF/JSON) now automatically updates the output filename extension to match.
- **Pipelines list** — Schedule column now shows a human-readable description (e.g. "Every hour", "Daily at 02:00") with the raw cron expression below it; unscheduled pipelines show "Manual only". Status column now shows a green "Active" badge for enabled pipelines instead of a plain Yes/No text column.
- **CronBuilder label** — Hourly frequency label corrected from the confusing "at minute N" to "at :N each hour".

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

[Unreleased]: https://github.com/jagdeepvirdi/flowforge/compare/v0.1.4...HEAD
[0.1.4]: https://github.com/jagdeepvirdi/flowforge/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/jagdeepvirdi/flowforge/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/jagdeepvirdi/flowforge/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/jagdeepvirdi/flowforge/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/jagdeepvirdi/flowforge/releases/tag/v0.1.0
