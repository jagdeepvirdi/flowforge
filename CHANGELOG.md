# Changelog

All notable changes to FlowForge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed — 2026-07-08

- **Frontend route-based code splitting** — `App.tsx` now lazy-loads every page via `React.lazy()` instead of static imports, with a `<Suspense>` boundary around the top-level `<Routes>` (covers `/login`) and a second one in `Layout.tsx` around `<Outlet/>` (covers nested authenticated routes, keeping the sidebar/topbar mounted during navigation). New `components/shared/RouteFallback.tsx` centers the existing `Spinner` as the loading fallback. The single production JS bundle dropped from ~1.1MB to a 254 kB main chunk, with Recharts, CodeMirror, and per-page code now split into on-demand chunks — clears Vite's default 500 kB `chunkSizeWarningLimit`. ([`frontend/src/App.tsx`](frontend/src/App.tsx), [`frontend/src/components/shared/Layout.tsx`](frontend/src/components/shared/Layout.tsx), [`frontend/src/components/shared/RouteFallback.tsx`](frontend/src/components/shared/RouteFallback.tsx))

> The entries below were reconstructed from commit history to close a gap — a large amount of
> work landed in a small number of squash-merged PRs whose commit messages didn't reflect their
> full contents, so it was never itemized here at the time. Grouped by the date it actually shipped.

### Added — 2026-07-01

- **Plugin step-type system** — Drop a `BaseStep` subclass into `FLOWFORGE_PLUGIN_DIR` (default `./plugins`) and it's picked up automatically on next pipeline load — no fork required. See [`docs/plugins.md`](docs/plugins.md). ([`flowforge/engine/loader.py`](flowforge/engine/loader.py))
- **Snowflake, BigQuery, and Redshift connectors** — Three more database types behind the same `BaseConnection` interface (Redshift reuses the core `psycopg2` dependency; no extra install needed). Install with `pip install 'flowforge-io[snowflake]'` / `[bigquery]`. ([`flowforge/connections/snowflake.py`](flowforge/connections/snowflake.py), [`flowforge/connections/bigquery.py`](flowforge/connections/bigquery.py), [`flowforge/connections/redshift.py`](flowforge/connections/redshift.py))
- **`s3_upload` / `azure_blob_upload` steps** — Upload a file to an AWS S3 bucket or Azure Blob Storage container; wired into the smart-attachment fallback alongside Drive/OneDrive. Install with `[ses]` (S3 shares the `boto3` dependency) / `[azure_blob]`. ([`flowforge/storage/s3.py`](flowforge/storage/s3.py), `flowforge/steps/s3_upload.py`, [`flowforge/storage/azure_blob.py`](flowforge/storage/azure_blob.py), `flowforge/steps/azure_blob_upload.py`)
- **SAML 2.0 SSO** — Enterprise IdP login (Okta, Azure AD, PingFederate) alongside the existing Google/Microsoft OAuth2 SSO. Install with `pip install 'flowforge-io[sso]'` (requires system `libxmlsec1`). ([`flowforge/api/routes/sso.py`](flowforge/api/routes/sso.py))
- **Redis-backed distributed concurrency lock** — Replaces the in-process run-limit check so multiple API/worker instances can be scaled horizontally without over-running the same pipeline concurrently.
- **Team-scoped project membership** (`ff_project_members`) — Projects can now be restricted to specific users instead of being visible instance-wide.

### Added — 2026-06-05

*A large batch of work (SSH steps, production hardening, the compliance track, new connectors, pipeline dependencies, and new email providers) shipped together; grouped by area below.*

**New step types:**
- **`ssh_command`** — run a remote command over SSH; `save_output` writes stdout (+ optionally stderr) to a file and sets `output_path`, even on non-zero exit, so failure logs can be attached to an alert email.
- **`ssh_health_check`** — connects once over SSH and collects load average, memory, disk usage, and top processes in a single session; generates an Excel/CSV report directly (`flowforge/reports/health_report.py`).
- **`db_health_check`** (refactored) — now also generates an Excel/CSV report and sets `output_path` instead of only logging. PostgreSQL: sessions, cache hit ratio, replication lag. Oracle: sessions, buffer cache, tablespace usage. MySQL: thread count.
- **`data_report`** (`flowforge/steps/script_report.py`) — turns an arbitrary script's output into a report.

  ([`flowforge/steps/ssh_command.py`](flowforge/steps/ssh_command.py), [`flowforge/steps/ssh_health_check.py`](flowforge/steps/ssh_health_check.py), [`flowforge/connections/ssh.py`](flowforge/connections/ssh.py); see [`docs/scenarios/health-monitoring.md`](docs/scenarios/health-monitoring.md) and [`docs/scenarios/log-extraction.md`](docs/scenarios/log-extraction.md) for end-to-end setup guides)

