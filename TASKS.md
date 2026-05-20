# TASKS.md — FlowForge

*Completed tasks are in [TASKS_ARCHIVE.md](TASKS_ARCHIVE.md).*
*Full codebase review with scores in [CODEBASE_REVIEW.md](CODEBASE_REVIEW.md).*

---

## GitHub Release Score: 8.2 / 10 (updated 2026-05-18)
## Codebase Review Score: 6.0 / 10 (reviewed 2026-05-20 — see CODEBASE_REVIEW.md)

| Dimension | Score |
|---|---|
| Code quality | 7/10 — Clean architecture, good separation of concerns |
| Feature completeness | 8/10 — Async, Docker, CI, M365 token refresh, YAML import all done |
| Security | 9/10 — Encryption, rate limiting, Alembic migrations all done |
| Documentation | 5/10 — Missing pages, no screenshots |
| Deployment UX | 7/10 — Docker Compose + CI added |
| GitHub readiness | 8/10 — Legacy removed, stubs fixed, deps corrected |

---

## Remaining Work

---

## Phase 5 — Security Fixes 🔴 *(P0 — fix before any public traffic)*
*Addresses SEC findings from CODEBASE_REVIEW.md. Target score: Security 5.5 → 8.0*

- [ ] **[SEC-1] Remove hardcoded credentials from `tests/conftest.py`** — replace `harpal123` default with `os.environ['FLOWFORGE_DB_URL']` (no default); add `.env.test.example`; update CI workflow to set the var explicitly.
- [ ] **[SEC-2] Split encryption key and JWT secret** — introduce `FLOWFORGE_JWT_SECRET` env var used only for JWT signing; keep `FLOWFORGE_SECRET_KEY` for AES-256 only. Update `app.py`, `auth.py`, `.env.example`, docs.
- [ ] **[SEC-3] Fix rate limiter for proxied deployments** — replace `get_remote_address` with `get_remote_address` + `app.config['RATELIMIT_HEADERS_ENABLED'] = True` and configure `ProxyFix` middleware; document `FLOWFORGE_TRUSTED_PROXIES` env var.
- [ ] **[SEC-6] Require `FLOWFORGE_CORS_ORIGIN` in production** — raise a startup error (or at minimum log a loud `WARNING`) if the var is not set and `FLASK_ENV=production`. Remove the `http://localhost:5173` default.
- [ ] **[SEC-7] Add basic audit logging** — log triggered-by, pipeline name, and outcome to a dedicated `logs/audit.log` file on every pipeline run and login attempt.

---

## Phase 6 — Reliability & Production Readiness 🟠
*Addresses ARCH + OPS findings. Target score: Architecture 6.5 → 8.0, DevOps 6.0 → 7.5*

- [ ] **[ARCH-1a] Add concurrency limit to pipeline execution** — introduce `FLOWFORGE_MAX_CONCURRENT_RUNS` env var (default 5); use a `threading.Semaphore` in `trigger_run` to reject excess runs with HTTP 429.
- [ ] **[ARCH-1b] Enforce `timeout_minutes` in `runner.py`** — run each pipeline in a `concurrent.futures.ThreadPoolExecutor` with a timeout; on timeout set run status to `failed` with `error_message = "Pipeline timed out"`.
- [ ] **[ARCH-1c] Sweep stuck `running` runs on startup** — on `create_app()`, query all `PipelineRun` rows with `status='running'` and set them to `failed` with `error_message = "Run interrupted by server restart"`.
- [ ] **[ARCH-2] Add `scheduler` service to `docker-compose.yml`** — add a second service that runs `flowforge schedule`; share the same image; mount the same `output_files` volume.
- [ ] **[ARCH-3] Fix stuck-run race condition in `trigger_run`** — wrap `load_pipeline()` call in `try/except`; on failure update the pre-created run record to `failed` before returning 500.
- [ ] **[OPS-2] Add `healthcheck` to `app` service in `docker-compose.yml`** — `GET /api/health` returns 200; configure `interval: 15s`, `timeout: 5s`, `retries: 3`.
- [ ] **[OPS-3] Move `_seed_admin` out of `create_app()`** — make it a `flowforge db seed` CLI command; document in getting-started.md; remove the DB query from the app factory.

---

## Phase 7 — Code Quality 🟡
*Addresses CODE + DB findings. Target score: Code Quality 6.0 → 7.5, Database 6.5 → 8.0*

- [ ] **[CODE-1] Fix silent exception swallowing in `runner.py` DB helpers** — change `except Exception: return None` to `except SQLAlchemyError as e: logger.error(...)` in `_create_run_record`, `_write_step_run`, `_finish_run_record`.
- [ ] **[CODE-2] Replace class-name string manipulation for `step_type`** — add `step_type: str` class attribute to `BaseStep`; set it in each concrete step class; use it in `_write_step_run`.
- [ ] **[CODE-3] Protect built-in context variables from `output_variables` overwrite** — before `context.update(step_result.output_variables)`, check for key collisions with `_CONTEXT_META_KEYS`; raise `RuntimeError` or log a warning and skip the conflicting key.
- [ ] **[CODE-4] Fix `_utcnow()` timezone stripping** — change to `datetime.now(timezone.utc)` (no `.replace(tzinfo=None)`); ensure all model columns use `DateTime(timezone=True)`; add Alembic migration for the column type change.
- [ ] **[DB-1] Fix step reordering constraint** — update the `PUT /pipeline-steps/<id>` route and the drag-to-reorder mutation to use a two-phase swap (set temp order → set target order) to avoid unique constraint violations.
- [ ] **[DB-2] Add performance indexes in a new Alembic migration** — `(pipeline_id, started_at DESC)` on `ff_pipeline_runs`; `(pipeline_run_id)` on `ff_step_runs`.
- [ ] **[DB-3] Widen `DbConnection` check constraint** — add `'mysql'`, `'snowflake'`, `'mssql'` to the check constraint (or remove it and validate at the application layer); add Alembic migration.

