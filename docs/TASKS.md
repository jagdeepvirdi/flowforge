# TASKS.md — FlowForge

*Completed tasks are in [TASKS_ARCHIVE.md](TASKS_ARCHIVE.md).*
*Full codebase review with scores in [CODEBASE_REVIEW.md](CODEBASE_REVIEW.md).*

---

## GitHub Release Score: 9.5 / 10 (updated 2026-05-23)
## Codebase Review Score: 7.9 / 10 (post NEW-1–10 — estimated)

| Dimension | 2026-05-20 | 2026-05-23 | Post NEW-1–10 | Target (8.5+) |
|---|---|---|---|---|
| Architecture | 6.5 | 7.0 (+0.5) | 7.0 | 7.5 (SCORE-7) |
| Code Quality | 6.0 | 7.0 (+1.0) | 7.0 | 7.5 (SCORE-2) |
| Database | 6.5 | 8.0 (+1.5) | 8.0 | 8.5 (SCORE-8) |
| Security | 5.5 | 7.5 (+2.0) | 7.5 | 7.5 |
| Tests | 6.0 | 7.5 (+1.5) | 7.5 | 8.5 (SCORE-6,11) |
| Frontend | 5.5 | 6.5 (+1.0) | 6.5 | 8.5 (SCORE-1,2,3,10) |
| DevOps | 6.0 | 7.5 (+1.5) | 7.5 | 8.5 (SCORE-4,5) |
| **Overall** | **6.0** | **7.3 (+1.3)** | **7.9 (+0.6)** | **≥ 8.5** |

---

## New Issues — Found in 2026-05-23 Review

*Identified in the latest codebase review. Address before public launch.*

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

---

## Score 8.5+ Track

*Ordered by score impact. Frontend is the biggest lever — it's the lowest-scoring dimension and caps the overall average. Complete SCORE-1 through SCORE-3 first.*

### Frontend (6.5 → 8.5)

- [ ] **[SCORE-1] Loading skeletons** — every data-fetch page currently shows a blank white flash before content arrives. Add `<Skeleton />` components (shadcn/ui or a thin custom implementation using Tailwind `animate-pulse`) to `Dashboard.tsx`, `RunHistory.tsx`, `PipelineEdit.tsx`, `Connections.tsx`, and `BulkLoads.tsx`. Each page should show a shimmer layout that matches its final shape. *Frontend +1.0 — single biggest visual quality gap.*

- [ ] **[SCORE-2] React Hook Form + Zod migration** — CLAUDE.md declares React Hook Form + Zod as the form library, but most forms (`EmailEdit.tsx`, `ReportEdit.tsx`, `DbConnectionForm.tsx`, `EmailProviderForm.tsx`) use `useState` + manual validation. Migrate the highest-traffic forms to `useForm<Schema>()` + `zodResolver`. Eliminates per-field error state variables, makes validation declarative. *Frontend +0.5, Code Quality +0.5.*

- [ ] **[SCORE-3] CSS token variables — replace scattered inline styles** — multiple components use hardcoded hex colours (`#0F1117`, `#1A1D27`, `#F97316`, etc.) outside of Tailwind classes. Audit all files under `frontend/src/` for raw `style={{ ... }}` objects and non-token hex strings; move to CSS custom properties defined in `index.css` and reference via Tailwind config or `var(--color-*)`. *Frontend +0.5 — consistency and maintainability.*

- [ ] **[SCORE-10] React error boundaries** — unhandled render errors crash the entire app with a blank screen. Wrap major routes in an `<ErrorBoundary>` component (React class component pattern; React 19 `use`-based if already on that version) that renders a "Something went wrong — reload" fallback. One global boundary at the router level; optional finer-grained ones around the pipeline step editor. *Frontend +0.5, Architecture +0.25.*

### DevOps (7.5 → 8.5)

- [ ] **[SCORE-4] Log rotation for `audit.log`** — `flowforge/audit.py` writes to `logs/audit.log` with no size cap or rotation. Replace `FileHandler` with `RotatingFileHandler(maxBytes=10*1024*1024, backupCount=5)`. Also add a `LOG_LEVEL` env var to control verbosity without code changes. *DevOps +0.5 — prevents disk-fill in production.*

- [ ] **[SCORE-5] Fix `alembic.ini` hardcoded database URL** — `alembic.ini` contains a `sqlalchemy.url = postgresql://...` placeholder that gets overridden at runtime via `env.py`, but the hardcoded string still exists and confuses new contributors (and some Alembic tooling picks it up before `env.py` runs). Set it to `%(FLOWFORGE_DB_URL)s` and document the pattern, or strip it entirely and add a note that `env.py` handles URL injection from the env var. *DevOps +0.5 — eliminates silent wrong-DB connections for new devs.*

