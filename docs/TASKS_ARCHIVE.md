# TASKS_ARCHIVE.md — FlowForge
*Completed tasks moved here from TASKS.md. Ordered newest-first.*

---

## Session — 2026-05-24 (Score 8.5+ Track, Tests complete) 🟢 *(COMPLETE)*

### Score 8.5+ Track — Tests

- [x] **[SCORE-6] Report generation end-to-end test** — `tests/test_report_e2e.py`: CSV + Excel full-chain tests against real test DB (SQL → ReportStep → file on disk), zero-rows edge case, output_path validation. *Tests +0.5.*
- [x] **[SCORE-11] Bulk load step tests** — Already complete: `tests/test_bulk_load_step.py` (27 tests) + `tests/test_bulk_load_configs.py` (14 tests). Covers normal load, skip/fail on no files, footer stripping, replace mode, column mapping, archive, config resolution, runner context propagation. *Tests +0.5.*

---

## Session — 2026-05-24 (Score 8.5+ Track) 🟢 *(COMPLETE)*

### New Issues — Found in 2026-05-23 Review (all resolved)

- [x] **[NEW-1] Email preview modal** — API endpoint `GET /email-configs/{id}/preview` + preview button in `EmailEdit.tsx`. Documented in CLAUDE.md; never built. P0.
- [x] **[NEW-2] SMTP send timeout** — `smtplib.SMTP(host, port, timeout=30)` missing in `smtp.py`; slow servers block pipeline threads indefinitely. P1.
- [x] **[NEW-3] Audit log completeness** — `flowforge/audit.py` logs login and pipeline events but NOT config changes (connections, providers), email sends, or report exports. P1.
- [x] **[NEW-4] JWT token revocation** — stolen token valid 24h; add `jti` claim + server-side blocklist + `/auth/logout` endpoint. P1.
- [x] **[NEW-5] Table-name injection guard** — `db_query.py` and `bulk_load.py` interpolate `output_table` into raw SQL; validate against safe identifier regex `^[a-zA-Z_][a-zA-Z0-9_.]*$`. P1.
- [x] **[NEW-6] DB factory vs check constraint mismatch** — constraint allows `mysql`, `mssql`, `snowflake` but factory raises at runtime; either remove from constraint or implement. P2.
- [x] **[NEW-7] Index on `ff_pipeline_variables(pipeline_id)`** — full table scan on every pipeline run. P2.
- [x] **[NEW-8] Frontend E2E tests (Playwright)** — no coverage of the full login → create → run → history journey. P2.
- [x] **[NEW-9] Production deployment guide** — `wsgi.py` exists but no Gunicorn + Nginx setup documented. P2.
- [x] **[NEW-10] Webhook / API trigger** — `POST /pipelines/{id}/trigger?token=...` for external system integration. P2.

### Score 8.5+ Track — Frontend

- [x] **[SCORE-1] Loading skeletons** — added `<Sk />` shimmer component (`Skeleton.tsx`); shape-matched loading states on `Dashboard.tsx`, `RunHistory.tsx`, `PipelineEdit.tsx`, `Connections.tsx`, `BulkLoads.tsx`. *Frontend +1.0*
- [x] **[SCORE-2] React Hook Form + Zod migration** — migrated `EmailEdit.tsx` and `ReportEdit.tsx` to `useForm<Schema>()` + `zodResolver`; cross-field validation with `.refine()` on recipients; `Controller` for chip-input arrays; `isSubmitting` replaces `saving` state. *Frontend +0.5, Code Quality +0.5*
- [x] **[SCORE-3] CSS token variables** — added 7 new tokens to `index.css` (`--text-3`, `--failure-text`, `--success-text`, `--running-text`, `--accent-text`, `--bg-code`, `--surface-hover`); bulk-replaced all design-token hex strings across 23 TSX files; preserved raw hex in `DB_COLORS` (template-literal alpha-suffix) and `PROJECT_COLORS` (DB-stored, equality-compared). *Frontend +0.5*
- [x] **[SCORE-10] React error boundaries** — enhanced `RouteErrorBoundary` with `componentDidCatch` logging, `label` prop, collapsible stack-trace detail, "Reload page" + "Try again" buttons; global boundary in `main.tsx`; step-editor boundary in `PipelineEdit.tsx` around `<DndContext>`. *Frontend +0.5, Architecture +0.25*

