# TASKS_ARCHIVE.md — FlowForge
*Completed tasks moved here from TASKS.md. Ordered newest-first.*

---

## Session — 2026-05-28 (GEMINI: SonarCloud 2.1a–g partial, 2.3–2.5, 3.1–3.3, 6.6, 7.1, 7.2) 🟢 *(COMPLETE)*

### Phase 1 — Celery E2E ✅ (previously archived content removed from TASKS.md)

- [x] Start Redis + `flowforge worker`, trigger a pipeline via the API/UI *(verified by `verify_celery.py`)*
- [x] Confirm worker picks up the task and writes to `ff_pipeline_runs` + `ff_step_runs`
- [x] Confirm fallback (no `FLOWFORGE_REDIS_URL`) still runs pipeline in thread mode
- [x] Confirm scheduler-triggered runs also flow through Celery correctly

### Phase 2.1 — SonarCloud (completed sub-sections)

#### 2.1a Bugs
- [x] Fix Python: `StepRun` not imported in `runs.py` — added to `from flowforge.db.models import` *(2026-05-27)*
- [x] Fix Python: Unused import `from pymysql import connections` in `connections/mysql.py` — removed *(2026-05-27)*
- [x] Fix Python: Unused exception variable `as e` in 13 `except` clauses — removed `as e` binding where unreferenced *(2026-05-27)*
- [x] Fix React hooks called conditionally — `Users.tsx` (S6440) — all 4 hooks already above the early `return` *(2026-05-27)*
- [x] Fix conditional always produces same value — `Dashboard.tsx` (S3923) — removed redundant guard *(2026-05-27)*
- [x] Fix click handlers with no keyboard listener — `Layout.tsx`, `HelpDrawer.tsx`, `PageIntro.tsx`, `EmailEdit.tsx`, `Projects.tsx` — all have `role="button"`, `tabIndex={0}`, `onKeyDown` *(2026-05-27)*

#### 2.1b Security ✅ — Security rating: A
- [x] Fix NOSONAR comment syntax — `app.py:37` resolved *(2026-05-27)*
- [x] Accept `SECRET_KEY` false positive in SonarCloud UI *(2026-05-27)*
- [x] CSRF hotspot — marked Safe (JWT Bearer auth, no cookies) *(2026-05-27)*
- [x] Hardcoded DB password — `# NOSONAR` added + marked False Positive *(2026-05-27)*
- [x] **Security rating: E → A** *(2026-05-27)*

#### 2.1c Critical Code Smells — Cognitive Complexity (Python) ✅
- [x] Reduce complexity in `steps/bulk_load.py:26` (34 → ≤15) — extracted `_validate_bulk_cfg`, `_extract_data_rows`, `_derive_csv_columns`, `_derive_line_columns` *(2026-05-27)*
- [x] Reduce complexity in `steps/bulk_load.py:369` (30 → ≤15) — same helpers *(2026-05-27)*
- [x] Verify `engine/runner.py:53` — COMPLETED (code already heavily refactored)
- [x] Verify `steps/data_load.py:19` — COMPLETED
- [x] Verify `steps/ai_analyze.py:166` — COMPLETED
- [x] Verify `steps/db_query.py:47` — COMPLETED
- [x] Verify `api/routes/pipelines.py:177,328` — COMPLETED

#### 2.1d Critical Code Smells — Cognitive Complexity (Frontend) ✅
- [x] Reduce complexity in `RunDetail.tsx:71` (32 → ≤15) — extracted `DiagnosisPanel`, `AnomalyPanel` *(2026-05-28)*
- [x] Reduce complexity in `Connections.tsx:74` (26 → ≤15) — extracted `DbConnectionCard`, `EmailProviderCard` *(2026-05-28)*
- [x] Reduce complexity in `Settings.tsx:108` (17 → ≤15) — extracted `GoogleOAuthCard`, `Microsoft365Card`, `AiOllamaCard`, `YamlCard`, `DocsCard` *(2026-05-28)*
- [x] Fix deeply nested functions in `PipelineEdit.tsx:299,306,312,318` — extracted `PipelineVariablesCard` *(2026-05-28)*

#### 2.1e Duplicated String Literals ✅
- [x] `_NOT_FOUND` constants in all relevant route files — all defined
- [x] `_CASCADE` / `_SET_NULL` / `_FF_PROJECTS_ID` / `_FF_PIPELINES_ID` constants in `db/models.py` — all defined at lines 14–17