### Tests (7.5 → 8.5)

- [ ] **[SCORE-6] Report generation end-to-end test** — `tests/` has unit tests for individual steps but no test that runs the full chain: execute SQL against a test DB → call `ReportGenerator` → verify a real file is written to disk with the correct format and row count. Add `tests/test_report_e2e.py`: spin up a SQLite (or pg test DB from conftest) with seed data, configure a `ReportConfig`, run it, assert `output_path.exists()` and that the Excel/CSV contains the expected rows. *Tests +0.5.*

- [ ] **[SCORE-11] Bulk load step tests** — `flowforge/steps/bulk_load.py` and `flowforge/bulk_load.py` have zero test coverage. Add `tests/test_bulk_load.py`: write temp CSV files, call `BulkLoadStep.execute()`, verify rows land in a test table. Cover: normal load, `on_no_files='skip'`, `on_no_files='fail'`, footer row stripping. *Tests +0.5.*

### Architecture (7.0 → 7.5)

- [ ] **[SCORE-7] Graceful shutdown — drain in-flight pipeline runs** — the Flask/APScheduler process uses daemon threads for pipeline execution. When the process receives `SIGTERM` (systemd stop, Docker stop), daemon threads are killed instantly, leaving `status='running'` rows in the DB that never resolve. Add a `signal.signal(SIGTERM, ...)` handler in `runner.py` or `cli.py` that: sets a shutdown flag, waits up to 60 s for in-flight runs to finish, then marks any still-running rows as `status='cancelled'` before exiting. Update `flowforge-api.service` in `docs/deployment.md` to set `TimeoutStopSec=90`. *Architecture +0.5 — eliminates ghost "running" runs after restart.*

### Database (8.0 → 8.5)

- [ ] **[SCORE-8] Deleted-pipeline run history visibility** — `ff_pipeline_runs.pipeline_id` is a FK with `ON DELETE CASCADE`, meaning when a pipeline is deleted all its run history vanishes. History should be an append-only audit log. Change the FK to `ON DELETE SET NULL` (migration `0011_pipeline_runs_set_null.py`) and update `RunHistory.tsx` filter logic to show `pipeline_id IS NULL` runs under a "Deleted pipelines" group. The `pipeline_name` column is already denormalized precisely for this case. *Database +0.5.*

---

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
- [x] **Pipeline variables** — Variables card in Pipeline Builder; key/value/secret pairs; `{{ var_key }}` and `{{ vars.var_key }}` in all step configs; secrets encrypted at rest and masked in UI. *(Shipped 2026-05-23)*
- [x] **Bulk file loader step (`bulk_load`)** — Directory scanning, `file_prefix`/`file_prefix_exclude`, PostgreSQL `COPY FROM STDIN`, chunked Python fallback, footer row stripping, archive-after-load, `on_no_files` behaviour, Bulk Loads UI page. *(Shipped 2026-05-23)*

### Platform
- [ ] Plugin system for community step types
- [ ] Slack/Teams notifications (v2)
- [ ] AI analyze step — `flowforge/steps/ai_analyze.py`, Ollama routing, `{{ ai_summary }}` variable — see AI Features track for the full AI roadmap

---

## AI Features — Ollama-Only (Zero Cost, Data Stays Local)

*All features route exclusively through Ollama running locally (`OLLAMA_URL`, default `http://localhost:11434`).  
No data is sent to any external API. Each feature is independently opt-in and degrades gracefully if Ollama is unreachable.*

*Ordered by build priority — earlier items have fewer dependencies and higher immediate ROI.*

| # | Feature | Data sent to Ollama | Privacy risk | Effort |
|---|---|---|---|---|
| AI-1 | AI Chart Generator | column names + ≤50 rows | Low — local only | S |
| AI-2 | SQL Explainer | SQL text only | None | S |
| AI-3 | SQL Optimizer | SQL text only | None | S |
| AI-4 | Pipeline Failure Diagnosis | error message + step config | None | S |
| AI-5 | Data Profiler | column names + sample rows | Low — local only | M |
| AI-6 | Run History Anomaly Alerts | none (stats) / optional narrative | None | M |

---

