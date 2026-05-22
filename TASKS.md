# TASKS.md — FlowForge

*Completed tasks are in [TASKS_ARCHIVE.md](TASKS_ARCHIVE.md).*
*Full codebase review with scores in [CODEBASE_REVIEW.md](CODEBASE_REVIEW.md).*

---

## GitHub Release Score: 8.6 / 10 (updated 2026-05-22)
## Codebase Review Score: 6.0 / 10 (reviewed 2026-05-20 — see CODEBASE_REVIEW.md)

| Dimension | Score |
|---|---|
| Code quality | 7/10 — Clean architecture, good separation of concerns |
| Feature completeness | 9/10 — Scheduler sync, JSON format, quick-attach, all phase 9 items done |
| Security | 9/10 — Encryption, rate limiting, Alembic migrations all done |
| Documentation | 7/10 — All docs updated, scheduler runbook added, screenshots in progress |
| Deployment UX | 7/10 — Docker Compose + CI added |
| GitHub readiness | 9/10 — Startup scripts solid, scheduler reliable, UX improvements shipped |

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

## Session — 2026-05-22 🟢 *(COMPLETE)*

### Infrastructure
- [x] **Oracle 23c Free in Docker** — Added `gvenzl/oracle-free:23-slim` service to `docker-compose.yml` with `APP_USER: oracle` / `APP_USER_PASSWORD: harpal123`. Docker project renamed to `flowforge-oracle`. Data persisted in `oracle_data` volume. (`docker-compose.yml`)
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

## Remaining Work

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

## Phase 2 — Tests & Verification 🧪
*Automated test coverage + manual pre-launch smoke tests.*

### Manual Verification Checklist (do before launch)

#### End-to-End Pipeline Test
- [x] Create DB connection → Test → verify "Connected" *(screenshot: connection-test-success.png — Connected · 20ms)*
- [x] Create report config with simple `SELECT` → Preview → verify rows appear *(screenshot: report-preview-rows.png — 9 rows)*
- [x] Create pipeline with one `report` step → Run Now → check Run History *(screenshot: pipeline-run-now-success.png — 20 runs, 0 failed)*
- [ ] Add `email` step after report → run → verify email received
- [x] Verify `{{ current_month }}` resolves in output filename *(screenshot: run-detail-steps.png — RunBook_Report_2026-05_...csv visible)*
- [x] Verify `StepResult.output_path` flows from report step *(screenshot: run-detail-steps.png — output file and Download button visible)*
- [x] Verify `rows_affected` written to `ff_step_runs` *(screenshot: run-detail-steps.png — "Rows affected: 9" visible)*

#### Scheduler Smoke Test
- [x] Create pipeline with scheduled run → start scheduler → verify auto-run in history *(screenshot: scheduler-auto-run-history.png — 19 scheduler-triggered runs)*
- [ ] Disable pipeline → verify no more runs triggered

---

## Phase 4 — Polish & Release Prep 🔵
*Docs, GitHub presence, and final UX touches.*

- [ ] **README screenshots** — ~~Dashboard~~ ✓, ~~Run Detail~~ ✓, **Pipeline Builder still needed**. Highest-impact item for GitHub stars.

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
- [ ] **OneDrive / SharePoint upload step** — Graph API + MSAL (already installed via `[microsoft365]`). New `onedrive_upload` step type, extend smart attachment with `storage_provider` field (`google_drive` | `onedrive`). Deferred to post-core-stability. *User confirmed active need.*

### More DB Support
- [ ] MySQL / MariaDB
- [ ] MSSQL / SQL Server
- [ ] Generic ODBC