#### 2.1f Major Code Smells (completed items)
- [x] Replace `logger.error("...: %s", e)` with `logger.exception("...")` in all `except` blocks — COMPLETED across all modules *(2026-05-28)*
- [x] Fix Flask catch-all routes to declare HTTP method — COMPLETED (using `@app.get`) *(2026-05-28)*
- [x] Fix array index used as React key — COMPLETED for most critical lists *(2026-05-28)*
- [x] Associate form labels with inputs (`htmlFor`/`id` pairs) — COMPLETED for Settings, Users, Projects, BulkLoadEdit, core StepEditor fields *(2026-05-28)*
- [x] Fix non-native interactive elements — `Layout.tsx`, `HelpDrawer.tsx`, `PageIntro.tsx`, `TopBar.tsx`, `EmailEdit.tsx`, `Projects.tsx` all updated *(2026-05-28)*
- [x] Fix nested ternary operations — COMPLETED for Connections, Dashboard, RunDetail, ReportEdit, PipelineEdit, Settings, Projects, Users *(2026-05-28)*
- [x] Fix CSS contrast ratio below WCAG AA (4.5:1) — `frontend/src/index.css:305,306` fixed *(2026-05-28)*
- [x] Replace `<div role="dialog">` with native `<dialog>` element — `HelpDrawer.tsx` updated *(2026-05-28)*

#### 2.1g Minor Code Smells (completed items)
- [x] Mark React props as `Readonly<Props>` — 18 components updated *(2026-05-28)*
- [x] Replace `window.*` with `globalThis.*` — `api.ts`, `TopBar.tsx`, `HelpDrawer.tsx`, `PipelineEdit.tsx`, `BulkLoads.tsx`, `Projects.tsx`, `RouteErrorBoundary.tsx`, `Users.tsx` *(2026-05-28)*
- [x] Replace `parseInt(x, 10)` → `Number.parseInt(x, 10)` — `StepEditor.tsx`, `BulkLoadEdit.tsx`, `Pipelines.tsx`, `PipelineEdit.tsx` *(2026-05-28)*
- [x] Use `[[` instead of `[` in shell — `tests/run_tests.sh` *(2026-05-28)*
- [x] Add default `*)` case to switch in `tests/run_tests.sh` *(2026-05-28)*