### Score 8.5+ Track — DevOps

- [x] **[SCORE-4] Log rotation for `audit.log`** — replaced `FileHandler` with `RotatingFileHandler(10 MB, 5 backups, utf-8)`; `LOG_LEVEL` env var controls verbosity in `audit.py`, `cli.py`, and `create_app()`; documented in `.env.example`. *DevOps +0.5*
- [x] **[SCORE-5] Fix `alembic.ini` hardcoded database URL** — `sqlalchemy.url` was already absent from baseline; added explanatory comment block to `alembic.ini`; removed silent `flowforge:flowforge` fallback from `env.py` `_db_url()` — now raises `RuntimeError` with actionable message if `FLOWFORGE_DB_URL` is unset. *DevOps +0.5*

### Score 8.5+ Track — Architecture

- [x] **[SCORE-7] Graceful shutdown — drain in-flight pipeline runs** — new `flowforge/engine/shutdown.py`: active-run registry (`register_run`/`unregister_run`), `_drain(timeout)` polling loop, `_cancel_stuck_runs()` DB UPDATE, `install_handler(app)` SIGTERM handler + `atexit` hook, `graceful_exit(app)` for Ctrl+C path. Integrated into `runner.py` (try/finally), `cli.py` `web` and `schedule` commands. `TimeoutStopSec=90` added to both systemd units in `deployment.md`. `FLOWFORGE_SHUTDOWN_TIMEOUT=60` in `.env.example`. *Architecture +0.5*

### Score 8.5+ Track — Database

- [x] **[SCORE-8] Deleted-pipeline run history visibility** — `ff_pipeline_runs.pipeline_id` FK was already `ON DELETE SET NULL` in baseline (no migration needed); `PipelineRun.pipeline_id` typed as `string | null` in `types.ts`; "Deleted pipelines" filter option added to `RunHistory.tsx` (client-side `__deleted__` sentinel, suppressed from API query); `(deleted)` badge shown inline when `pipeline_id === null`. *Database +0.5*

### Pipeline Features (shipped 2026-05-23)

- [x] **Pipeline variables** — Variables card in Pipeline Builder; key/value/secret pairs; `{{ var_key }}` and `{{ vars.var_key }}` in all step configs; secrets encrypted at rest and masked in UI.
- [x] **Bulk file loader step (`bulk_load`)** — Directory scanning, `file_prefix`/`file_prefix_exclude`, PostgreSQL `COPY FROM STDIN`, chunked Python fallback, footer row stripping, archive-after-load, `on_no_files` behaviour, Bulk Loads UI page.

---

## Session — 2026-05-23 (v1.0.0) 🟢 *(COMPLETE)*

### Multi-Project Support

**Goal:** Organize all FlowForge resources (pipelines, reports, email configs, recipient groups) into named projects — so teams can manage Finance, HR, Marketing Ops, etc. in one FlowForge instance without everything living in a flat list.

**Design decisions:**
- `db_connections` and `email_providers` stay **global** — infrastructure configured once, shared across projects
- A **"Default"** project is seeded on migration — all existing rows assigned to it, zero data loss
- Project switcher lives in the topbar beside the breadcrumb (moved from sidebar 2026-05-23)
- "All Projects" admin view for cross-project run history

#### Phase 1 — Database & Backend
- [x] `flowforge/db/models.py` — add `Project` model: `id`, `name`, `description`, `color`, `created_at`
- [x] `flowforge/db/models.py` — add `project_id` FK (nullable → non-null after backfill) to `Pipeline`, `ReportConfig`, `EmailConfig`, `RecipientGroup`
- [x] `flowforge/db/migrations/` — Alembic migration `0006_projects.py`: create `projects` table, add `project_id` columns, seed "Default" project, backfill all existing rows
- [x] `flowforge/api/routes/projects.py` — CRUD endpoints: `GET /projects`, `POST /projects`, `PATCH /projects/:id`, `DELETE /projects/:id`
- [x] All existing list/get routes — filter by `project_id` query param (e.g. `GET /pipelines?project_id=...`)
- [x] `flowforge/api/routes/runs.py` — "All Projects" run history: `GET /runs` with optional `project_id` filter