- [ ] **[AI-1] AI Chart Generator** — "Visualize" button on the Report Preview panel. Sends column names + up to 50 rows to Ollama; Ollama returns a JSON chart config `{ type, x, y, title }`. FlowForge renders it immediately using Recharts (already installed). Supported types: bar, line, area, pie, scatter. User can swap axes or change type manually. Optional: embed as static PNG in email body via `html2canvas`. New Flask endpoint `POST /api/ai/chart-config`; new React component — no DB schema changes needed. *Best first build: self-contained, visually impressive, directly addresses the "understand my data" need.*

- [ ] **[AI-2] SQL Explainer** — "Explain" button in the Report Designer SQL editor. Sends the SQL text only (never row data) to Ollama; returns a plain-English summary of what the query does: joins, filters, aggregations. Also flags obvious problems: missing WHERE clause on large tables, cartesian joins, column name typos. *Zero privacy concern — SQL text contains no user data.*

- [ ] **[AI-3] SQL Optimizer** — "Optimize" button alongside AI-2. Ollama rewrites the query using CTEs, window functions, or index-friendly predicates where applicable. User sees a side-by-side diff of original vs. suggested and can accept or dismiss. Builds on the same `/api/ai/sql` endpoint as AI-2, different prompt.

- [ ] **[AI-4] Pipeline Failure Diagnosis** — "Explain this error" button in the Run Detail page, shown next to the raw error message when a step fails. Sends error text + step type + step config (no row data) to Ollama; returns a human-readable cause and suggested fix. Example: `ORA-01555: snapshot too old` → *"Your query ran longer than the undo retention window. Try reducing the fetch size or scheduling during off-peak hours."* New Flask endpoint `POST /api/ai/explain-error`.

- [ ] **[AI-5] Data Profiler** — "Summarise" button on the Report Preview panel, shown after the user runs a preview query and sees rows. Sends column names + sample rows to Ollama; returns a short narrative: value ranges, null counts, outliers, duplicate key suspicion. Opt-in per session with a visible banner: *"Sample rows will be processed by your local Ollama instance."* Helps users confirm the query is correct before attaching it to a pipeline that emails 200 people.

- [ ] **[AI-6] Run History Anomaly Alerts** — Statistical outlier detection on `rows_affected` and `duration_ms` per step across the last 30 runs (no LLM required for detection). When a step result is >2σ outside its normal range, show a warning badge in the Run Detail page. Ollama optionally generates a one-sentence narrative: *"Load Customer Extract wrote 847 rows — 94% below its 30-run average of 13,200. Check upstream data load."* The statistical layer ships first; the Ollama narrative is additive.

### Shared Implementation Notes

- Recommended model: `llama3.2:3b` or `mistral:7b` for SQL/text tasks; `phi3:mini` if RAM is constrained.
- All AI calls are best-effort: if Ollama is unreachable the button shows *"AI unavailable — is Ollama running?"* and the rest of the UI is unaffected.
- A single `POST /api/ai/query` endpoint (with a `task` field) handles AI-2/3/4 to avoid endpoint sprawl. AI-1 and AI-5 have dedicated endpoints due to different input/output shapes.

---

## v2 Track — Multi-User Support

*Required before FlowForge can be used by teams where more than one person logs in.*

### Auth & Identity
- [ ] `ff_users` table — add `role` column: `admin | editor | viewer`
- [ ] `ff_project_members` join table — user X can access Project A but not Project B
- [ ] Switch JWT from single-user (env-var admin) to user-id-bearing tokens; store `user_id` in every JWT claim
- [ ] Server-side token revocation — `jti` UUID per token, revocation table in DB (or Redis set); `/api/auth/logout` endpoint invalidates current token
- [ ] Password reset flow — `POST /auth/forgot-password` → email token → `POST /auth/reset-password`
- [ ] User management UI page — list users, invite, change role, deactivate; admin only

### Role-Based Access Control
- [ ] **Admin** — full access: manage connections, email providers, all projects, all users
- [ ] **Editor** — create/edit/run pipelines, reports, emails in assigned projects; cannot manage connections or users
- [ ] **Viewer** — read-only: view runs, download reports, no config changes
- [ ] Permission guards on every API route — decorator `@require_role('editor')` pattern
- [ ] Permission guards in frontend — hide/disable buttons based on user role from `/api/auth/me`
- [ ] Audit log — attach `user_id` to every existing audit event so every action is attributable

### Effort estimate: 3–5 days backend + 2–3 days frontend UI

---

## v2 Track — High-Concurrency Support

*Required before FlowForge can reliably handle 50+ simultaneous pipeline runs or horizontal scaling.*

