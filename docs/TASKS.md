# TASKS.md — FlowForge

*Completed tasks are in [TASKS_ARCHIVE.md](TASKS_ARCHIVE.md).*
*Full codebase review with scores in [CODEBASE_REVIEW.md](CODEBASE_REVIEW.md).*

---

## Codebase Review Score: 7.8 / 10 (2026-05-25)

| Dimension | 2026-05-20 | 2026-05-23 | Score Track | 2026-05-25 Review | Target |
|---|---|---|---|---|---|
| Architecture | 6.5 | 7.0 | 7.5 ✓ | 7.5 | 8.5 |
| Code Quality | 6.0 | 7.0 | 7.5 ✓ | 7.5 | 8.5 |
| Database | 6.5 | 8.0 | 8.5 ✓ | 8.5 | 9.0 |
| Security | 5.5 | 7.5 | 7.5 ✓ | 7.5 | 8.5 |
| Tests | 6.0 | 7.5 | 8.5 ✓ | 8.5 | 9.0 |
| Frontend | 5.5 | 6.5 | 8.5 ✓ | 8.0 | 9.0 |
| DevOps | 6.0 | 7.5 | 8.5 ✓ | 8.5 | 9.0 |
| **Overall** | **6.0** | **7.3** | **~8.3** | **7.8** | **≥ 9.0** |

---

## Code Review 2026-05-25 — Bug & Feature Track

> Full review scored **7.8 / 10**. CR-1 and CR-2 resolved. Remaining items ordered by phase and priority.

---

### Phase 3 — Backlog (v2+, no fixed date)

*These are real gaps but not blockers for initial open-source release.*

- [ ] Snowflake / BigQuery / Redshift connectors
- [ ] AWS S3 / Azure Blob upload step
- [ ] MSSQL / SQL Server connection support
- [ ] Generic ODBC connection support
- [ ] SendGrid / AWS SES / Mailgun email providers
- [ ] Pipeline dependencies (run pipeline B only after pipeline A succeeds)
- [ ] Parallel step execution within a single pipeline
- [ ] Environment promotion workflow (dev → staging → prod pipeline config sync)
- [ ] Distributed concurrency control (Redis-backed advisory lock replacing in-process semaphore) — see v2 High-Concurrency Track
- [ ] Pipeline run diff view ("what changed since last run" for row counts / output sizes)
- [ ] Report column formatting rules (number format, date format, conditional cell colours in Excel)

---

## Feature Backlog

### More Email Providers
- [ ] SendGrid API
- [ ] AWS SES
- [ ] Mailgun

### More Storage
- [ ] AWS S3 upload step
- [ ] Azure Blob upload step

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