#### Phase 2 — Frontend: Project Switcher & Projects Page
- [x] `frontend/src/components/shared/ProjectSwitcher.tsx` — dropdown: current project name, list of all projects, "All Projects" link, "+ New Project" action; compact prop for topbar use
- [x] `frontend/src/lib/store.ts` (Zustand) — add `activeProjectId` global state; persisted to `localStorage`
- [x] `frontend/src/pages/Projects.tsx` — projects list as cards: name, color tag, pipeline count, last run status; create/edit/delete actions
- [x] `frontend/src/lib/api.ts` — pass `project_id` on all scoped API calls (pipelines, reports, email, recipients)

#### Phase 3 — Frontend: Scoped Pages & All Projects View
- [x] `frontend/src/pages/Dashboard.tsx` — scope pipeline cards to active project; show project name in header
- [x] `frontend/src/pages/PipelineEdit.tsx` — set `project_id` on create
- [x] `frontend/src/pages/ReportEdit.tsx` — scope to active project on create
- [x] `frontend/src/pages/EmailEdit.tsx` — scope to active project on create; recipient groups filtered by project
- [x] `frontend/src/pages/Recipients.tsx` — scope to active project on list and create
- [x] `frontend/src/pages/RunHistory.tsx` — scope to active project by default; pipeline filter list scoped to active project

#### Phase 4 — Tests & Migration Safety
- [x] `tests/test_projects.py` — CRUD for projects; confirm resources are correctly scoped per project
- [x] `tests/test_projects.py` — confirm pipelines/groups created without `project_id` are assigned to Default project
- [x] `tests/test_projects.py` — confirm `GET /pipelines?project_id=X` returns only X's pipelines, not cross-project leakage
- [x] Manual migration test: N/A — DB is clean (no pre-existing data to backfill)

---

### Query Results in Email (`db_query` → `email` data display)

**Goal:** When a `db_query` step runs (e.g. a post-load audit query returning success/fail counts), subsequent `email` steps can display those results inside the email body — without the user writing raw Jinja2.

**How it works end-to-end:**
1. User ticks **"Capture rows for email"** on the `db_query` step config and sets a row limit (default 100).
2. The step runner stores the result rows in `context['steps']['step_name']['rows']` (list-of-dicts) and pre-renders a styled `context['steps']['step_name']['table_html']` string.
3. In the email body editor, a new **"Insert step data"** button lists all `db_query` steps in the pipeline that have capture enabled. User picks one and a display format → the correct Jinja2 snippet is inserted into the body.
4. Email renders: `{{ steps.load_check.table_html }}` expands to an HTML table inside the sent email.

**Display format presets:**
| Preset | Variable inserted | Output |
|---|---|---|
| HTML table | `{{ steps.NAME.table_html }}` | Styled `<table>` with all columns |
| Key-value list | `{{ steps.NAME.kv_html }}` | `<dl>` — first row as label:value pairs (good for single-row summaries) |
| Counts only | `{{ steps.NAME.rows_affected }}` | Plain number — same as existing `rows_affected` |
| Custom Jinja2 | `{% for row in steps.NAME.rows %}{{ row.status }}: {{ row.count }}<br>{% endfor %}` | User writes own markup with column-name access |

**No migration required** — `capture_rows` and `row_limit` are stored in `pipeline_steps.config` JSONB; `table_html`/`kv_html` live only in the in-memory pipeline context.

#### Phase 1 — Backend Core
- [x] `flowforge/steps/base.py` — add `rows: list[dict]`, `table_html: str`, `kv_html: str` fields to `StepResult`
- [x] `flowforge/steps/db_query.py` — read `capture_rows: bool` (default `False`) and `row_limit: int` (default 100) from step config
- [x] `flowforge/steps/db_query.py` — implement `table_html` renderer: inline-styled `<table>` (no external CSS, email-client safe), HTML-escaped
- [x] `flowforge/steps/db_query.py` — implement `kv_html` renderer: `<dl>` from first row only (single-row summary queries), HTML-escaped
- [x] `flowforge/steps/db_query.py` — when `capture_rows=True`, use `execute_query_with_columns`, zip into list-of-dicts, store rows + rendered HTML in StepResult
- [x] `flowforge/engine/runner.py` — add `'rows'`, `'table_html'`, `'kv_html'` to `context['steps'][step.name]` (same pattern as `files_found` etc.)