### Pipeline Features
- [ ] Pipeline dependencies (run B after A)
- [ ] Parallel step execution
- [ ] Step retry with exponential backoff
- [ ] Pipeline YAML import/export from UI
- [ ] **Pipeline run parameter UI** — A "Parameters" section on the pipeline edit page where you define named params and their computation rules (e.g., `week_start = start of current ISO week`, `week_end = end of current ISO week`). More flexible than built-in date vars; allows per-pipeline customization. Params become available as `{{ params.week_start }}` in all step configs. Pairs with the built-in smart date vars (ship those first).
- [ ] **Bulk file loader step (`bulk_load`)** — Advanced successor to `data_load`. Replaces the Oracle SQL\*Loader shell script at `github.com/jagdeepvirdi/DayToDayOfficeOperations`. Adds: directory scanning (`file_prefix`, `file_prefix_exclude`), Oracle SQL\*Loader direct-path via subprocess (fastest), PostgreSQL `COPY FROM STDIN`, footer row stripping, `.bad` file surfacing in logs, archive-after-load, `files_found`/`records_loaded`/`records_failed` output variables. Full spec below.

  **Step config (stored in `pipeline_steps.config` JSONB):**
  ```json
  {
    "connection_id": "uuid",
    "source_directory": "/data/incoming/",
    "file_prefix": "SUBS_",
    "file_prefix_exclude": null,
    "file_type": "csv",
    "delimiter": ",",
    "header_rows": 1,
    "footer_rows": 0,
    "target_table": "STAGING.SUBSCRIPTIONS",
    "load_mode": "append",
    "column_mapping": [],
    "use_sqlloader": true,
    "archive_directory": "/data/archive/{{ current_date }}/",
    "on_no_files": "skip"
  }
  ```

  **Execution — three internal paths:**
  1. **Oracle + `use_sqlloader: true`** — FlowForge generates a `.ctl` control file dynamically from the step config (delimiter, column mapping, date formats). Calls `sqlldr user/pass@dsn control=<tmp>.ctl log=<tmp>.log bad=<tmp>.bad` as a subprocess. Parses the `.log` file for "rows loaded" / "rows not loaded" counts. Surfaces `.bad` file content (rejected rows) in `step_runs.logs`. Fastest path — Oracle direct-path load, bypasses redo logging.
  2. **PostgreSQL** — Uses psycopg2 `cursor.copy_expert("COPY table FROM STDIN CSV HEADER", file)`. Equivalent speed to SQL\*Loader for Postgres. Parse `copy_expert` counts for loaded/rejected rows.
  3. **Python fallback** (any DB, or `use_sqlloader: false`)— Reads file in chunks of 10,000 rows, strips `header_rows` + `footer_rows`, inserts via `executemany()`. Slower but requires no external tooling.

  **Control file auto-generation (Oracle path):**
  FlowForge writes the `.ctl` to a temp directory — the user never touches it. Derives from: delimiter, `column_mapping`, any date-format hints on columns. After load: archive source files to `archive_directory`, delete temp `.ctl`/`.log`/`.bad`.

  **Step output variables (available in subsequent steps via `{{ steps.<name>.x }}`):**
  | Variable | Example |
  |---|---|
  | `files_found` | 3 |
  | `files_loaded` | 3 |
  | `files_failed` | 0 |
  | `records_loaded` | 147,832 |
  | `records_failed` | 14 |
  | `duration_sec` | 8.3 |

  Use these directly in an `email` step body to send a load confirmation — no new feature needed, standard pipeline step.

  **Run History tracking:**
  - `step_runs.rows_affected` = `records_loaded`
  - `step_runs.logs` = full load summary + first 50 rejected rows from `.bad` file

  **Code changes required:**
  - `flowforge/steps/bulk_load.py` — new step class
  - `flowforge/steps/base.py` — add `files_found`, `files_loaded`, `files_failed`, `records_loaded`, `records_failed`, `duration_sec` fields to `StepResult`
  - `flowforge/engine/context.py` — propagate new `StepResult` fields into pipeline context (same pattern as `output_path` and `drive_url`)
  - `frontend/src/components/pipeline/StepEditor.tsx` — add `bulk_load` step config panel
  - `frontend/src/lib/helpContent.ts` — add `bulk_load` to step hints
  - Alembic migration — add `bulk_load` to step type enum if constrained

  **Implementation order:** Python fallback first (works immediately, no Oracle client needed for dev/test) → PostgreSQL COPY → Oracle SQL\*Loader.

### Platform
- [ ] Multi-user auth with roles (v2)
- [ ] Plugin system for community step types
- [ ] Slack/Teams notifications (v2)
- [ ] AI analyze step — `flowforge/steps/ai_analyze.py`, Ollama/Claude routing, `{{ ai_summary }}` variable (v2)

---

## Known Risks & Mitigations

| Risk | Mitigation |
|---|---|
| ~~cx_Oracle requires Oracle Instant Client~~ | ✅ Resolved — migrated to `python-oracledb` (thin mode, pure Python, no Instant Client needed) |
| M365 requires Azure AD app registration | Step-by-step guide in docs/email-providers.md; flowforge setup microsoft365 wizard |
| Gmail OAuth2 token expiry | Refresh token handling; re-auth wizard in settings |
| Drive folder ID opaque to users | Folder picker in frontend fetches Drive tree via API |
| Smart attachment: Drive upload fails after report generated | Fallback: attach directly if Drive upload fails, log warning |
| Large report query times out in Preview | Preview uses `LIMIT 20` wrapper around user query |
| Oracle LOB columns break row serialization | OracleConnection reads LOB values explicitly before cursor close |
