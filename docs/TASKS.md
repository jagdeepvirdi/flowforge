# TASKS.md — FlowForge

*Completed tasks are in [TASKS_ARCHIVE.md](TASKS_ARCHIVE.md).*
*Full codebase review with scores in [CODEBASE_REVIEW.md](CODEBASE_REVIEW.md).*

---

## Codebase Review Score: 7.8 / 10 (2026-05-25)

| Dimension | 2026-05-20 | 2026-05-23 | 2026-05-25 | Target (v1.0) |
|---|---|---|---|---|
| Architecture | 6.5 | 7.0 | 7.5 | 8.5 |
| Code Quality | 6.0 | 7.0 | 7.5 | 8.5 |
| Database | 6.5 | 8.0 | 8.5 | 9.0 |
| Security | 5.5 | 7.5 | 7.5 | 8.5 |
| Tests | 6.0 | 7.5 | 8.5 | 9.0 |
| Frontend | 5.5 | 6.5 | 8.0 | 9.0 |
| DevOps | 6.0 | 7.5 | 8.5 | 9.0 |
| **Overall** | **6.0** | **7.3** | **7.8** | **≥ 9.0** |

---

## Release Definition

| Release | Goal |
|---|---|
| **v1.0** | Public GitHub release — stable, tested, `docker compose up` works, badges and docs polished, GTM done |
| **v2.0** | Production-hardening — Gunicorn/scaling docs, metrics, audit UI, retention, dependency audit in CI |
| **v2.x Compliance** | Regulated-environment track — MFA, SSO, GDPR, encryption at rest |
| **v3.0** | New connectors/providers, pipeline DAGs, plugin system |

---

---

# V1.0 RELEASE — REMAINING TASKS

---

## Phase 2 — Code Quality Badges (remaining items)

### 2.1 SonarCloud
- [x] Take a screenshot of the SonarCloud dashboard for LinkedIn post

#### 2.1f Major Code Smells (one remaining)
- [x] Add explicit `{' '}` between inline JSX elements — `Layout.tsx:103,148`, `Projects.tsx:232`, `PipelineEdit.tsx:313`, `BulkLoadEdit.tsx:186`

#### 2.1g Minor Code Smells (remaining)
- [x] Remove unnecessary type assertions (`as SomeType`) — `StepEditor.tsx:37,224,268` (config already typed); `Pipelines.tsx:92` (removed with FileReader refactor); `ReportEdit.tsx:196` (api.ts return type tightened); `ProjectSwitcher.tsx:39`, `FieldTooltip.tsx:18` (replaced with instanceof)
- [x] Fix unexpected negated conditions — `Layout.tsx:195`, `RunDetail.tsx:186`, `BulkLoads.tsx:78`
- [x] Replace `FileReader.readAsText(blob)` with `await blob.text()` — `Pipelines.tsx:88`
- [x] Replace `dict()` / `list()` constructor calls with literals `{}` / `[]` — `sftp_transfer.py:60`

### 2.2 OpenSSF Scorecard
- [ ] Review final Scorecard score after next weekly run (Saturday); target ≥ 7.0

---

## Phase 3 — Documentation Polish (remaining)

### 3.4 Getting-Started Quick Check
- [x] Run through `docs/getting-started.md` end-to-end — verify all commands and screenshots are current
- [ ] Update any screenshots that show old UI (pre-multi-user) *(deferred — no screenshots in docs yet)*

---

---

# V2.0 — TASKS

*Post-release hardening. Starts after v1.0 ships.*

---

## Phase 5 — Go-To-Market (P1 — Visibility)

*These do not block the GitHub release tag but should happen within the first week of release.*

### 5.1 Demo Assets
- [ ] Record a 60–90 second screen recording (GIF or MP4):
  - Open dashboard → create a pipeline with a report + email step → run it → show Run History with logs
- [ ] Capture a high-quality static screenshot of the Dashboard for the README hero and LinkedIn Featured section
- [ ] Add the demo GIF to the README (below the tagline, above the feature list)