#### Phase 2 — Frontend: Step Config
- [x] `frontend/src/components/pipeline/StepEditor.tsx` — add **"Capture rows for email"** toggle (`capture_rows`) to the `db_query` form
- [x] `frontend/src/components/pipeline/StepEditor.tsx` — show **"Row limit"** number input (1–1000, default 100) when toggle is on
- [x] `frontend/src/components/pipeline/StepEditor.tsx` — add hint text showing the exact `{{ steps.NAME.table_html }}` snippet for the step name

#### Phase 3 — Frontend: Email Designer
- [x] `frontend/src/components/pipeline/StepEditor.tsx` — email step shows **"Query data"** section listing upstream `db_query` steps with `capture_rows=true`, with copyable snippets for `table_html`, `kv_html`, and custom loop
- [x] `frontend/src/pages/EmailEdit.tsx` — added `{{ steps.step_name.table_html }}`, `{{ steps.step_name.kv_html }}`, and `{% for row in steps.step_name.rows %}` to the Available Variables reference card

#### Phase 4 — Help Content & Tests
- [x] `frontend/src/lib/helpContent.ts` — added `capture_rows` / `row_limit` hints to `db_query` step tips
- [x] `frontend/src/lib/helpContent.ts` — added embed-query-data hint to `email` step tips
- [x] `tests/test_db_query_capture.py` — `capture=True`: rows stored, HTML rendered, `row_limit` respected; `capture=False`: rows empty, no HTML rendered; HTML renderer unit tests incl. XSS escaping
- [x] `tests/test_runner.py` — assert `rows`, `table_html`, `kv_html` keys are in `context['steps']` for both capturing and non-capturing steps

---

## Session — 2026-05-22 (v0.1.4) 🟢 *(COMPLETE)*

### Bug Fixes
- [x] **Email provider `test()` missing** — `AttributeError` on every provider test. Added `test()` to base class and all three providers: Gmail (token refresh), SMTP (connect + login), M365 (MSAL token). (`flowforge/email_providers/base.py`, `gmail.py`, `smtp.py`, `microsoft365.py`)
- [x] **Gmail test scope error** — `getProfile` requires `gmail.readonly`, exceeding the `gmail.send` scope. Replaced with a token refresh call. (`flowforge/email_providers/gmail.py`)
- [x] **Test error message silently discarded** — Connections UI showed only "FAILED" with no detail. Error now captured and displayed under the Failed badge; also logged to browser console. (`frontend/src/pages/Connections.tsx`)
- [x] **Quick-attach invalid Jinja2 for step names with spaces** — Generated `{{ steps.my step.output_path }}` (invalid dot notation). Now uses `{{ steps['my step'].output_path }}` bracket notation for names with spaces. (`frontend/src/components/pipeline/StepEditor.tsx`)
- [x] **Documentation links showed no content** — Settings page links pointed to `/docs/*.md` which nothing served. Added Flask `/api/docs/<filename>` route; links updated to `/api/docs/` and open in new tab. (`flowforge/api/app.py`, `frontend/src/pages/Settings.tsx`)
- [x] **`data load` button hidden in pipeline builder** — 6 step-type buttons overflowed off the right edge. Fixed with `flexWrap: wrap`. (`frontend/src/pages/PipelineEdit.tsx`)

### Verified End-to-End
- [x] **Gmail email send verified** — Report → email pipeline ran successfully; email received with CSV attachment via Gmail OAuth2.

---

## Phase 4 — Polish & Release Prep 🔵 *(COMPLETE — 2026-05-22)*

- [x] **README screenshots** — Dashboard ✓, Run Detail ✓, Pipeline Builder ✓, Email Setup ✓, Scheduler Disabled ✓ *(all 9 in `docs/screenshots/`)*

---

## Phase 2 — Tests & Verification 🧪 *(COMPLETE — 2026-05-22)*

### End-to-End Pipeline Test
- [x] Create DB connection → Test → verify "Connected" *(screenshot: connection-test-success.png — Connected · 20ms)*
- [x] Create report config with simple `SELECT` → Preview → verify rows appear *(screenshot: report-preview-rows.png — 9 rows)*
- [x] Create pipeline with one `report` step → Run Now → check Run History *(screenshot: pipeline-run-now-success.png — 20 runs, 0 failed)*
- [x] Add `email` step after report → run → verify email received *(Gmail OAuth2 verified end-to-end)*
- [x] Verify `{{ current_month }}` resolves in output filename *(screenshot: run-detail-steps.png)*
- [x] Verify `StepResult.output_path` flows from report step *(screenshot: run-detail-steps.png)*
- [x] Verify `rows_affected` written to `ff_step_runs` *(screenshot: run-detail-steps.png)*