**Production hardening:**
- **Gunicorn + Nginx + systemd deployment guide** (`docs/RUNBOOK.md` §4a) — gevent workers, worker-count formula, TLS termination, systemd units for web/scheduler/worker processes. `Dockerfile` CMD switched to gevent workers with `GUNICORN_WORKERS` / `GUNICORN_TIMEOUT` overrides.
- **SQLAlchemy connection pool tuning** — `SQLALCHEMY_POOL_SIZE` / `MAX_OVERFLOW` / `POOL_TIMEOUT` / `POOL_RECYCLE` env vars, with PgBouncer guidance for 100+ concurrent pipelines (`docs/RUNBOOK.md` §9).
- **Prometheus metrics endpoint** — `GET /api/metrics` (Bearer-token protected) exposes `flowforge_runs_total{status}`, `flowforge_runs_active`, and `flowforge_queue_depth` in plain-text exposition format, no extra dependency. ([`flowforge/api/routes/metrics.py`](flowforge/api/routes/metrics.py))
- **Celery Flower dashboard** — opt-in `flower` service in `docker-compose.yml` under `--profile monitoring`.

**Compliance track:**
- **Report encryption at rest** (`FLOWFORGE_ENCRYPT_OUTPUT=true`) — `crypto.py` gains `encrypt_file()` / `decrypt_file_to_stream()`; the download endpoint decrypts `.enc` files transparently.
- **TOTP MFA** — `ff_users` gains `mfa_secret` / `mfa_enabled` / `mfa_backup_codes` (AES-256 encrypted); `/auth/mfa/enroll|confirm|disable|verify|use-backup` endpoints; QR-code enrollment in Settings; 10 backup codes; step-2 TOTP input on the login page. (`pyotp` dependency)
- **SSO (Google OAuth2 + Microsoft OAuth2)** — `/auth/sso/google|microsoft` + callbacks; token delivered via a `#sso_token=` hash fragment; `FLOWFORGE_SSO_AUTO_CREATE` controls whether first-time SSO logins auto-provision a user.
- **GDPR data export & purge** — `GET /api/admin/users/{id}/export` (profile + audit log + run history); `DELETE /api/admin/users/{id}?purge=true` (anonymises audit log, deletes the user).
- **IP allowlisting** — `FLOWFORGE_ALLOWED_IPS=CIDR,...` rejects `/api/*` requests from non-listed source IPs.
- **TruffleHog secrets scan** — new `.github/workflows/secrets-scan.yml` CI job.
- **`docs/data-flow.md`** — data inventory, encryption, retention, and GDPR-rights reference for SOC 2 / GDPR / HIPAA assessments.

  ([`flowforge/api/routes/mfa.py`](flowforge/api/routes/mfa.py), [`flowforge/api/routes/sso.py`](flowforge/api/routes/sso.py), [`flowforge/crypto.py`](flowforge/crypto.py))

**New connectors + password reset:**
- **MSSQL connector** — `pyodbc` with SQL Server ODBC driver, named-param `EXEC` syntax, `fast_executemany` for bulk loads. Install with `pip install 'flowforge-io[mssql]'`.
- **Generic ODBC connector** — DSN or raw connection string; `{CALL procedure(?,?)}` syntax for portable procedure calls.
- **Email-based password reset** — `POST /auth/password-reset/request` (always returns 200 — no user-existence leak) and `/confirm` (1-hour TTL, single-use token); "Forgot password?" flow on the Login page.

  ([`flowforge/connections/mssql.py`](flowforge/connections/mssql.py), [`flowforge/connections/odbc.py`](flowforge/connections/odbc.py))

