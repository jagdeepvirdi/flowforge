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

## Phase 5 — Security Fixes 🔴 *(COMPLETE — 2026-05-20)*
*Addresses SEC findings from CODEBASE_REVIEW.md. Target score: Security 5.5 → 8.0*

- [x] **[SEC-1] Remove hardcoded credentials from `tests/conftest.py`** — removed `harpal123` default; added `.env.test.example`; `sys.exit(1)` with clear message if `FLOWFORGE_DB_URL` not set; CI workflow already sets it.
- [x] **[SEC-2] Split encryption key and JWT secret** — `FLOWFORGE_JWT_SECRET` introduced for JWT signing; `FLOWFORGE_SECRET_KEY` reserved for AES-256 only. Falls back with a `warnings.warn` if unset. Updated `app.py`, `auth.py`, `conftest.py`, `.env.example`, CI workflow.
- [x] **[SEC-3] Fix rate limiter for proxied deployments** — added `werkzeug.middleware.proxy_fix.ProxyFix` controlled by `FLOWFORGE_TRUSTED_PROXIES` env var (default 0). When set ≥1, `get_remote_address` correctly resolves real client IP from `X-Forwarded-For`. Documented in `.env.example`.
- [x] **[SEC-6] Require `FLOWFORGE_CORS_ORIGIN` in production** — logs a loud `WARNING` at startup if `FLASK_ENV=production` and var is unset. `http://localhost:5173` is now dev/test fallback only. Added `FLOWFORGE_CORS_ORIGIN` to `.env.example`.
- [x] **[SEC-7] Add basic audit logging** — `flowforge/audit.py` writes to `logs/audit.log`. Login success/failure logged from `routes/auth.py` (with IP). Pipeline STARTED/SUCCESS/FAILED logged from `runner.py`.

---

## Phase 6 — Reliability & Production Readiness 🟠 *(COMPLETE — 2026-05-20)*
*Addresses ARCH + OPS findings. Target score: Architecture 6.5 → 8.0, DevOps 6.0 → 7.5*

- [x] **[ARCH-1a] Add concurrency limit to pipeline execution** — `FLOWFORGE_MAX_CONCURRENT_RUNS` env var (default 5); `threading.Semaphore` in `trigger_run`; excess runs rejected with HTTP 429; semaphore released in `finally` block.
- [x] **[ARCH-1b] Enforce `timeout_minutes` in `runner.py`** — background thread uses `concurrent.futures.ThreadPoolExecutor`; `.result(timeout=...)` raises `TimeoutError`; run marked `failed` with `"Pipeline timed out"`.
- [x] **[ARCH-1c] Sweep stuck `running` runs on startup** — `_sweep_stuck_runs()` called from `create_app()`; marks all `status='running'` rows as `failed` with `"Run interrupted by server restart"`; skips silently if table missing.
- [x] **[ARCH-2] Add `scheduler` service to `docker-compose.yml`** — second service runs `flowforge schedule`; shares image + `output_files` volume; depends on `app: service_healthy`.
- [x] **[ARCH-3] Fix stuck-run race condition in `trigger_run`** — `load_pipeline()` wrapped in `try/except`; on failure run record is set to `failed` and semaphore is released before returning 500.
- [x] **[OPS-2] Add `healthcheck` to `app` service in `docker-compose.yml`** — `GET /api/health`; `interval: 15s`, `timeout: 5s`, `retries: 3`, `start_period: 30s`.
- [x] **[OPS-3] Move `_seed_admin` out of `create_app()`** — `flowforge db seed` CLI command added; documented in getting-started.md; `_seed_admin` removed from app factory, replaced with `_sweep_stuck_runs`.

---

## Phase 7 — Code Quality 🟡 *(COMPLETE — 2026-05-20)*
*Addresses CODE + DB findings. Target score: Code Quality 6.0 → 7.5, Database 6.5 → 8.0*

- [x] **[CODE-1] Fix silent exception swallowing in `runner.py` DB helpers** — `except Exception: return None` replaced with `except SQLAlchemyError as e: logger.error(...)` in all three helpers; `SQLAlchemyError` imported at module level.
- [x] **[CODE-2] Replace class-name string manipulation for `step_type`** — `step_type: str = ''` added to `BaseStep`; each concrete step sets its own value; `_write_step_run` uses `step.step_type` with the string-hack as fallback.
- [x] **[CODE-3] Protect built-in context variables from `output_variables` overwrite** — before `context.update(...)`, collision check against `_CONTEXT_META_KEYS`; conflicting keys logged and skipped; safe keys propagated normally.
- [x] **[CODE-4] Fix `_utcnow()` timezone stripping** — `_utcnow()` returns `datetime.now(timezone.utc)` (no `.replace(tzinfo=None)`); all model `DateTime` columns changed to `DateTime(timezone=True)`; all call sites updated; migration `0002_timezone_timestamps.py` converts columns to TIMESTAMPTZ.
- [x] **[DB-1] Fix step reordering constraint** — `PUT /pipeline-steps/<id>` uses two-phase swap: occupant moved to order 999999 → target step moved → occupant moved to original slot; no unique constraint violation.
- [x] **[DB-2] Add performance indexes** — migration `0003_indexes_and_constraints.py` adds `ix_pipeline_runs_pipeline_started` on `(pipeline_id, started_at DESC)` and `ix_step_runs_pipeline_run` on `(pipeline_run_id)`.
- [x] **[DB-3] Widen `DbConnection` check constraint** — `mysql`, `mssql`, `snowflake` added to constraint in both `models.py` and migration `0003`; old constraint dropped and recreated.

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