### Scheduler Smoke Test
- [x] Create pipeline with scheduled run → start scheduler → verify auto-run in history *(screenshot: scheduler-auto-run-history.png — 19 scheduler-triggered runs)*
- [x] Disable pipeline → verify no more runs triggered *(screenshot: scheduler-pipeline-disabled.png)*

---

## Session — 2026-05-22 🟢 *(COMPLETE)*

### Infrastructure
- [x] **Oracle 23c Free in Docker** — Added `gvenzl/oracle-free:23-slim` service to `docker-compose.yml` with `APP_USER: oracle` / `APP_USER_PASSWORD loaded from `.env`.`. Docker project renamed to `flowforge-oracle`. Data persisted in `oracle_data` volume. (`docker-compose.yml`)
- [x] **Oracle driver upgrade: `cx_Oracle` → `python-oracledb`** — Replaced deprecated driver with `python-oracledb` (thin mode — pure Python, no Oracle Instant Client required). Updated `pyproject.toml`, `requirements.txt`, and `flowforge/connections/oracle.py`. (`flowforge/connections/oracle.py`)
- [x] **`credentials.local.md`** — Local dev credentials file for PostgreSQL and Oracle (gitignored, never committed). (`credentials.local.md`, `.gitignore`)

### Features Added
- [x] **DataLoader step (`data_load`)** — New pipeline step type for bulk-loading data into any configured DB connection (Oracle or PostgreSQL).
  - Source types: `file` (CSV / Excel, supports `{{ steps.prev.output_path }}`) and `query` (SQL on any source connection — cross-DB ETL)
  - Target modes: `replace` (TRUNCATE + bulk INSERT) and `append`
  - PostgreSQL target uses `psycopg2.extras.execute_batch` for true bulk performance
  - Oracle target uses positional bind vars (`:1, :2, ...`) via `oracledb.executemany`
  - Chunked inserts with configurable `chunk_size` (default 1000)
  - Optional `column_map` to rename source → target columns
  - (`flowforge/steps/data_load.py`, `flowforge/connections/base.py`, `flowforge/connections/postgres.py`, `flowforge/connections/oracle.py`, `flowforge/engine/loader.py`, `flowforge/api/routes/steps.py`)
- [x] **DataLoader frontend form** — `DataLoadForm` component in `StepEditor.tsx`:
  - Source type toggle (File / SQL Query)
  - File source: quick-attach buttons from preceding report steps, file_path input, format picker, optional sheet name
  - Query source: source connection picker + SQL textarea
  - Target section: connection picker, table input (Jinja2 vars), mode selector
  - Advanced panel (collapsible): chunk size + column map JSON editor
  - Amber `Load` badge (`.tbadge-load`) added to design system
  - (`frontend/src/components/pipeline/StepEditor.tsx`, `frontend/src/pages/PipelineEdit.tsx`, `frontend/src/lib/types.ts`, `frontend/src/lib/helpContent.ts`, `frontend/src/index.css`)

### Bug Fixes
- [x] **TypeScript TS6133 errors in test files** — Removed unused `React`, `beforeEach`, and `vi` imports from `Dashboard.test.tsx`, `Pipelines.test.tsx`, and `TopBarSearch.test.tsx`. `npx tsc --noEmit` now exits clean. (`frontend/src/__tests__/`)

### Scripts
- [x] **`scripts/test_oracle.py`** — Oracle connection + DataLoader smoke test: waits for container readiness, prints Oracle version banner, exercises `execute_many` + `make_placeholders` via `OracleConnection`, verifies replace mode.

---

## Session — 2026-05-21 / 2026-05-22 🟢 *(COMPLETE)*

### Bug Fixes
- [x] **Scheduler stale job bug** — `_load_pipeline_jobs()` only added jobs, never removed them. Clearing or disabling a pipeline schedule in the UI had no effect; the old job persisted in the PostgreSQL jobstore across restarts. Fixed by replacing with `_sync_pipeline_jobs()` which diffs existing vs active job IDs and calls `remove_job()` for stale entries. Added a `_pipeline_sync` interval job (every 60s) so schedule changes apply automatically without restarting. (`flowforge/engine/scheduler.py`)
- [x] **Scheduler thread-context bug** — APScheduler worker threads had no Flask app context; `current_app` raised `RuntimeError`. Fixed by storing `app` at module level and pushing context per job run. (`flowforge/engine/scheduler.py`, `flowforge/cli.py`)
- [x] **PowerShell `$PID` reserved variable** — `.\flowforge.ps1 stop` crashed with "Cannot overwrite variable PID because it is read-only or constant". Renamed local variable to `$procId`. (`flowforge.ps1`)