**Pipeline dependencies + parallel execution:**
- **Pipeline dependencies** — `ff_pipeline_dependencies` table; cycle detection via BFS; a downstream pipeline auto-launches once all of its upstreams have a successful run since it last started (`triggered_by="dependency"`). `DependenciesCard` in the Pipeline Builder.
- **Parallel step execution** — steps sharing a `parallel_group` run concurrently in a `ThreadPoolExecutor`; outputs merge back into the shared context after the wave completes.

  ([`flowforge/engine/runner.py`](flowforge/engine/runner.py))

**Run diff, report formatting, and environment promotion:**
- **Run diff view** — `GET /api/runs/{id}/diff` compares a run against the previous successful run of the same pipeline (row/duration/file-size deltas per step); `DiffPanel` in Run Detail.
- **Excel column formatting** — `column_formatting` on report configs applies number formats, explicit column widths, and conditional cell coloring (`lt`/`lte`/`gt`/`gte`/`eq`/`ne` rules); `ColumnFormattingCard` in the Report Designer.
- **Environment promotion** — `POST /api/pipelines/{id}/promote` clones a pipeline (steps + non-secret variables) into a different project, starting disabled for safety.

**New email providers + notification step:**
- **SendGrid, AWS SES, Mailgun** — three more `EmailProvider` implementations behind the existing interface. Install with `[ses]` for SES.
- **`notification` step** — sends a message to Slack, Microsoft Teams, or Telegram via webhook/bot API (stdlib `urllib`, no extra dependency); outbound webhook URLs are validated against SSRF.

  ([`flowforge/email_providers/sendgrid.py`](flowforge/email_providers/sendgrid.py), [`flowforge/email_providers/ses.py`](flowforge/email_providers/ses.py), [`flowforge/email_providers/mailgun.py`](flowforge/email_providers/mailgun.py), [`flowforge/steps/notification.py`](flowforge/steps/notification.py))

### Security — 2026-06-05 / 2026-07-01

- CVE patches across the full Python and npm dependency tree (cryptography, Flask, Flask-CORS, bcrypt, PyJWT, SQLAlchemy, Alembic, Vite, Vitest, react-router-dom, and more) — `npm audit` and `pip-audit` both report 0 known vulnerabilities as of this batch.
- **Fuzzing** — property-based tests (`hypothesis`) covering `render()` crash-safety, env-var blocklist enforcement, and pipeline variable handling; runs in CI outside the main DB-backed test suite.
- **Signed releases + PyPI publishing** — `.github/workflows/release.yml` attaches SLSA build provenance to tagged releases; `.github/workflows/publish.yml` publishes to PyPI via OIDC trusted publishing (no stored tokens).
- Hash-pinned `requirements.txt` (via `requirements.in` + `pip-compile --generate-hashes`); `ruff` and frontend ESLint added to CI.
- CII Best Practices Silver documentation: `CODE_OF_CONDUCT.md`, `GOVERNANCE.md`, `ROADMAP.md`, `docs/threat-model.md`.

### Changed — 2026-07-05 to 2026-07-08

- **Full Tailwind CSS frontend migration** — every page and shared component converted from inline style objects / hand-written CSS to Tailwind utility classes; custom classes that remain are wrapped in `@layer components` instead of relying on `!important` overrides. (Commits tagged `chunk 12.1`–`12.13` in git history.)
- Docker service images (`docker-compose*.yml`, CI service containers) pinned to digest; Dependabot now tracks the `Dockerfile` + compose files for digest updates.
- Migration files with autogenerated hash IDs renamed to fit the numbered scheme (filenames only — revision IDs untouched) so directory order matches execution order.

### Added — earlier 2026-07 (previously undocumented)

