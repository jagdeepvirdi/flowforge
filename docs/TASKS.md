# TASKS.md — FlowForge

*Completed tasks are in [TASKS_ARCHIVE.md](TASKS_ARCHIVE.md).*
*Full codebase review with scores in [CODEBASE_REVIEW.md](CODEBASE_REVIEW.md).*

---

## GitHub Release Score: 9.5 / 10 (updated 2026-05-23)
## Codebase Review Score: ~8.5 / 10 (estimated post Score Track)

| Dimension | 2026-05-20 | 2026-05-23 | Score Track | Target |
|---|---|---|---|---|
| Architecture | 6.5 | 7.0 | 7.5 ✓ (SCORE-7) | 7.5 |
| Code Quality | 6.0 | 7.0 | 7.5 ✓ (SCORE-2) | 7.5 |
| Database | 6.5 | 8.0 | 8.5 ✓ (SCORE-8) | 8.5 |
| Security | 5.5 | 7.5 | 7.5 ✓ | 7.5 |
| Tests | 6.0 | 7.5 | 8.5 ✓ (SCORE-6,11) | 8.5 |
| Frontend | 5.5 | 6.5 | 8.5 ✓ (SCORE-1,2,3,10) | 8.5 |
| DevOps | 6.0 | 7.5 | 8.5 ✓ (SCORE-4,5) | 8.5 |
| **Overall** | **6.0** | **7.3** | **~8.3** | **≥ 8.5** |

---

## Bug Fix Track — Code Review 2026-05-24

*14 issues identified in full code review. Ordered by severity.*

### Critical

- [x] **BUG-1: `bulk_load.py:201` — `_resolve_connection` crashes at runtime** — replaced broken `.items()` dict-comprehension with `decrypt_config(row.config)`.
- [x] **BUG-2: `bulk_load.py:281,343` — SQL injection via CSV column headers** — added `validate_identifier()` call on every mapped column name in both `_load_python_fallback` and `_load_postgres_copy`.
- [x] **BUG-3: `bulk_load.py:418` — Oracle password exposed in process list** — credentials written to a `load.par` tempfile (chmod 600); `sqlldr parfile=…` used instead of inline `user/pass@dsn` arg; tempdir cleaned up in finally block.
- [x] **BUG-4: DB constraint / step type mismatch** — migration 0011 adds `data_load` and `bulk_load` to `ck_step_type`; removes `ai_analyze` (no implementation yet). Model updated to match.
- [x] **BUG-5: `context.py:47` — Jinja2 is not sandboxed + full `os.environ` in context** — switched to `SandboxedEnvironment`; `ctx['env']` now uses `_SafeEnv` proxy that blocks credential vars (`FLOWFORGE_SECRET_KEY`, `FLOWFORGE_PASSWORD`, `*_CLIENT_SECRET`, etc.).

### High

- [x] **BUG-6: `audit.py:20` — Audit log silenced when `LOG_LEVEL=WARNING`** — removed `_LEVEL` variable; `_get_logger()` now hardcodes `logging.INFO` so audit events are always written regardless of `LOG_LEVEL`.
- [x] **BUG-7: `runs.py:93` — No path containment check on file download** — `abs_path` and `output_root` are both `.resolve()`d; a 403 is returned if `abs_path` does not start with `output_root + os.sep`.
- [x] **BUG-8: `context.py:115` — Pipeline variables silently overwrite built-ins** — added `_BUILT_IN_VAR_KEYS` frozenset; `build()` logs a `WARNING` listing any collision before applying `ctx.update(pipeline_vars)`.
- [x] **BUG-9: `app.py` — No `MAX_CONTENT_LENGTH`** — `app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024` added in `create_app()`.
- [x] **BUG-10: `scheduler.py:97` — Dead function `_load_pipeline_jobs`** — function removed; `check_scheduler.py` section 7 updated to query the DB directly.

### Medium

- [x] **BUG-11: `models.py:273` — `TokenBlocklist` grows unbounded** — added `_prune_token_blocklist()` to `scheduler.py`; called from the existing daily `_cleanup_job`. Deletes all rows where `expires_at < NOW()` inside an app context.
- [x] **BUG-12: `steps.py:88` — Step reorder magic number can violate unique constraint** — replaced `999999` with `-old_order` (guaranteed negative, never collides with a positive step order); added `.with_for_update()` to the occupant query to prevent concurrent swap races.
- [x] **BUG-13: `bulk_load.py:343` — Delimiter injected into COPY SQL string literal** — `delimiter` is validated in `BulkLoadStep.run()` before any SQL is constructed: must be exactly one printable character and not a quote or backslash.
- [x] **BUG-14: `report.py:38` — Excel template path unrestricted** — added `_resolve_template_path()` helper: joins `raw` against `FLOWFORGE_TEMPLATE_DIR` (default `./templates`), resolves both, and raises `ValueError` if the result escapes the root.

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

- [x] **[AI-1] AI Chart Generator** — "Visualize" button on the Report Preview panel. Sends column names + up to 50 rows to Ollama; Ollama returns a JSON chart config `{ type, x, y, title }`. FlowForge renders it immediately using Recharts (already installed). Supported types: bar, line, area, pie, scatter. User can swap axes or change type manually. New Flask endpoint `POST /api/ai/chart-config`; new `ChartPreview` React component — no DB schema changes needed.

- [x] **[AI-2] SQL Explainer** — "Explain" button in the Report Designer SQL editor header. Sends SQL text only to Ollama via `POST /api/ai/query` (`task: explain`); returns structured plain-text summary (tables/joins, filters, aggregations, potential issues). Dismissible panel below SQL editor.

- [x] **[AI-3] SQL Optimizer** — "Optimize" button alongside AI-2. Ollama rewrites the query (uses JSON mode for reliable SQL extraction). Side-by-side diff panel: original (red tint) vs suggested (green tint). Accept replaces textarea; Dismiss closes panel.

- [x] **[AI-4] Pipeline Failure Diagnosis** — "Explain this error" button in the Run Detail Logs tab, shown per failed step under the error message. Sends `step_type + error + logs` to Ollama via `POST /api/ai/query` (`task: diagnose`). Returns 2-4 sentence plain-English cause + fix. Diagnosis panel is per-step, dismissible, shows "via Ollama" label.

- [x] **[AI-5] Data Profiler** — "Summarise" button in the TopBar (visible after preview runs). One-time opt-in banner per session: "Your preview rows will be sent to your local Ollama instance. No data leaves your machine." After consent, calls `POST /api/ai/data-profile`; returns a 3-5 sentence narrative (structure, value ranges, nulls, outliers, key suspicion). Profile card dismissible, clears on query re-run, consent persists for the session.

- [x] **[AI-6] Run History Anomaly Alerts** — Statistical outlier detection on `rows_affected` and `duration_ms` per step across the last 30 runs (no LLM required for detection). When a step result is >2σ outside its normal range, show a warning badge in the Run Detail page. Ollama optionally generates a one-sentence narrative: *"Load Customer Extract wrote 847 rows — 94% below its 30-run average of 13,200. Check upstream data load."* The statistical layer ships first; the Ollama narrative is additive.

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
