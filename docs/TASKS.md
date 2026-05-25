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

## Multi-User Feature — Active Sprint

> Foundation already in place: `ff_users` + `role` column, `require_role` decorator, `ff_token_blocklist`, `ff_projects`. Cutting `ff_project_members` and password-reset (v3). Estimated: ~3 days backend + 1.5 days frontend.

### MU-1 — JWT carries `user_id` + `/api/auth/me` *(backend)*
- [ ] `auth.py:generate_token` — include `user_id` in JWT payload (role already present)
- [ ] `require_auth` — expose `g.current_user_id` after token decode (for audit log use)
- [ ] `GET /api/auth/me` — return `{ id, username, role }` for the current token
- [ ] Tests: verify `/api/auth/me` returns correct fields; verify old tokens without `user_id` are rejected cleanly

### MU-2 — User management API *(backend)*
- [ ] `POST /api/users` — create user: `{ username, password, role }` — admin only
- [ ] `GET /api/users` — list all users (id, username, role, created_at) — admin only
- [ ] `PATCH /api/users/{id}` — update role or username — admin only; cannot demote self
- [ ] `DELETE /api/users/{id}` — delete user — admin only; cannot delete self
- [ ] `POST /api/auth/change-password` — `{ current_password, new_password }` — any authenticated user
- [ ] Tests for all five endpoints (auth, role checks, self-protection guards)

### MU-3 — `@require_role` guards on all remaining routes *(backend)*
- [ ] `pipelines.py` — create/update/delete/run/clone → `require_role(['admin','editor'])`; GET → `require_auth`
- [ ] `reports.py` — create/update/delete → `require_role(['admin','editor'])`; GET → `require_auth`
- [ ] `emails.py` — create/update/delete → `require_role(['admin','editor'])`; GET → `require_auth`
- [ ] `recipients.py` — create/update/delete → `require_role(['admin','editor'])`; GET → `require_auth`
- [ ] `runs.py` — cancel → `require_role(['admin','editor'])`; GET/list → `require_auth`
- [ ] `providers.py` — already done (admin only for write); verify read routes
- [ ] `connections.py` — already done; verify read routes
- [ ] Tests: spot-check that viewer token gets 403 on write routes, 200 on reads

### MU-4 — Audit log `user_id` attribution *(backend)*
- [ ] `audit.py` — read `g.current_user_id` (set by `require_auth`) and include in every log entry
- [ ] Verify structured log lines contain `user_id` field for all existing audit calls
- [ ] No new migrations needed — audit log is file-based

### MU-5 — Frontend role context *(frontend)*
- [ ] `lib/api.ts` — add `getMe(): Promise<{ id, username, role }>` calling `GET /api/auth/me`
- [ ] Zustand `useAuthStore` — add `user: { id, username, role } | null`; populate on login and app load
- [ ] `useCurrentUser()` hook — convenience wrapper over the store
- [ ] Call `getMe()` in app bootstrap (e.g. `App.tsx` effect) so role is always available

### MU-6 — User management UI *(frontend)*
- [ ] New page `src/pages/Users.tsx` — admin-only; redirect non-admins to dashboard
- [ ] Add route `/settings/users` in `App.tsx`; add nav item in `Layout.tsx` (visible to admins only)
- [ ] Users table: username, role badge, "Change Role" dropdown, "Delete" button
- [ ] "Add User" slide-over: username + password + role selector → `POST /api/users`
- [ ] "Change Password" section in Settings page (self-service, any user)

### MU-7 — Frontend role-based visibility *(frontend)*
- [ ] Connections page — hide "Add Connection", "Delete" for non-admins
- [ ] Providers page — hide "Add Provider", "Delete" for non-admins
- [ ] Pipelines — hide "New Pipeline", edit/delete/clone actions for viewers
- [ ] Dashboard — hide "Run Now" button for viewers
- [ ] Reports / Emails / Recipients — hide create/edit/delete for viewers
- [ ] Use `useCurrentUser().role` — no API calls, instant from store

---

## Critical Action Items (Post-Review May 2026)

### P0 — UX & Confidence
- [ ] **Mobile/Responsive**: Fix the layout breakage on screens smaller than 1200px.

### P1 — Technical Debt & Scalability
- [ ] **Frontend Refactor**: Replace inline `style={{...}}` with Tailwind CSS classes or CSS modules — 574 occurrences across 15 files (`Dashboard.tsx`, `PipelineEdit.tsx`, `Layout.tsx` and others).
- [ ] **Task Queue (v2)**: Migrate from daemon threads to Celery/Redis for reliable execution.

### P1 — Security & Compliance
- [ ] **RBAC**: *(In progress — see Multi-User Sprint above)*
- [ ] **Audit log `user_id` attribution**: *(In progress — MU-4)*

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
- [ ] MSSQL / SQL Server
- [ ] Generic ODBC