- **Bulk load dry-run V2** — "Attempt insert (rolled back)" checkbox in the Bulk Load editor's Test File action. Inserts each sampled row individually against the real target table inside a transaction (rolled back, never committed), catching NOT NULL/unique/length/type errors that untyped CSV text can't reveal on its own. Failures are grouped by column + error type with affected rows/cells highlighted in the preview table. Not available for the Oracle SQL\*Loader path. ([`flowforge/steps/bulk_load.py`](flowforge/steps/bulk_load.py), [`frontend/src/pages/BulkLoadEdit.tsx`](frontend/src/pages/BulkLoadEdit.tsx))
- **Step performance trends** — new `GET /api/step-runs/trends` endpoint aggregates existing `step_runs` data (avg/p95 duration, row counts, failures) into daily buckets over a rolling window. Collapsible "Performance Trends" panel on the Run History page with a step-type/window picker and a Recharts duration chart. ([`flowforge/api/routes/runs.py`](flowforge/api/routes/runs.py), [`frontend/src/components/runs/StepTrendsPanel.tsx`](frontend/src/components/runs/StepTrendsPanel.tsx))
- **Audit log `run_id` cross-referencing** — `EMAIL_SENT`/`REPORT_EXPORTED` audit entries now carry `run_id`, so they can be joined directly to `pipeline_runs`/`step_runs` instead of fuzzy-matching on name and timestamp. ([`flowforge/audit.py`](flowforge/audit.py))
- **Loading skeletons** on 9 pages that previously showed a bare spinner on a blank screen (`AuditLog`, `BulkLoadEdit`, `Emails`, `Pipelines`, `Projects`, `Recipients`, `Reports`, `RunDetail`, `Settings`), matching the content-shaped skeleton pattern already used on `Dashboard`/`BulkLoads`/`RunHistory`.

## [1.0.0] — 2026-05-25 *(Initial Public Release)*

This is the first public release of FlowForge. It incorporates all the
features developed across the v1.1.0 and v1.2.0 milestones documented
below — see those entries for the full feature breakdown.

**Highlights**
- `docker compose up` brings up the full stack (API, frontend, PostgreSQL, scheduler, Redis, Celery worker)
- 10 step types: `db_procedure`, `db_query`, `report`, `email`, `drive_upload`, `onedrive_upload`, `sftp_transfer`, `ai_analyze`, `bulk_load`, `data_load`
- Email providers: Gmail (OAuth2), Microsoft 365 (MSAL + Graph API), generic SMTP
- Database connectors: PostgreSQL, Oracle, MySQL/MariaDB
- Multi-user roles: `admin`, `editor`, `viewer`
- Celery/Redis task queue with thread fallback
- 842 tests, ≥ 80 % coverage

## [1.2.0] — 2026-05-25

### Added

- **Multi-user roles** — FlowForge moves from a single-admin model to a proper user system with three built-in roles:
  - `admin` — full access, user management, all write operations
  - `editor` — create and edit pipelines, connections, reports, email configs; cannot manage users
  - `viewer` — read-only; can view pipelines and run history; cannot create, edit, run, or delete

  Users are stored in `ff_users` (`id`, `username`, `password_hash`, `role`, `created_at`). The legacy `FLOWFORGE_USERNAME` / `FLOWFORGE_PASSWORD` env vars are preserved for single-admin deployments; the DB user table takes precedence when rows exist. ([`flowforge/db/models.py`](flowforge/db/models.py), `flowforge/db/migrations/`)

- **`require_role` decorator** — Applied to every write route in the API. Reads `g.current_user_id` and `g.current_user_role` injected by `require_auth`. Returns `403 Forbidden` for insufficient roles. Cancel and seed endpoints are also guarded. ([`flowforge/api/auth.py`](flowforge/api/auth.py))

- **`GET /api/auth/me`** — Returns the current user's `id`, `username`, and `role`. Used by the frontend to bootstrap the auth context on load. ([`flowforge/api/auth.py`](flowforge/api/auth.py))

- **User management API** — Admin-only endpoints for full user lifecycle:
  - `GET /api/admin/users` — list all users with role and creation date
  - `POST /api/admin/users` — create user (username, password, role)
  - `PUT /api/admin/users/<id>` — update username or role
  - `DELETE /api/admin/users/<id>` — delete user (cannot delete own account)
  - `POST /api/admin/users/<id>/change-password` — force-set any user's password
  - `POST /api/users/me/change-password` — self-service password change (any role)

  ([`flowforge/api/routes/users.py`](flowforge/api/routes/users.py))

- **Users page** — New `/users` frontend page, visible to admins only. Shows a table of all users with role badges, inline role-change selector, and delete buttons. "New User" modal with username, password, and role picker. ([`frontend/src/pages/Users.tsx`](frontend/src/pages/Users.tsx))