### 5.2 ProductHunt Launch
- [ ] Create a ProductHunt account / maker profile
- [ ] Draft the listing:
  - Name: **FlowForge**
  - Tagline: `SQL-to-Email pipeline orchestrator. No YAML. No Airflow complexity.`
  - Description: Explain the problem (50+ cron scripts), the solution, highlight Celery scaling + local AI
  - Gallery: dashboard screenshot + report designer + run history
- [ ] Schedule launch for a Tuesday or Wednesday (highest ProductHunt traffic)

### 5.3 Reddit Posts
- [ ] Post in **r/selfhosted**: "I built an open-source database pipeline orchestrator — SQL → Report → Email, with local AI. No YAML required."
- [ ] Post in **r/Python**: focus on the Flask + Celery + APScheduler architecture choices
- [ ] Post in **r/opensource**: general project introduction with demo GIF
- [ ] Cross-post to **r/dataengineering** focusing on the Oracle + PostgreSQL + MySQL support

### 5.4 Awesome Lists Submission
- [ ] Submit PR to [awesome-selfhosted](https://github.com/awesome-selfhosted/awesome-selfhosted) — category: "Automation"
- [ ] Submit PR to [awesome-python](https://github.com/vinta/awesome-python) — category: "Task Queues" or "Data Pipeline"

### 5.5 LinkedIn
- [ ] Write the launch post:
  - Hook: "Stop writing boilerplate Python scripts for DB automation..."
  - Highlight: Celery/Redis scaling, local AI (Ollama), full audit logging, multi-user roles
  - Tech stack: React + Flask + PostgreSQL + Celery
  - Link to GitHub repo
  - Attach: demo GIF or dashboard screenshot
- [ ] Add FlowForge to LinkedIn "Featured" section with dashboard screenshot and 2-sentence value description
- [ ] Tag: `#OpenSource`, `#Python`, `#LocalAI`, `#DataEngineering`, `#Productivity`

---

## Phase 6 — Production Hardening (P1)

### 6.1 Gunicorn Deployment Guide
- [x] Document `gunicorn --workers 4 --worker-class gevent` in RUNBOOK.md (§4a)
- [x] Explain why Celery is required when running multiple Gunicorn workers
- [x] Add Nginx reverse-proxy config example
- [x] Add systemd units for web, scheduler, and Celery worker (RUNBOOK.md §4a)

### 6.2 SQLAlchemy Pool Tuning
- [x] Document `SQLALCHEMY_POOL_SIZE`, `SQLALCHEMY_MAX_OVERFLOW`, `SQLALCHEMY_POOL_TIMEOUT`, `SQLALCHEMY_POOL_RECYCLE` in `.env.example`
- [x] Add pool settings to `create_app()` from env vars
- [x] Add PgBouncer note in RUNBOOK.md §9

### 6.3 Prometheus Metrics Endpoint
- [x] `GET /api/metrics` — plain-text Prometheus format (no extra dependency)
- [x] Metrics: `flowforge_runs_total{status}`, `flowforge_runs_active`, `flowforge_queue_depth`
- [x] Requires Bearer token auth; documented scrape config + Grafana PromQL in RUNBOOK.md §10

### 6.4 Flower Dashboard (Celery Monitoring)
- [x] `flower` service added to `docker-compose.yml` with `--profile monitoring` (opt-in)
- [x] `FLOWER_BASIC_AUTH` and `FLOWER_PORT` env vars in `.env.example`
- [x] Documented in RUNBOOK.md §11 (Docker Compose + bare-metal + monitoring guide)

### 6.5 Dependency Audit in CI
- [x] `pip-audit` already runs in GitHub Actions `test.yml` — fails on any CVE
- [x] `npm audit --audit-level=high` already runs in `frontend` job
- [x] All `requirements.txt` deps pinned to exact versions ✅

### 6.6 Reliability & Hardening (from Codebase Review)
- [x] **[ARCH-2] Persistent Scheduler Jobstore** — APScheduler already uses `SQLAlchemyJobStore` when `FLOWFORGE_DB_URL` is set; falls back to memory with a warning. Tests confirm both paths.
- [x] **[CODE-3] Drive API Failure Visibility** — `_handle_attachments` now wraps each upload in try/except; failures fall back to direct attachment and are surfaced in Run History step logs via `warnings_out`.
- [x] **[DB-1] Prevent Invisible History** — `PipelineRun.pipeline_id` already uses `ondelete=SET NULL` (nullable); deleting a pipeline preserves all run rows with their denormalized `pipeline_name`.
- [x] **[SEC-3] SQL Sandbox Protection** — `render_sql()` added to `context.py`; warns when secret pipeline variables appear in SQL templates. `_secret_var_keys` stored in context by runner. Used in `db_query` and `report` steps for query rendering.

---

## Phase 7 — Observability & Admin UI

### 7.3 Code Climate Badge (Optional)
- [ ] Set up Code Climate maintainability badge
- [ ] Add to README badge row if grade is A or B

---

## Phase 8 — Compliance Track (P2 — Regulated Environments) ✅ *(COMPLETE 2026-05-30)*

*Required before FlowForge can be deployed in finance, healthcare, or SOC2-reviewed environments.*

### 8.1 Data Protection
- [x] **Report file encryption at rest** — AES-256-GCM via `FLOWFORGE_ENCRYPT_OUTPUT=true`; `crypto.py` gains `encrypt_file()` / `decrypt_file_to_stream()`; `report.py` + `script_report.py` encrypt after generation; download endpoint decrypts `.enc` files transparently
- [x] **Secrets scanning in CI** — `.github/workflows/secrets-scan.yml` using TruffleHog OSS (`--only-verified --fail`) on every push and PR
- [x] **GDPR data export** — `GET /api/admin/users/{id}/export` — user profile, audit log entries, pipeline run history as JSON; Download button in Users UI
- [x] **GDPR data deletion** — `DELETE /api/admin/users/{id}?purge=true` — anonymises audit log (username → `[deleted:...]`, ip_address removed), then deletes user record; GDPR purge button in Users UI

### 8.2 Identity Hardening
- [x] **MFA (TOTP)** — `pyotp` added to deps; DB migration `0020_mfa_sso.py` adds `mfa_secret`, `mfa_enabled`, `mfa_backup_codes` (all AES-256 encrypted); `POST /auth/mfa/enroll|confirm|disable|verify|use-backup`; Login page shows step-2 TOTP input; Settings page shows MFA enrollment card with QR code + 10 backup codes
- [x] **SSO / OAuth2 login** — `GET /api/auth/sso/google|microsoft` + callbacks; `GOOGLE_SSO_CLIENT_ID/SECRET` + `MICROSOFT_SSO_TENANT_ID/CLIENT_ID/SECRET`; `FLOWFORGE_SSO_AUTO_CREATE`; Login page shows SSO buttons when configured; token delivered via `/#sso_token=<jwt>` hash fragment
- [x] **IP allowlisting** — `FLOWFORGE_ALLOWED_IPS=10.0.0.0/8,192.168.1.0/24`; `_register_ip_allowlist()` in `app.py` registers `before_request` handler using stdlib `ipaddress`; invalid CIDRs logged as warnings and skipped

### 8.3 Compliance Documentation
- [x] **Data flow diagram** — `docs/data-flow.md` — full inventory: data types, storage locations, transmission targets, encryption, data retention, GDPR rights, authentication security, audit events, network ports
- [ ] **SAML support** — `python3-saml` for Okta / Azure AD / Ping enterprise IdP *(v2.x, lower priority — deferred)*

---

---

# V3.0 BACKLOG

*No fixed date. Community-driven. Good candidates for "good first issue" labeling.*

## New Connectors & Providers
- [ ] Snowflake / BigQuery / Redshift connectors
- [ ] AWS S3 / Azure Blob upload step
- [x] MSSQL / SQL Server connection support — `connections/mssql.py` via `pyodbc`; `flowforge[mssql]` optional extra *(2026-05-30)*
- [x] Generic ODBC connection support — `connections/odbc.py` via `pyodbc`; DSN or connection string config *(2026-05-30)*
- [ ] SendGrid API email provider
- [ ] AWS SES email provider
- [ ] Mailgun email provider
- [ ] Telegram / Slack / Teams notification step

## Pipeline Features
- [ ] Pipeline dependencies — run pipeline B only after pipeline A succeeds
- [ ] Parallel step execution within a single pipeline
- [ ] Pipeline run diff view — row count and output size delta vs last run
- [ ] Report column formatting rules — number format, date format, conditional cell colours in Excel
- [ ] Environment promotion workflow — dev → staging → prod config sync

## Platform
- [ ] Plugin system — community step types loaded from a directory
- [ ] `ff_project_members` join table — team-scoped project access (deferred from v2)
- [x] Password reset flow via email — `ff_password_reset_tokens` table; `POST /auth/password-reset/request|confirm`, `GET /auth/password-reset/validate/<token>`; user `email` column; "Forgot password?" on Login; Users page shows/sets email *(2026-05-30)*
- [ ] Distributed Redis-backed concurrency lock (replaces per-process semaphore for horizontal scale)

---

## Phase 9 — Automation Scenarios (SSH & Remote Execution)

### 9.1 Infrastructure Support
- [x] **Implement `SSHConnection`** — new connection type to store host, port, credentials (password/key_path)
- [x] **Implement `SshCommandStep`** — execute remote commands/scripts via paramiko; capture stdout/stderr
- [x] **Implement `DbHealthCheckStep`** — industry-standard metrics (Lag, Locks, Bloat, Sessions)
- [x] **Smart Alerting Logic** — add `send_only_on_failure` toggle to pipelines to suppress routine emails
- [x] **Alembic migration** — update `ck_step_type` to include `ssh_command`, `db_health_check`, and `data_report`
- [x] **Implement `ScriptReportStep`** — generate Excel/CSV/PDF from pipeline context variables (e.g. Shell script outputs)

### 9.2 Scenario 1: Industry-Standard Health Monitoring
- [x] **Configure Daily Health Pipeline** — importable YAML templates in `examples/` (daily digest + alerting variant)
- [x] **Standard SSH Metrics**: Load Average, Memory Usage (`free -m`), Disk I/O, and `df -h` — documented in `docs/scenarios/health-monitoring.md`
- [x] **Standard DB Metrics**: PostgreSQL (`pg_stat_activity`, cache hit ratio, replication lag) and Oracle (`v$session`, `v$sysstat`, tablespace usage) — implemented in `DbHealthCheckStep`
- [x] **Conditional Execution**: Threshold-check SSH step exits 1 on breach; `send_only_on_failure: true` suppresses routine emails — documented with example in alerting YAML template

### 9.3 Scenario 2: Remote Script & Log Processing
- [x] **Configure Log Extraction Pipeline** — importable YAML in `examples/log-extraction-pipeline.yaml` (SSH → Report → Email, 3 steps)
- [x] **Log Handling**: `ssh_command` gains `save_output: true` — writes stdout/stderr to a `.log` file and sets `output_path`; attach alongside Excel via `{{ steps.<name>.output_path }}`

---

---

## Known Risks & Mitigations

| Risk | Mitigation |
|---|---|
| ~~cx_Oracle requires Oracle Instant Client~~ | ✅ Migrated to `python-oracledb` (thin mode, pure Python) |
| M365 requires Azure AD app registration | Step-by-step guide in `docs/email-providers.md`; `flowforge setup microsoft365` wizard |
| Gmail OAuth2 token expiry | Refresh token handling; re-auth wizard in Settings |
| Drive folder ID opaque to users | Folder picker in frontend fetches Drive tree via API |
| Smart attachment: Drive upload fails after report generated | Fallback: attach directly if Drive upload fails, log warning |
| Large report query times out in Preview | Preview uses `LIMIT 20` wrapper around user query |
| Oracle LOB columns break row serialization | OracleConnection reads LOB values explicitly before cursor close |
| SonarCloud flags security hotspots | Review each hotspot; most will be acknowledged false positives with justification comments |