### Features Added
- [x] **JSON report format** — New output format in Report Designer: generates a JSON array of objects (one per row). Alembic migration `0004_json_report_format.py` applied. (`flowforge/reports/json_report.py`, `flowforge/steps/report.py`, `flowforge/api/routes/reports.py`, `flowforge/db/models.py`)
- [x] **Dashboard next run time** — Pipeline cards show when the next scheduled run fires, computed server-side via APScheduler `CronTrigger.from_crontab()`. (`flowforge/api/routes/pipelines.py`, `frontend/src/pages/Dashboard.tsx`)
- [x] **Startup scripts auto-start scheduler** — `flowforge.ps1` and `flowforge.sh` now start API + scheduler + UI together. `[sched]` log prefix. Stop action kills all three. (`flowforge.ps1`, `flowforge.sh`)
- [x] **Scheduler diagnostic script** — `check_scheduler.py` — 7-step end-to-end diagnostic (env → DB → pipelines → thread context → direct fire → run history → job registration).
- [x] **Quick-attach report steps in email config** — When an email step has preceding report steps in the same pipeline, they appear as one-click buttons showing step name + output filename. Clicking inserts `{{ steps.<name>.output_path }}` automatically; already-added steps show green checkmark. (`frontend/src/components/pipeline/StepEditor.tsx`)
- [x] **Email body template size increase** — `rows={14}` → `rows={28}`, `minHeight: 420px`. (`frontend/src/pages/EmailEdit.tsx`)

### UI Improvements
- [x] **Report Designer format auto-extension** — Selecting a format now automatically updates the output filename extension.
- [x] **Pipelines list schedule column** — Shows human-readable cron description + raw expression; "Manual only" for unscheduled.
- [x] **Pipelines list status column** — Green "Active" badge for enabled pipelines.
- [x] **CronBuilder hourly label** — Fixed confusing "at minute N" → "at :N each hour".

### Documentation
- [x] `docs/running-the-server.md` — scheduler as third process, updated mode descriptions, stop behaviour, troubleshooting rows
- [x] `docs/getting-started.md` — startup script as recommended path, JSON format mention, Scheduler Diagnostics section
- [x] `docs/step-types.md` — JSON added to report format options
- [x] `RUNBOOK.md` — all-in-one startup section, scheduler troubleshooting table (section 4a)
- [x] `CHANGELOG.md` — v0.1.1 and v0.1.2 entries

### Manual Testing (Phase 2)
- [x] DB connection test — Connected · 20ms (`docs/screenshots/connection-test-success.png`)
- [x] Report preview rows — 9 rows (`docs/screenshots/report-preview-rows.png`)
- [x] Pipeline Run Now → success in Run History (`docs/screenshots/pipeline-run-now-success.png`)
- [x] Run detail step timeline + output path + rows_affected (`docs/screenshots/run-detail-steps.png`)
- [x] Scheduler auto-trigger — 19 runs with `triggered_by=scheduler` (`docs/screenshots/scheduler-auto-run-history.png`)
- [x] Dashboard README screenshot (`docs/screenshots/dashboard.png`)

---

## Phase 9 — Frontend Quality 🟢 *(COMPLETE — 2026-05-20)*
*Addresses FE findings. Target score: Frontend 5.5 → 7.0*