- **Role-based UI visibility** — Write actions are hidden for viewers and non-admins throughout the app: "New Pipeline", "Run Now", "Edit", "Delete", "Clone" buttons; all step configuration forms; Connections "Add" button; recipient group, email config, and report create/edit controls. Role is read from the `useCurrentUser` hook which calls `/api/auth/me` once on login. ([`frontend/src/pages/`](frontend/src/pages/))

- **Celery / Redis task queue** — When `FLOWFORGE_REDIS_URL` is set, pipeline runs are dispatched to Celery workers instead of background threads. `FlaskTask` base class (in `celery_app.py`) wraps each task execution in a Flask app context. Worker processes lazily call `create_app()` once via `_get_app()`; the web server process calls `init_celery(app)` on startup, so `create_app()` is never called twice. Thread-based execution is fully retained as a zero-dependency fallback when Redis is not configured. ([`flowforge/celery_app.py`](flowforge/celery_app.py), [`flowforge/tasks.py`](flowforge/tasks.py), [`flowforge/engine/launcher.py`](flowforge/engine/launcher.py))

- **`flowforge worker` CLI command** — `flowforge worker [--concurrency N] [--loglevel LEVEL]` starts a Celery worker via `celery.worker_main()`. Exits with a clear error message if `FLOWFORGE_REDIS_URL` is not set. ([`flowforge/cli.py`](flowforge/cli.py))

### Security

- **Audit log user attribution** — `g.current_user_id` (set by `require_auth`) is now emitted alongside `by=<username>` in all `audit.py` log entries, enabling per-user accountability in the audit trail. ([`flowforge/audit.py`](flowforge/audit.py))

### Changed

- **Responsive / mobile layout** — All pages converted from inline style objects to Tailwind utility classes. Sidebar collapses on narrow viewports. Tables gain horizontal scroll at the `sm` breakpoint. Dashboard and Run History cards reflow to a single column on mobile. ([`frontend/src/`](frontend/src/))

### Tests

- `tests/test_users.py` — user management API: create, list, update, delete, self-delete prevention, force change-password, role validation, duplicate username rejection.
- `tests/test_rbac.py` — role-based access control: viewer blocked on all write routes, editor blocked on user-management routes, admin succeeds on all, unauthenticated requests return 401.
- `tests/test_jwt_expiry.py` — JWT revocation: logout invalidates the token immediately, subsequent requests with the same token return 401, expired tokens are still rejected after logout.

---

## [1.1.0] — 2026-05-24

### Added

- **MySQL / MariaDB connector** — `MySQLConnection` using PyMySQL. Implements the same `BaseConnection` interface as PostgreSQL and Oracle — pipelines require no changes to switch databases. Migration adds `mysql` to the `ck_db_type` check constraint. Install with: `pip install 'flowforge-io[mysql]'`. ([`flowforge/connections/mysql.py`](flowforge/connections/mysql.py))

- **OneDrive upload step** — `onedrive_upload` step type uploads files to Microsoft OneDrive via Microsoft Graph API. Uses a direct PUT for files ≤ 4 MB and chunked upload sessions for larger files. `createLink` generates an anonymous shareable URL stored as `{{ steps.<name>.drive_url }}`. `onedrive_folder_id` added to `ff_email_configs` so the smart-attachment logic routes large attachments to OneDrive when configured, with Google Drive as a fallback. Install with: `pip install 'flowforge-io[microsoft365]'`. ([`flowforge/steps/onedrive_upload.py`](flowforge/steps/onedrive_upload.py), [`flowforge/storage/onedrive.py`](flowforge/storage/onedrive.py))

- **SFTP transfer step** — `sftp_transfer` step type for file transfer over SSH/SFTP. Supports download (single file, directory, or glob pattern) and upload modes. Accepts password or private-key authentication. `create_remote_dirs` auto-creates the destination path on the remote server. Configurable `overwrite` flag and `strict_host_keys` mode (defaults to TOFU for compatibility; set `FLOWFORGE_SFTP_STRICT_HOSTKEYS=true` in production). Uses `paramiko`. Install with: `pip install 'flowforge-io[sftp]'`. ([`flowforge/steps/sftp_transfer.py`](flowforge/steps/sftp_transfer.py))