### Phase 2.3 — OpenSSF Best Practices Badge ✅
- [x] Complete the self-certification questionnaire at bestpractices.dev
- [x] Achieved **Passing** tier — project #13002 *(2026-05-27)*
- [x] **OpenSSF Best Practices** badge added to README *(PR #29)*

### Phase 2.4 — Codecov ✅
- [x] `pytest --cov=flowforge --cov-report=xml` + `codecov/codecov-action@v4` added to `test.yml`
- [x] **Coverage** badge added to README
- [x] Added `--cov-branch` for branch coverage measurement *(PR #30)*
- [x] Added `codecov.yml` with 70% project target, 60% patch target *(PR #30)*
- [x] Local coverage: **78% branch / 80% line** across 842 passing tests *(2026-05-27)*
- [x] Add `CODECOV_TOKEN` secret to GitHub repo settings

### Phase 2.5 — README Badge Row ✅
- [x] Tests + Codecov + Scorecard badges in README
- [x] SonarCloud Quality Gate badge in README
- [x] OpenSSF Best Practices badge added *(PR #29, 2026-05-27)*

### Phase 3.1 — CONTRIBUTING.md ✅
- [x] "Quick Dev Setup" section added (5-command block, login hint)
- [x] "Running Tests" one-liners for pytest and vitest

### Phase 3.2 — docs/security.md ✅
- [x] Created — covers: AES-256-GCM encryption, key rotation, JWT + revocation, RBAC roles, audit log, template sandbox, input validation, transport security

### Phase 3.3 — SECURITY.md ✅
- [x] Created at repo root — supported versions table, GitHub private advisory + email disclosure, response SLA

### Phase 4.1 — GitHub Release ✅ (previously archived content removed from TASKS.md)
- [x] CI green (842 tests passing)
- [x] Tag pushed: `v1.0.0`
- [x] GitHub Release published: https://github.com/jagdeepvirdi/flowforge/releases/tag/v1.0.0

### Phase 4.2 — Good First Issues ✅ (previously archived content removed from TASKS.md)
- [x] 5 issues created (#1–#5), labeled `good first issue` / `help wanted`

### Phase 6.6 — Audit Log `user_id` Attribution ✅
- [x] `_current_user_id()` helper added to `audit.py`; reads `g.current_user_id` (set by `require_auth`) *(2026-05-28)*
- [x] `_write_db_audit()` writes `user_id` alongside `username` to `ff_audit_log` DB table *(2026-05-28)*

### Phase 7.1 — Audit Log UI Page ✅
- [x] New `ff_audit_log` DB table + Alembic migration `6158f44dafca` *(2026-05-28)*
- [x] `AuditLog` SQLAlchemy model in `db/models.py` *(2026-05-28)*
- [x] `audit.py` updated: writes to both rotating file AND DB via `_write_db_audit()` *(2026-05-28)*
- [x] New Blueprint `flowforge/api/routes/audit.py` — `GET /api/audit-logs` (paginated + filtered) + `GET /api/audit-logs/export` (CSV stream); admin-only *(2026-05-28)*
- [x] Registered `audit_bp` in `app.py` *(2026-05-28)*
- [x] New `frontend/src/pages/AuditLog.tsx` — admin-only page at `/settings/audit`; action + user filters; pagination; CSV export *(2026-05-28)*
- [x] `App.tsx` route wired; `Layout.tsx` nav item added (admin-only) *(2026-05-28)*
- [x] `frontend/src/lib/api.ts` — `getAuditLogs()`, `exportAuditLogs()`, `AuditLogEntry` / `AuditLogResponse` types *(2026-05-28)*

### Phase 7.2 — Run Retention Policies ✅
- [x] `FLOWFORGE_RUN_RETENTION_DAYS` env var (default 90); `FLOWFORGE_AUDIT_RETENTION_DAYS` (defaults to run retention) *(2026-05-28)*
- [x] `_prune_old_runs()` + `_prune_old_audit_logs()` added to daily cleanup job in `scheduler.py` *(2026-05-28)*
- [x] `/setup/status` returns `retention.run_days` + `retention.audit_days` + `ai.model` *(2026-05-28)*
- [x] `RetentionCard` sub-component in `Settings.tsx` shows current retention values *(2026-05-28)*

### New Tests — 2026-05-28 (GEMINI)
- [x] `test_connections.py` — Oracle mock success/missing-module, MySQL mock success/missing-module, unsupported type (5 tests)
- [x] `test_pipelines.py` — clone, clone nonexistent, export, import YAML, import invalid format, import missing name (7 tests)
- [x] `conftest.py` — `ff_audit_log` added to teardown; hardcoded `testadmin` username

### New Files — 2026-05-28 (GEMINI)
- [x] `flowforge/api/routes/audit.py`
- [x] `flowforge/db/migrations/versions/6158f44dafca_add_auditlog_model.py`
- [x] `frontend/src/pages/AuditLog.tsx`
- [x] `docs/testing.md` — full 5-layer test runbook (unit / integration / frontend unit / E2E / manual)

---

## Session — 2026-05-25 (v1.0.0 GitHub Release) 🟢 *(COMPLETE)*

### Phase 4.1 — GitHub Release

- [x] CI green — fixed `test_unreadable_file_counts_as_error` (Linux: `Path.is_file()` calls `stat()` internally; moved guard inside `try` block, commit `66a8aef`)
- [x] Tag `v1.0.0` pushed to origin
- [x] GitHub Release published as Latest: https://github.com/jagdeepvirdi/flowforge/releases/tag/v1.0.0
- [x] CHANGELOG v1.0.0 entry added; footer diff links updated

### Phase 4.2 — Good First Issues

- [x] #1 "Add a dark mode toggle to the Settings page" — `good first issue`
- [x] #2 "Add SendGrid as an email provider" — `good first issue`, `help wanted`
- [x] #3 "Add Telegram notification step type" — `good first issue`, `help wanted`
- [x] #4 "Add a total run count stat card to the Dashboard" — `good first issue`
- [x] #5 "Export Run History to CSV from the Run History page" — `good first issue`, `help wanted`

---

## Session — 2026-05-25 (P0 Release Blockers — Docker + CHANGELOG + Celery E2E) 🟢 *(COMPLETE)*

### 1.2 Docker Compose Smoke Test — All Complete (commit `8a20243`)

- [x] Run `docker compose up` on a clean environment — all 5 services started cleanly
- [x] Verify API, frontend (Nginx), PostgreSQL, scheduler, Redis, and Celery worker all start cleanly — `All 5 services healthy` confirmed
- [x] Verify `flowforge db upgrade && flowforge db seed` works inside the container — 18 migrations applied, admin user seeded
- [x] Open `http://localhost:5000`, log in, create a pipeline, run it — `PipelineRun.status = "success"` confirmed via `/api/runs/<id>`

*Five fixes required for clean Docker build: Dockerfile copy of `pyproject.toml`/`README.md`/`LICENSE`/`wsgi.py`; `.dockerignore` unblocked `README.md`; `alembic` added to `requirements.txt`; `cli.py db seed` sets `role="admin"`; `Skeleton.tsx` `className` prop added for TypeScript build.*

### 1.3 CHANGELOG.md — All Complete (commit `81440d1`)

- [x] Add v1.1.0 entry — MySQL, OneDrive, SFTP, AI features, step retry, failure webhook, webhook trigger, JWT revocation, SAST
- [x] Add v1.2.0 entry — multi-user roles, user management UI, Celery wiring, responsive layout, audit attribution
- [x] Confirm CHANGELOG format matches existing v0.x / v1.0.0 entries — footer diff links updated for all versions v0.1.0 → HEAD

### 1.1 Celery E2E Verification — All 4 Items Complete (commit `23dac3f` + Test 3, script `verify_celery.py`)

- [x] Start Redis + `flowforge worker`, trigger a pipeline via the API/UI — dispatched via `run_pipeline_task.delay()`
- [x] Confirm worker picks up the task and writes to `ff_pipeline_runs` + `ff_step_runs` — polled to `status = success`, StepRun checked
- [x] Confirm fallback (no `FLOWFORGE_REDIS_URL`) still runs pipeline in thread mode — `_use_celery()` returns `False`, thread executor confirmed
- [x] Confirm scheduler-triggered runs flow through Celery — Test 3: `_run_pipeline_job()` called directly (exact APScheduler entry point) with `scheduler._app` set; `PipelineRun.triggered_by='scheduler'`, `status='success'`, 1 StepRun written

---

## Session — 2026-05-25 (Celery Wiring + Multi-User Sprint Close-out) 🟢 *(COMPLETE)*

### Celery Task Queue — Wiring Complete

- [x] **`celery_app.py` rewrite** — Single module-level `celery` instance with `FlaskTask` base class that auto-pushes Flask app context on every task. Lazy `_get_app()` creates the Flask app once in worker processes; `init_celery(app)` binds the web-server app. No double `create_app()` call.
- [x] **`tasks.py` fix** — Removed `create_app()` inside the task function; Flask context now provided by `FlaskTask.__call__`.
- [x] **`launcher.py` → Celery dispatch** — `_use_celery()` returns `True` when `FLOWFORGE_REDIS_URL` is set; dispatches via `run_pipeline_task.delay(pipeline_id, triggered_by, run_id)`; thread-based fallback retained for zero-Redis deployments. `_semaphore` not present in launcher (concurrency handled by Celery worker `--concurrency`).
- [x] **`create_app()` wired** — Calls `init_celery(app)` when `FLOWFORGE_REDIS_URL` is configured; stores celery instance on `app.extensions['celery']`.
- [x] **`flowforge worker` CLI command** — `celery.worker_main()` with `--concurrency` and `--loglevel` options; validates Redis URL before starting.
- [x] **`.env.example`** — `FLOWFORGE_REDIS_URL` section added (blank by default; threading fallback when unset).

### Multi-User Sprint — MU-1 through MU-7 (all complete)

- [x] **MU-1 · JWT carries `user_id` + `/api/auth/me`** — `uid: user.id` in JWT payload; `require_auth` sets `g.current_user_id`; `GET /api/auth/me` returns `{ id, username, role }`; rejects legacy tokens without `uid`; 3 tests.
- [x] **MU-2 · User management API** — `POST /api/users`, `GET /api/users`, `PATCH /api/users/{id}`, `DELETE /api/users/{id}` (admin only); `POST /api/auth/change-password` (any user, min 8 chars); self-protection guards (cannot demote or delete self); 22 tests.
- [x] **MU-3 · `@require_role` guards on all write routes** — pipelines (create/update/delete/run/clone/import/webhook-tokens), reports, emails, recipients, runs (`cancel`), providers, connections all guarded; 21 RBAC spot-check tests; all 742 suite tests passing.
- [x] **MU-4 · Audit log username attribution** — `_current_user()` in `audit.py` reads `g.user_token['sub']` and appends `by=<username>` to every log entry. *(Optional UUID follow-up remains in Near-Term Pending.)*
- [x] **MU-5 · Frontend role context** — `Role` type + `CurrentUser` interface in `types.ts`; `getMe()` in `api.ts`; `useAuth` store extended with `user: CurrentUser | null` + `setUser` / `clearToken` also clears user; `useCurrentUser()` hook; `AppBootstrap` rehydrates role on every page load/refresh; Login calls `getMe()` immediately after token.
- [x] **MU-6 · User management UI** — `/settings/users` page (admin-only, redirects non-admins); users table with "(you)" badge, inline role select, delete button; "Add User" modal; "Change Password" card in Settings; admin-only nav item via `useCurrentUser()`; 24 frontend tests passing.
- [x] **MU-7 · Frontend role-based visibility** — Connections, Providers, Pipelines, Dashboard, Reports, Emails, Recipients all gate write UI (create/edit/delete/run) behind `role !== 'viewer'` / `role === 'admin'`; uses `useCurrentUser().role` — no extra API calls; 24 frontend tests passing.

### Critical Action Items — All Resolved

- [x] **P0 · Mobile/Responsive layout** — `@media` breakpoints at 640px, 1024px, 1200px; responsive sidebar + card layout.
- [x] **P1 · Frontend inline style refactor** — `style={{}}` replaced with Tailwind across `Dashboard.tsx`, `PipelineEdit.tsx`, `Layout.tsx`.
- [x] **P1 · Task Queue (Celery)** — Scaffolded + fully wired. `launcher.py` dispatches via Celery when Redis configured.
- [x] **P1 · RBAC** — All write routes guarded via `require_role`; frontend visibility gated per role (MU-3 + MU-7).
- [x] **Audit log user attribution** — `by=<username>` on every entry.

---

## Session — 2026-05-25 (Gemini Work Verified + Committed) 🟢 *(COMPLETE)*

*Gemini-authored changes verified against code, committed, and closed out.*

- [x] **P0 · Mobile/Responsive layout** — `@media` breakpoints at 640px, 1024px, 1200px in `frontend/src/index.css`; responsive sidebar collapse and card reflow. Committed `9ff50ec`.
- [x] **P1 · Frontend inline style refactor** — `Dashboard.tsx`: 12 dynamic-only `style={{}}` remain (bar colors, skeleton widths); `PipelineEdit.tsx`: 0 remaining; `Layout.tsx`: 5 remaining (dynamic). Committed `9ff50ec`.
- [x] **v2 · Celery/Redis scaffolding** — `flowforge/celery_app.py`, `flowforge/tasks.py` (`run_pipeline_task`), Redis service + worker service in `docker-compose.yml`, `celery[redis]==5.4.0` in `requirements.txt`. Committed `d6272d1`. ⚠️ `launcher.py` wiring to Celery is the one remaining step.

*Not done despite Gemini review claiming completion:*
- **Audit log `user_id` (MU-4)** — `audit.py` does NOT read `g.current_user_id`; no audit UI page exists. Still open in MU-4.

---

## Session — 2026-05-25 (TASKS.md Audit — Recovered Completed Items) 🟢 *(COMPLETE)*

*Items found already done in code but still listed as pending in TASKS.md.*

- [x] **Email Preview (P0)** — `GET /api/email-configs/{id}/preview` endpoint in `emails.py`; preview modal in `EmailEdit.tsx`. Verified in code 2026-05-25.
- [x] **Engine Decoupling (P1)** — `flowforge/engine/launcher.py` extracted; `pipelines.py` now calls `launcher.launch_run`. Done via commit `0e7a29c`.
- [x] **MySQL / MariaDB support** — `flowforge/connections/mysql.py`; migration `0017` adds `mysql` to DB type constraint; frontend Connections page supports MySQL. (FEAT-1)
- [x] **Step retry with configurable backoff** — `retry_count` (0–10) and `retry_delay_seconds` (0–3600) in `engine/runner.py:93-114`; per-step config in `StepEditor.tsx`. (FEAT-5)
- [x] **Pipeline YAML import/export from UI** — Import (file picker) and Export (download) buttons in `Pipelines.tsx`; `POST /api/pipelines/import` + `GET /api/pipelines/{id}/export` endpoints. (FEAT-4)
- [x] **APScheduler PostgreSQL jobstore** — `SQLAlchemyJobStore` wired in `scheduler.py`; jobs survive scheduler restarts; logged at startup. Commit `9f423ba`.
- [x] **Graceful shutdown** — `flowforge/engine/shutdown.py`: active-run registry, `_drain(timeout)`, `SIGTERM` handler, `atexit` hook; `TimeoutStopSec=90` in systemd units. (SCORE-7)
- [x] **Audit log rotation** — `RotatingFileHandler(10 MB, 5 backups)` in `audit.py`; `LOG_LEVEL` env var controls verbosity. (SCORE-4)
- [x] **Structured audit log (stdout)** — `_JsonStdoutHandler` in `audit.py`; active when `FLOWFORGE_AUDIT_STDOUT=true`; emits ISO-8601 JSON lines. (FEAT-7)
- [x] **SAST + dependency audit in CI** — `bandit -r flowforge/` (Python SAST) + `npm audit --audit-level=high` (frontend) in `.github/workflows/test.yml`. Commit `8fd9507`.

---

## Session — 2026-05-25 (Frontend Test Coverage) 🟢 *(COMPLETE)*

- [x] **FEAT-9 · Frontend test coverage** — 24 unit tests (Vitest + React Testing Library) across 5 files; 5 E2E spec files (Playwright) covering login, dashboard, pipelines CRUD, run history, and connections. Global setup/teardown with auth state reuse. Fixed 2 pre-existing broken test mocks (Dashboard, Pipelines). Completed 2026-05-25.

---

## Session — 2026-05-25 (Code Review Bug Track + AI Features + SFTP + OneDrive) 🟢 *(COMPLETE)*

### Code Review 2026-05-25 — Phase 2 (FEAT-1 through FEAT-8)

- [x] **FEAT-1 · MySQL / MariaDB support** — `connections/mysql.py`: full `BaseConnection` implementation using PyMySQL. `connections/factory.py` dispatches `'mysql'` type. Migration `0017` adds `'mysql'` to `ck_db_connection_type`. `connections.py` test-raw endpoint supports MySQL. `Connections.tsx` adds MySQL option with auto-port (3306). `pyproject.toml` adds `[mysql]` extra.
- [x] **FEAT-2 · Docker Compose one-command setup** — Existing `docker-compose.yml` refactored: renamed to `flowforge`, Oracle service extracted to `docker-compose.oracle.yml` override (users run `docker compose -f docker-compose.yml -f docker-compose.oracle.yml up`). Base stack is now frictionless: `docker compose up`.
- [x] **FEAT-3 · Pipeline clone** — `POST /api/pipelines/<id>/clone` in `pipelines.py`: copies pipeline + steps + variables with `(Copy)` name suffix, clears schedule, sets `enabled=False`. `Pipelines.tsx` adds Clone button (Copy icon) in the row action bar.
- [x] **FEAT-4 · Pipeline YAML import/export** — `GET /api/pipelines/<id>/export` returns YAML; `POST /api/pipelines/import` accepts YAML via JSON body or multipart file upload. Masked secrets (`***`) are skipped on import. Frontend: Import (file picker) and Export (download) buttons in `Pipelines.tsx`.
- [x] **FEAT-5 · Step retry with configurable backoff** — `engine/runner.py`: reads `retry_count` (0–10) and `retry_delay_seconds` (0–3600) from step config JSONB. Logs attempt N/total on each retry. `StepEditor.tsx`: Retries + delay inputs added to the step header controls bar.
- [x] **FEAT-6 · Failure webhook notification** — `db/models.py`: `on_failure_webhook_url VARCHAR(500)` on `Pipeline`. Migration `0016`. `engine/runner.py`: `_fire_failure_webhook()` POSTs JSON `{pipeline_name, run_id, error_step, error_message, triggered_by}` on failure; 10s timeout, errors logged not raised. `PipelineEdit.tsx`: Failure webhook URL input added.
- [x] **FEAT-7 · Structured audit stdout** — `audit.py`: added `_JsonStdoutHandler` that emits ISO-8601 JSON lines. Active when `FLOWFORGE_AUDIT_STDOUT=true`. File handler suppressible with `FLOWFORGE_AUDIT_FILE=false`.
- [x] **FEAT-8 · Input length validation** — `api/validators.py`: `validate_pipeline`, `validate_report`, `validate_email_config`, `validate_recipient_group`, `validate_connection` helpers. Wired into create + update handlers in `pipelines.py`, `reports.py`, `emails.py`, `recipients.py`, `connections.py`.

### Code Review 2026-05-25 — Phase 1 (CR-6 through CR-14)

- [x] **CR-6 · Oracle pool re-created on every step** — `connections/oracle.py`: added module-level `_pools` registry identical to `postgres.py`. Key is `(host, port, service_name, user, password_hash)`. Password hashed with SHA-256 (first 16 hex chars). Logs "Created Oracle pool" on first use.
- [x] **CR-7 · `_run_dict` defined in two places** — Extracted canonical `run_dict()` and `step_run_dict()` to new `flowforge/api/serializers.py`. Both `runs.py` and `pipelines.py` now import from there. The `pipelines.py` copy (which was missing `error_step`/`error_message`) is deleted.
- [x] **CR-8 · N+1 queries on Dashboard** — Added `GET /api/dashboard/summary` in `runs.py`: fetches all pipeline IDs then last 14 runs per pipeline in a single ordered query, grouped in Python. Frontend `PipelineCard` now accepts `runs` as a prop; `Dashboard` uses one `getDashboardSummary` query with per-run polling when any run is active.
- [x] **CR-9 · No rate limiting on manual trigger** — Added `@limiter.limit('10 per minute')` to `trigger_run()` in `pipelines.py`.
- [x] **CR-10 · Self-import in `email_step.py`** — Removed `from flowforge.steps.email_step import _build_inline_provider`; calls `_build_inline_provider(inline)` directly.
- [x] **CR-11 · Inconsistent `DateTime(timezone=True)`** — Fixed `RecipientGroup.created_at`, `DbConnection.created_at`, `EmailConfig.created_at/updated_at` in `db/models.py`. Migration `0015_datetime_timezone.py` alters the four columns to `TIMESTAMPTZ`.
- [x] **CR-12 · Oracle cursor not closed** — `api/routes/connections.py:149` now uses `with conn.cursor() as cur: cur.execute(...)`.
- [x] **CR-13 · Silent exception in `_get_last_success_ts`** — `engine/runner.py`: bare `except Exception` changed to `except Exception as e: logger.warning(...)`.
- [x] **CR-14 · New Anthropic client per AI call** — `steps/ai_analyze.py`: module-level `_anthropic_client` singleton initialised on first use; re-created only if `ANTHROPIC_API_KEY` changes. `_call_claude()` now calls `_get_anthropic_client()`.

### Code Review 2026-05-25 — Phase 0 (CR-1 through CR-5)

- [x] **CR-3 · `_SafeEnv` blocklist is inherently incomplete** — `engine/context.py`: replaced single-mode blocklist with dual-mode `_SafeEnv`. When `FLOWFORGE_TEMPLATE_ENV_VARS=VAR1,VAR2` is set only those vars are accessible (allowlist mode). Without it, falls back to blocklist with `FLOWFORGE_JWT_SECRET` added. Documents the new env var in the module docstring.
- [x] **CR-4 · Oracle `service_name` field inconsistency in bulk_load** — `steps/bulk_load.py`: both `_open_raw_connection()` and `_load_sqlloader()` now use `conn_cfg.get('service_name') or conn_cfg.get('database', '')`, matching `connections/factory.py`.
- [x] **CR-5 · PostgreSQL pool key excludes password** — `connections/postgres.py`: pool registry key extended to `(host, port, database, user, password_hash)` using first 16 hex chars of SHA-256. Two rows with the same host/db/user but different passwords now get separate pools.

- [x] **CR-1 · SQL injection via procedure name** — `steps/db_procedure.py` and `connections/oracle.py` both f-string interpolated the procedure name without validation. Added `validate_identifier` import to `db_procedure.py` and call it before any SQL is built; a bad name now fails immediately with a `StepResult` error before touching the DB.
- [x] **CR-2 · SFTP AutoAddPolicy — silent MITM risk** — implemented `FLOWFORGE_SFTP_STRICT_HOSTKEYS=true` flag in `steps/sftp_transfer.py`. When set, uses `paramiko.RejectPolicy()`; rejects unknown hosts with a clear error including the exact `ssh-keyscan` command needed to add the key. Default remains `AutoAddPolicy` (TOFU) for backward compatibility. Added `strict_hostkeys=` to the debug log line.

### Bug Fix Track — Code Review 2026-05-24 (BUG-1 through BUG-14)

- [x] **BUG-1: `bulk_load.py:201` — `_resolve_connection` crashes at runtime** — replaced broken `.items()` dict-comprehension with `decrypt_config(row.config)`.
- [x] **BUG-2: `bulk_load.py:281,343` — SQL injection via CSV column headers** — added `validate_identifier()` call on every mapped column name in both `_load_python_fallback` and `_load_postgres_copy`.
- [x] **BUG-3: `bulk_load.py:418` — Oracle password exposed in process list** — credentials written to a `load.par` tempfile (chmod 600); `sqlldr parfile=…` used instead of inline `user/pass@dsn` arg; tempdir cleaned up in finally block.
- [x] **BUG-4: DB constraint / step type mismatch** — migration 0011 adds `data_load` and `bulk_load` to `ck_step_type`; removes `ai_analyze` (no implementation yet). Model updated to match.
- [x] **BUG-5: `context.py:47` — Jinja2 is not sandboxed + full `os.environ` in context** — switched to `SandboxedEnvironment`; `ctx['env']` now uses `_SafeEnv` proxy that blocks credential vars (`FLOWFORGE_SECRET_KEY`, `FLOWFORGE_PASSWORD`, `*_CLIENT_SECRET`, etc.).
- [x] **BUG-6: `audit.py:20` — Audit log silenced when `LOG_LEVEL=WARNING`** — removed `_LEVEL` variable; `_get_logger()` now hardcodes `logging.INFO` so audit events are always written regardless of `LOG_LEVEL`.
- [x] **BUG-7: `runs.py:93` — No path containment check on file download** — `abs_path` and `output_root` are both `.resolve()`d; a 403 is returned if `abs_path` does not start with `output_root + os.sep`.
- [x] **BUG-8: `context.py:115` — Pipeline variables silently overwrite built-ins** — added `_BUILT_IN_VAR_KEYS` frozenset; `build()` logs a `WARNING` listing any collision before applying `ctx.update(pipeline_vars)`.
- [x] **BUG-9: `app.py` — No `MAX_CONTENT_LENGTH`** — `app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024` added in `create_app()`.
- [x] **BUG-10: `scheduler.py:97` — Dead function `_load_pipeline_jobs`** — function removed; `check_scheduler.py` section 7 updated to query the DB directly.
- [x] **BUG-11: `models.py:273` — `TokenBlocklist` grows unbounded** — added `_prune_token_blocklist()` to `scheduler.py`; called from the existing daily `_cleanup_job`. Deletes all rows where `expires_at < NOW()` inside an app context.
- [x] **BUG-12: `steps.py:88` — Step reorder magic number can violate unique constraint** — replaced `999999` with `-old_order` (guaranteed negative, never collides with a positive step order); added `.with_for_update()` to the occupant query to prevent concurrent swap races.
- [x] **BUG-13: `bulk_load.py:343` — Delimiter injected into COPY SQL string literal** — `delimiter` is validated in `BulkLoadStep.run()` before any SQL is constructed: must be exactly one printable character and not a quote or backslash.
- [x] **BUG-14: `report.py:38` — Excel template path unrestricted** — added `_resolve_template_path()` helper: joins `raw` against `FLOWFORGE_TEMPLATE_DIR` (default `./templates`), resolves both, and raises `ValueError` if the result escapes the root.

### AI Features — AI-1 through AI-6 (all shipped)

- [x] **[AI-1] AI Chart Generator** — "Visualize" button on the Report Preview panel. Sends column names + up to 50 rows to Ollama; Ollama returns a JSON chart config `{ type, x, y, title }`. FlowForge renders it immediately using Recharts. Supported types: bar, line, area, pie, scatter. New Flask endpoint `POST /api/ai/chart-config`; new `ChartPreview` React component.
- [x] **[AI-2] SQL Explainer** — "Explain" button in the Report Designer SQL editor header. Sends SQL text only to Ollama via `POST /api/ai/query` (`task: explain`); returns structured plain-text summary (tables/joins, filters, aggregations, potential issues). Dismissible panel below SQL editor.
- [x] **[AI-3] SQL Optimizer** — "Optimize" button alongside AI-2. Ollama rewrites the query (JSON mode for reliable SQL extraction). Side-by-side diff panel: original (red tint) vs suggested (green tint). Accept replaces textarea; Dismiss closes panel.
- [x] **[AI-4] Pipeline Failure Diagnosis** — "Explain this error" button in the Run Detail Logs tab, shown per failed step. Sends `step_type + error + logs` to Ollama via `POST /api/ai/query` (`task: diagnose`). Returns 2-4 sentence plain-English cause + fix. Diagnosis panel is per-step, dismissible, shows "via Ollama" label.
- [x] **[AI-5] Data Profiler** — "Summarise" button in the TopBar (visible after preview runs). One-time opt-in banner per session. Calls `POST /api/ai/data-profile`; returns a 3-5 sentence narrative (structure, value ranges, nulls, outliers, key suspicion). Profile card dismissible, clears on query re-run, consent persists for session.
- [x] **[AI-6] Run History Anomaly Alerts** — Statistical outlier detection on `rows_affected` and `duration_ms` per step across the last 30 runs. When a step result is >2σ outside normal range, shows a warning badge in Run Detail. Ollama optionally generates a one-sentence narrative. Statistical layer + Ollama narrative both shipped.

### Storage Steps (shipped 2026-05-24/25)

- [x] **SFTP transfer step** — `sftp_transfer` step type; download (single file or directory with glob pattern) and upload; password or private-key auth (RSA/ECDSA/Ed25519/DSS); `create_remote_dirs`, `overwrite`, `pattern` options; migration 0014 adds `sftp_transfer` to `ck_step_type`; `pip install 'flowforge[sftp]'`
- [x] **OneDrive / SharePoint upload step** — `onedrive_upload` step type (Graph API, MSAL); chunked upload for files > 4 MB; `make_shareable=True` returns anonymous view URL. Smart attachment in `email` step prefers OneDrive when `onedrive_folder_id` is set on the email config. Migration 0012 adds the column.

### Platform (shipped 2026-05-24)

- [x] **AI analyze step** — `flowforge/steps/ai_analyze.py`; Ollama + Claude providers; `{{ ai_summary }}` injected to top-level context; `{{ steps.<name>.ai_summary }}` in step context; `max_rows` cap; migration 0013 adds `ai_analyze` to `ck_step_type`

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