- [x] **[FE-1] Add form validation** — `fieldErrors` state added to PipelineEdit, ReportEdit, EmailEdit; inline errors shown under Name, Subject, Query, Recipients, Timeout fields; errors clear on field edit. Zod/react-hook-form already installed.
- [x] **[FE-2] Add React error boundaries** — `RouteErrorBoundary` class component created; wraps `<Outlet />` in `Layout.tsx`; shows friendly card with "Try again" button on render errors.
- [x] **[FE-3] Fix `any` types in TopBar search** — `any[]` replaced with `Pipeline[]`, `ReportConfig[]`, `EmailConfig[]` from `lib/types.ts`.
- [x] **[FE-4] Show search hint when cache is empty** — when all caches empty and query has text, shows "Visit Pipelines and Reports pages first to populate search"; shows "No results" only when caches are populated but nothing matches. Test updated (14/14 passing).
- [x] **[FE-5] Migrate hardcoded hex colors to CSS tokens** — replaced `#F97316` → `var(--accent)`, `#1A1D27` → `var(--surface)`, `#21252F` → `var(--surface-2)`, `#2D3143` → `var(--border)`, `#F1F5F9` → `var(--text)`, `#64748B` → `var(--text-muted)`, `#475569` → `var(--text-dim)`, `#CBD5E1` → `var(--text-2)`, `#0F1117` → `var(--bg)`, `#22C55E` → `var(--success)`, `#FB923C` → `var(--accent-h)` across TopBar, Layout, PipelineEdit, ReportEdit, EmailEdit, RunHistory, Connections.
- [x] **[FE-6] Add pagination** — backend `GET /runs` now accepts `offset` param; `getRuns()` in api.ts updated; RunHistory defaults to 50 rows, "Load more" button adds 50 each click, limit resets when filters change, `keepPreviousData` prevents flicker.
- [x] **[FE-7] Fix TopBar blur handler** — replaced `setTimeout(..., 150)` with `containerRef` wrapping the search area; `onBlur` uses `relatedTarget.contains()` so dropdown stays open when tabbing to results; result divs have `tabIndex={-1}`.

---

## Phase 8 — Test Coverage *(COMPLETE — 2026-05-20)*
*Addresses TEST findings. Target score: Tests 6.0 → 7.5*

- **[TEST-2] Fix false-green test** — added `assert result.success is False` to `test_on_error_continue_pipeline_still_fails` in `test_runner.py`.
- **[TEST-3a] Test smart attachment logic** — already fully covered by `test_smart_attachments.py` (direct, Drive upload, missing file). No new tests needed.
- **[TEST-3b] Test Jinja2 rendering errors** — `tests/test_jinja_errors.py` added: `render()` raises `TemplateSyntaxError` on `{{ unclosed`; runner catches it and produces `StepResult(success=False)`; on_error=continue continues past the bad step.
- **[TEST-3c] Test cron validation endpoint** — `tests/test_cron_endpoint.py` added: 12 tests covering valid expressions, n parameter, results ordering, ISO-8601 format, missing expr, invalid expr, out-of-range field, and auth guard.
- **[TEST-3d] Test pipeline variable secret masking** — already fully covered by `test_pipeline_variables.py` (`test_secret_var_masked_in_api_response`, `test_secret_var_not_leaked_by_update`). No new tests needed.
- **[TEST-3e] Test encryption/decryption round-trip** — two tests added to `test_connections.py`: API masks password as `***`; raw DB column does not contain plaintext; `decrypt_config()` recovers original value. Also fixed stale `test_create_connection_bad_type` (was testing `mysql` which is now valid — changed to `sqlite`). Updated `connections.py` route to accept the 5 valid types.
- **[TEST-4] Add frontend tests** — Vitest + @testing-library/react installed; `vitest.config.ts` added; 13 tests in 3 files: `Dashboard.test.tsx` (5 tests), `Pipelines.test.tsx` (3 tests), `TopBarSearch.test.tsx` (5 tests — seeded React Query cache, Escape to clear, report search). All 13 pass.

---

## Phase 7 — Code Quality *(COMPLETE — 2026-05-20)*
*Addresses CODE + DB findings. Target score: Code Quality 6.0 → 7.5, Database 6.5 → 8.0*