- **AI analyze step** — `ai_analyze` step type runs an LLM prompt against query results and injects the response into the pipeline context. Two providers:
  - **Ollama** (default) — runs locally, zero cost, no data leaves your machine. Configure via `OLLAMA_URL` and `OLLAMA_QUERY_MODEL`.
  - **Claude API** — Anthropic cloud, pay-per-use, opt-in via `USE_CLAUDE=true` and `ANTHROPIC_API_KEY`.

  `max_rows` caps rows sent to the model to stay within context limits. The LLM response is stored in a named `output_variable` (e.g. `ai_summary`) for use in downstream email bodies or report titles via `{{ ai_summary }}`. Disabled globally with `FLOWFORGE_AI_ENABLED=false`. ([`flowforge/steps/ai_analyze.py`](flowforge/steps/ai_analyze.py))

- **Step retry** — Each pipeline step now accepts a `retry` block: `max_attempts` (default 1, no retry) and `backoff_seconds` (default 5). On failure, the step is retried up to `max_attempts − 1` additional times with configurable back-off before being marked failed. Each attempt is logged with its index and elapsed time. ([`flowforge/engine/runner.py`](flowforge/engine/runner.py))

- **Failure webhook notification** — Pipeline-level `failure_webhook_url` field. When a run ends with `status='failed'`, FlowForge POSTs a JSON payload to the URL: `pipeline_id`, `pipeline_name`, `run_id`, `error_step`, `error_message`, `failed_at`. Useful for alerting via Slack, PagerDuty, or any webhook-capable service. Migration adds the column to `ff_pipelines`. ([`flowforge/engine/runner.py`](flowforge/engine/runner.py))

- **Webhook / API trigger** — External systems can trigger pipelines without a user session. Tokens are managed via `GET / POST / DELETE /api/pipelines/<id>/webhook-tokens` (JWT-protected). Each token is stored as a SHA-256 hash — the plaintext is shown only once at creation. Triggering: `POST /api/pipelines/<id>/trigger?token=<token>` — public endpoint, rate-limited at 30 requests/min per IP, sets `triggered_by='api'` in run history. Adds `ff_webhook_tokens` table. ([`flowforge/api/routes/`](flowforge/api/routes/))

- **Pipeline clone** — `POST /api/pipelines/<id>/clone` creates a full copy of a pipeline including all steps and variables. The clone is created disabled with `(copy)` appended to the name.

- **Pipeline YAML import/export** — `GET /api/pipelines/<id>/export` returns a portable YAML document. `POST /api/pipelines/import` recreates the pipeline in the database, preserving step order and variable config. Useful for migrating pipelines between environments or checking configs into version control.

### Security

- **JWT revocation via server-side blocklist** — Every issued JWT now contains a `jti` (UUID v4) claim. `POST /api/auth/logout` writes the `jti` to the new `ff_token_blocklist` table. All subsequent requests bearing that token are rejected immediately — no need to wait for natural expiry. Mitigates stolen-session scenarios. The frontend Sign Out button calls the logout endpoint first, then clears local storage regardless of the response. ([`flowforge/api/auth.py`](flowforge/api/auth.py), [`flowforge/db/models.py`](flowforge/db/models.py))

- **Separate JWT signing key** — `FLOWFORGE_JWT_SECRET` is now a required, distinct secret from `FLOWFORGE_SECRET_KEY`. Using the same key for AES-256-GCM credential encryption and JWT signing created unnecessary key-reuse risk. Existing deployments must add `FLOWFORGE_JWT_SECRET` to their `.env` (see `.env.example` for the generation command).

- **SAST pipeline (Bandit)** — GitHub Actions CI split into three parallel jobs: `pytest`, `bandit`, and `npm-audit + vitest`. Bandit scans the entire `flowforge/` package on every push and pull request. Configured via `[tool.bandit]` in `pyproject.toml`. Five real security issues fixed during the initial scan (missing `timeout=` on `requests.post/put` calls in `microsoft365.py` and `onedrive.py`). Known false positives suppressed with `# nosec` comments and justification. ([`.github/workflows/test.yml`](.github/workflows/test.yml))

- **npm dependency audit** — `npm audit --audit-level=high` runs as part of the frontend CI job, failing the build on high-severity vulnerabilities.