### Pipeline Features
- [ ] Pipeline dependencies (run B after A)
- [ ] Parallel step execution

### Platform
- [ ] Plugin system for community step types
- [ ] Slack/Teams notifications (v2)

---

## v2 Track — Multi-User Support

*Required before FlowForge can be used by teams where more than one person logs in.*

### Auth & Identity
- [x] `ff_users` table — `role` column added (migration 0018) ✅
- [x] `require_role` decorator in `auth.py` ✅
- [x] `ff_token_blocklist` table for server-side revocation ✅
- [ ] JWT carries `user_id` — see MU-1
- [ ] User management API + UI — see MU-2 / MU-6
- [ ] `ff_project_members` join table — deferred to v3
- [ ] Password reset flow — deferred to v3

### Role-Based Access Control
- [x] `@require_role('admin')` on connections (create/delete) and providers ✅
- [ ] Guards on all remaining routes — see MU-3
- [ ] Frontend role visibility — see MU-5 / MU-7
- [ ] Audit log `user_id` — see MU-4

### Effort estimate: ~3 days backend + 1.5 days frontend (scoped, project-member access deferred)

---

## v2 Track — High-Concurrency Support

*Required before FlowForge can reliably handle 50+ simultaneous pipeline runs or horizontal scaling.*

### Task Queue (biggest change)
- [ ] **Replace `threading.Thread` with Celery** — install `celery[redis]`; move `_run_in_background` to a Celery task; remove `_semaphore` (Celery worker concurrency controls this)
- [ ] **Add Redis service to `docker-compose.yml`** — broker for Celery; also used for rate-limiter storage and token revocation set
- [ ] **Celery worker service in `docker-compose.yml`** — separate container running `celery -A flowforge.worker worker`
- [ ] **Flower dashboard** (optional but recommended) — `celery -A flowforge.worker flower`; real-time task monitoring

### Scheduler
- [x] **APScheduler PostgreSQL jobstore** — `SQLAlchemyJobStore` in `scheduler.py`; jobs survive restarts ✅
- [x] **Remove dead `_load_pipeline_jobs`** — replaced by `_sync_pipeline_jobs` + jobstore ✅

### API & Infrastructure
- [ ] **Gunicorn multi-worker deployment** — document `gunicorn -w 4 wsgi:app`; in-memory semaphore doesn't work across workers (resolved by Celery)
- [ ] **PgBouncer or SQLAlchemy pool tuning** — prevent DB connection exhaustion under load; document `pool_size`, `max_overflow` settings
- [ ] **Metrics endpoint** — `GET /api/metrics` returning Prometheus-compatible counters: runs queued, running, succeeded, failed; worker count; queue depth
- [x] **Graceful shutdown** — `flowforge/engine/shutdown.py`; `SIGTERM` handler + `atexit`; `TimeoutStopSec=90` in systemd units ✅

### Effort estimate: Celery migration alone ~1 week; rest is configuration (1–2 days)

---

## v2 Track — Regulated Environments (Compliance / SOC2 / GDPR)

*Required before FlowForge can be deployed in finance, healthcare, or any environment with a compliance review.*

### Audit & Logging
- [x] **Audit log completeness** — login, pipeline events, connection/provider config changes all logged ✅
- [x] **Structured audit stdout** — `FLOWFORGE_AUDIT_STDOUT=true` emits JSON lines via `_JsonStdoutHandler` ✅
- [x] **Log rotation** — `RotatingFileHandler` (10 MB × 5 backups) in `audit.py` ✅
- [ ] **`user_id` in every audit entry** — *(In progress — MU-4)*
- [ ] **Audit log UI page** — admin-only view with filters (user, action type, date range)
- [ ] **Retention policies** — configurable auto-purge of `ff_pipeline_runs` / `ff_step_runs` / audit log after N days

### Identity & Access Hardening
- [ ] **MFA (TOTP)** — time-based one-time password via `pyotp`; QR code enrollment in Settings; enforced per-user or globally by admin
- [ ] **SSO / OAuth2 login** — "Sign in with Google" or "Sign in with Microsoft" using the MSAL library already installed; map to internal user records
- [ ] **SAML support** — `python3-saml` for enterprise IdP integration (Okta, Azure AD, Ping)
- [ ] **IP allowlisting** — global or per-project; `FLOWFORGE_ALLOWED_IPS` env var; reject requests outside the list at the API middleware level

### Data Protection
- [ ] **Report file encryption at rest** — encrypt output files on disk with the `FLOWFORGE_SECRET_KEY`; decrypt on download
- [ ] **Secrets scanning in CI** — add `detect-secrets` or `truffleHog` GitHub Action to prevent credential commits
- [x] **SAST in CI** — `bandit` (Python) + `npm audit` in GitHub Actions CI ✅
- [ ] **GDPR data export** — `GET /api/admin/export-user-data?user_id=...`
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