- **[CODE-1] Fix silent exception swallowing in `runner.py` DB helpers** — `except Exception: return None` replaced with `except SQLAlchemyError as e: logger.error(...)` in all three helpers; `SQLAlchemyError` imported at module level.
- **[CODE-2] Replace class-name string manipulation for `step_type`** — `step_type: str = ''` added to `BaseStep`; each concrete step sets its own value; `_write_step_run` uses `step.step_type` with the string-hack as fallback.
- **[CODE-3] Protect built-in context variables from `output_variables` overwrite** — before `context.update(...)`, collision check against `_CONTEXT_META_KEYS`; conflicting keys logged and skipped; safe keys propagated normally.
- **[CODE-4] Fix `_utcnow()` timezone stripping** — `_utcnow()` returns `datetime.now(timezone.utc)` (no `.replace(tzinfo=None)`); all model `DateTime` columns changed to `DateTime(timezone=True)`; all call sites updated; migration `0002_timezone_timestamps.py` converts columns to TIMESTAMPTZ.
- **[DB-1] Fix step reordering constraint** — `PUT /pipeline-steps/<id>` uses two-phase swap: occupant moved to order 999999 → target step moved → occupant moved to original slot; no unique constraint violation.
- **[DB-2] Add performance indexes** — migration `0003_indexes_and_constraints.py` adds `ix_pipeline_runs_pipeline_started` on `(pipeline_id, started_at DESC)` and `ix_step_runs_pipeline_run` on `(pipeline_run_id)`.
- **[DB-3] Widen `DbConnection` check constraint** — `mysql`, `mssql`, `snowflake` added to constraint in both `models.py` and migration `0003`; old constraint dropped and recreated.

---

## Phase 6 — Reliability & Production Readiness *(COMPLETE — 2026-05-20)*
*Addresses ARCH + OPS findings. Target score: Architecture 6.5 → 8.0, DevOps 6.0 → 7.5*

- **[ARCH-1a] Add concurrency limit to pipeline execution** — `FLOWFORGE_MAX_CONCURRENT_RUNS` env var (default 5); `threading.Semaphore` in `trigger_run`; excess runs rejected with HTTP 429; semaphore released in `finally` block.
- **[ARCH-1b] Enforce `timeout_minutes` in `runner.py`** — background thread uses `concurrent.futures.ThreadPoolExecutor`; `.result(timeout=...)` raises `TimeoutError`; run marked `failed` with `"Pipeline timed out"`.
- **[ARCH-1c] Sweep stuck `running` runs on startup** — `_sweep_stuck_runs()` called from `create_app()`; marks all `status='running'` rows as `failed` with `"Run interrupted by server restart"`; skips silently if table missing.
- **[ARCH-2] Add `scheduler` service to `docker-compose.yml`** — second service runs `flowforge schedule`; shares image + `output_files` volume; depends on `app: service_healthy`.
- **[ARCH-3] Fix stuck-run race condition in `trigger_run`** — `load_pipeline()` wrapped in `try/except`; on failure run record is set to `failed` and semaphore is released before returning 500.
- **[OPS-2] Add `healthcheck` to `app` service in `docker-compose.yml`** — `GET /api/health`; `interval: 15s`, `timeout: 5s`, `retries: 3`, `start_period: 30s`.
- **[OPS-3] Move `_seed_admin` out of `create_app()`** — `flowforge db seed` CLI command added; documented in getting-started.md; `_seed_admin` removed from app factory, replaced with `_sweep_stuck_runs`.

---

## Phase 5 — Security Fixes *(COMPLETE — 2026-05-20)*
*Addresses SEC findings from CODEBASE_REVIEW.md. Target score: Security 5.5 → 8.0*

- **[SEC-1] Remove hardcoded credentials from `tests/conftest.py`** — removed hardcoded password default; added `.env.test.example`; `sys.exit(1)` with clear message if `FLOWFORGE_DB_URL` not set; CI workflow already sets it.
- **[SEC-2] Split encryption key and JWT secret** — `FLOWFORGE_JWT_SECRET` introduced for JWT signing; `FLOWFORGE_SECRET_KEY` reserved for AES-256 only. Falls back with a `warnings.warn` if unset. Updated `app.py`, `auth.py`, `conftest.py`, `.env.example`, CI workflow.
- **[SEC-3] Fix rate limiter for proxied deployments** — added `werkzeug.middleware.proxy_fix.ProxyFix` controlled by `FLOWFORGE_TRUSTED_PROXIES` env var (default 0). When set ≥1, `get_remote_address` correctly resolves real client IP from `X-Forwarded-For`. Documented in `.env.example`.
- **[SEC-6] Require `FLOWFORGE_CORS_ORIGIN` in production** — logs a loud `WARNING` at startup if `FLASK_ENV=production` and var is unset. `http://localhost:5173` is now dev/test fallback only. Added `FLOWFORGE_CORS_ORIGIN` to `.env.example`.
- **[SEC-7] Add basic audit logging** — `flowforge/audit.py` writes to `logs/audit.log`. Login success/failure logged from `routes/auth.py` (with IP). Pipeline STARTED/SUCCESS/FAILED logged from `runner.py`.

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