---

## Phase 8 — Test Coverage 🟡
*Addresses TEST findings. Target score: Tests 6.0 → 7.5*

- [ ] **[TEST-2] Fix false-green test** — `tests/test_runner.py:92`: add `assert result.success is False` to `test_on_error_continue_pipeline_still_fails`.
- [ ] **[TEST-3a] Test smart attachment logic** — unit test `_handle_attachments()`: file below threshold → direct, file above → Drive upload called, missing file → skipped with warning.
- [ ] **[TEST-3b] Test Jinja2 rendering errors** — test that a step with an invalid template string (`{{ unclosed`) fails gracefully with a `StepResult(success=False)` rather than crashing the runner.
- [ ] **[TEST-3c] Test cron validation endpoint** — `GET /api/pipelines/cron-next?expr=...` with valid, invalid, and edge-case expressions.
- [ ] **[TEST-3d] Test pipeline variable secret masking** — assert that `GET /api/pipelines/<id>` returns `var_value: "***"` for `is_secret=True` variables.
- [ ] **[TEST-3e] Test encryption/decryption round-trip through API** — create a DB connection via API, retrieve it, assert sensitive fields are masked; verify the stored value is not plaintext via direct DB query.
- [ ] **[TEST-4] Add frontend tests** — set up Vitest + React Testing Library; add smoke tests for Dashboard render, Pipelines list render, and TopBar search returning results from a seeded React Query cache.

---

## Phase 9 — Frontend Quality 🟢
*Addresses FE findings. Target score: Frontend 5.5 → 7.0*

- [ ] **[FE-1] Add form validation** — install `react-hook-form` + `zod`; add Zod schemas for Pipeline, ReportConfig, EmailConfig, DbConnection forms; show inline field errors instead of relying on API 400 responses.
- [ ] **[FE-2] Add React error boundaries** — wrap each route in a `<RouteErrorBoundary>` component that shows a friendly error card instead of a blank screen.
- [ ] **[FE-3] Fix `any` types in TopBar search** — replace `any[]` with `Pipeline[]`, `ReportConfig[]`, `EmailConfig[]` from `lib/types.ts`.
- [ ] **[FE-4] Show search hint when cache is empty** — when the query has text but results are empty, show "Visit Pipelines and Reports pages first to populate search" instead of just "No results".
- [ ] **[FE-5] Migrate hardcoded hex colors to CSS tokens** — replace `#F97316` → `var(--accent)`, `#1A1D27` → `var(--surface)`, `#2D3143` → `var(--border)`, etc. across all pages. Do one page at a time.
- [ ] **[FE-6] Add pagination** — add `page` / `offset` support to the runs API endpoint; add a "Load more" button or paginator to RunHistory and the pipeline runs list.
- [ ] **[FE-7] Fix TopBar blur handler** — replace `setTimeout(..., 150)` with a `useRef` on the dropdown container and a `relatedTarget.contains()` check in the `onBlur` handler.

---

## Phase 2 — Tests & Verification 🧪
*Automated test coverage + manual pre-launch smoke tests.*

### Manual Verification Checklist (do before launch)

#### End-to-End Pipeline Test
- [ ] Create DB connection → Test → verify "Connected"
- [ ] Create report config with simple `SELECT` → Preview → verify rows appear
- [ ] Create pipeline with one `report` step → Run Now → check Run History
- [ ] Add `email` step after report → run → verify email received
- [ ] Verify `{{ current_date }}` resolves in output filename and email subject
- [ ] Verify `StepResult.output_path` flows from report step → email attachments
- [ ] Verify `duration_ms` and `rows_affected` written to `ff_step_runs`

#### Scheduler Smoke Test
- [ ] Create pipeline with `* * * * *` schedule → start scheduler → verify auto-run in history
- [ ] Disable pipeline → verify no more runs triggered

---

## Phase 4 — Polish & Release Prep 🔵
*Docs, GitHub presence, and final UX touches.*

- [ ] **README screenshots** — Dashboard, Pipeline Builder, Run Detail. Highest-impact item for GitHub stars.

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
- [ ] **Bulk file loader step (`bulk_load`)** — Replaces the Oracle SQL\*Loader shell script at `github.com/jagdeepvirdi/DayToDayOfficeOperations`. Full spec below.

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
| cx_Oracle requires Oracle Instant Client | Document clearly; make Oracle optional: `pip install flowforge[oracle]` |
| M365 requires Azure AD app registration | Step-by-step guide in docs/email-providers.md; flowforge setup microsoft365 wizard |
| Gmail OAuth2 token expiry | Refresh token handling; re-auth wizard in settings |
| Drive folder ID opaque to users | Folder picker in frontend fetches Drive tree via API |
| Smart attachment: Drive upload fails after report generated | Fallback: attach directly if Drive upload fails, log warning |
| Large report query times out in Preview | Preview uses `LIMIT 20` wrapper around user query |
| Oracle LOB columns break row serialization | OracleConnection reads LOB values explicitly before cursor close |