### Changed

- **PostgreSQL APScheduler jobstore hardened** — `SQLAlchemyJobStore` targets PostgreSQL explicitly. `alembic/env.py` excludes the `apscheduler_jobs` table from autogenerate to prevent spurious DROP TABLE migrations. Startup logging now shows the DB host and database name when the PostgreSQL jobstore is active (credentials stripped). ([`flowforge/engine/scheduler.py`](flowforge/engine/scheduler.py))

- **Audit log stdout mode** — `FLOWFORGE_AUDIT_STDOUT=true` emits structured JSON audit lines to stdout for container log aggregators (Fluentd, Loki, CloudWatch). `FLOWFORGE_AUDIT_FILE=false` suppresses writing to `logs/audit.log`. Both flags default to their original behaviour so existing deployments are unaffected. ([`flowforge/audit.py`](flowforge/audit.py))

- **Serializer consolidation** — `api/serializers.py` introduces canonical `run_dict()` and `step_run_dict()` helpers used by all run-related routes, eliminating inconsistent field naming across endpoints. ([`flowforge/api/serializers.py`](flowforge/api/serializers.py))

- **Input length validation** — `api/validators.py` enforces maximum-length constraints on all string fields accepted by the API (pipeline names, query strings, file paths, etc.), preventing runaway database storage.

### Fixed

- **Oracle connection pool exhaustion** — A new connection pool was created per pipeline step, exhausting Oracle connections on multi-step pipelines. Pool is now keyed by `(host, port, service_name, user, password_hash)` and reused across all steps in the same process. ([`flowforge/connections/oracle.py`](flowforge/connections/oracle.py))

- **Dashboard N+1 query** — The dashboard summary (total runs, success rate, active count) was previously computed by loading every run row. Replaced with a single aggregation query via a dedicated `/api/runs/summary` endpoint. ([`flowforge/api/routes/runs.py`](flowforge/api/routes/runs.py))

### Tests

- 24 frontend unit tests (Vitest + React Testing Library) covering Dashboard, Pipelines list, TopBar, Login, and Connections components.
- 5 Playwright E2E specs: login flow, dashboard, pipeline CRUD, run history, and connections — with global setup/teardown and auth state reuse across specs.
- 38 tests for the `sftp_transfer` step (all auth modes, download/upload paths, glob matching, error handling).
- 27 tests for the `ai_analyze` step (Ollama and Claude provider paths, context injection, `max_rows` cap, output variable propagation).
- 16 additional Jinja2 context variable tests.

---

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
- Oracle via cx_Oracle (optional extra: `pip install flowforge-io[oracle]`)
- Both implement a shared `BaseConnection` interface — pipelines don't know which DB they're talking to
- `execute_query_with_columns()` returns actual column names from `cursor.description`; no more `col0 / col1 / col2` in report headers

#### Report Generation
- Excel via openpyxl — optional `.xlsx` template support, auto-width columns, bold headers
- CSV via Python stdlib — UTF-8 BOM, configurable delimiter
- PDF via WeasyPrint (optional install: `pip install flowforge-io[pdf]`)

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
- `flowforge-io[gmail]` — `google-api-python-client`, `google-auth`, `google-auth-oauthlib`
- `flowforge-io[drive]` — same as `[gmail]`
- `flowforge-io[microsoft365]` — `msal`
- `flowforge-io[oracle]` — `cx_Oracle`
- `flowforge-io[pdf]` — `weasyprint`
- `flowforge-io[dev]` — `pytest`, `pytest-mock`, `responses`, `pytest-cov`

[Unreleased]: https://github.com/jagdeepvirdi/flowforge/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/jagdeepvirdi/flowforge/compare/v0.1.5...v1.0.0
[1.2.0]: https://github.com/jagdeepvirdi/flowforge/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/jagdeepvirdi/flowforge/compare/v0.1.5...v1.1.0
[0.1.5]: https://github.com/jagdeepvirdi/flowforge/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/jagdeepvirdi/flowforge/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/jagdeepvirdi/flowforge/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/jagdeepvirdi/flowforge/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/jagdeepvirdi/flowforge/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/jagdeepvirdi/flowforge/releases/tag/v0.1.0