### Task Queue (biggest change)
- [ ] **Replace `threading.Thread` with Celery** — install `celery[redis]`; move `_run_in_background` to a Celery task; remove `_semaphore` (Celery worker concurrency controls this)
- [ ] **Add Redis service to `docker-compose.yml`** — broker for Celery; also used for rate-limiter storage and token revocation set
- [ ] **Celery worker service in `docker-compose.yml`** — separate container running `celery -A flowforge.worker worker`
- [ ] **Flower dashboard** (optional but recommended) — `celery -A flowforge.worker flower`; real-time task monitoring
- [ ] **Retry support** — Celery `autoretry_for`, `max_retries`, `countdown` — per-step retry with exponential backoff

### Scheduler
- [ ] **Switch APScheduler to PostgreSQL jobstore** — already designed for; set `SQLALCHEMY_JOB_STORE=True`; prevents duplicate job execution when multiple API workers run
- [ ] **Remove in-memory `_sync_pipeline_jobs`** — no longer needed once jobstore is durable

### API & Infrastructure
- [ ] **Gunicorn multi-worker deployment** — document `gunicorn -w 4 wsgi:app`; in-memory semaphore doesn't work across workers (resolved by Celery)
- [ ] **PgBouncer or SQLAlchemy pool tuning** — prevent DB connection exhaustion under load; document `pool_size`, `max_overflow` settings
- [ ] **Metrics endpoint** — `GET /api/metrics` returning Prometheus-compatible counters: runs queued, running, succeeded, failed; worker count; queue depth
- [ ] **Graceful shutdown** — `SIGTERM` handler drains in-flight tasks before exit; update `flowforge.ps1` / `flowforge.sh` stop logic

### Effort estimate: Celery migration alone ~1 week; rest is configuration (1–2 days)

---

## v2 Track — Regulated Environments (Compliance / SOC2 / GDPR)

*Required before FlowForge can be deployed in finance, healthcare, or any environment with a compliance review.*

### Audit & Logging
- [ ] **Complete audit log** — currently only pipeline start/end and login are logged; add:
  - Connection created / modified / deleted (who, when, what changed)
  - Email provider setup / modified
  - Email sent (pipeline, step, recipient list, attachment names)
  - Report generated (pipeline, step, output filename, row count)
  - User login / logout / failed login (already partial)
  - Config changes by any user
- [ ] **Structured audit log** — switch from plain text `logs/audit.log` to structured JSON lines; include `user_id`, `ip`, `action`, `resource_id`, `timestamp`
- [ ] **Log rotation** — `RotatingFileHandler` (10MB × 5 files) or ship to external log aggregator
- [ ] **Audit log UI page** — admin-only view of recent audit events with filters (user, action type, date range)
- [ ] **Retention policies** — configurable auto-purge of `ff_pipeline_runs` / `ff_step_runs` / audit log after N days; `flowforge cleanup --runs-older-than 90d`

### Identity & Access Hardening
- [ ] **MFA (TOTP)** — time-based one-time password via `pyotp`; QR code enrollment in Settings; enforced per-user or globally by admin
- [ ] **SSO / OAuth2 login** — "Sign in with Google" or "Sign in with Microsoft" using the MSAL library already installed; map to internal user records
- [ ] **SAML support** — `python3-saml` for enterprise IdP integration (Okta, Azure AD, Ping)
- [ ] **IP allowlisting** — global or per-project; `FLOWFORGE_ALLOWED_IPS` env var; reject requests outside the list at the API middleware level

### Data Protection
- [ ] **Report file encryption at rest** — encrypt output files on disk with the `FLOWFORGE_SECRET_KEY`; decrypt on download; prevents data exposure if server storage is compromised
- [ ] **Secrets scanning in CI** — add `detect-secrets` or `truffleHog` GitHub Action to prevent credential commits
- [ ] **SAST in CI** — add `bandit` (Python) and `eslint-plugin-security` (TypeScript) to the GitHub Actions workflow
- [ ] **GDPR data export** — `GET /api/admin/export-user-data?user_id=...` — export all pipeline configs, run history, and audit events for a user
- [ ] **GDPR data deletion** — `DELETE /api/admin/users/{id}` — anonymize run history, remove credentials, delete user record

### Compliance Documentation
- [ ] **Security policy doc** — `docs/security.md`: credential encryption details, key rotation procedure, access control model, incident response contacts
- [ ] **Data flow diagram** — what data touches FlowForge (query results, report files, email addresses) and where it is stored/transmitted
- [ ] **Dependency audit** — `pip-audit` + `npm audit` in CI; fail build on critical CVEs

### Effort estimate: 3–4 weeks for the full list; audit log + RBAC + MFA covers 80% of most internal compliance reviews

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
