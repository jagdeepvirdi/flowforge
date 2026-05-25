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

# V1.0 RELEASE — TASKS

*Everything here must be done before tagging and publishing the GitHub v1.0.0 release.*

---

## Phase 1 — Code Stability (P0 — Release Blockers)

*The release cannot ship until these pass.*

### 1.1 Celery End-to-End Verification ✅ COMPLETE
- [x] Start Redis + `flowforge worker`, trigger a pipeline via the API/UI *(verified by `verify_celery.py`, commit `23dac3f`)*
- [x] Confirm worker picks up the task and writes to `ff_pipeline_runs` + `ff_step_runs` *(verified by `verify_celery.py`)*
- [x] Confirm fallback (no `FLOWFORGE_REDIS_URL`) still runs pipeline in thread mode *(verified by `verify_celery.py`)*
- [x] Confirm scheduler-triggered runs also flow through Celery correctly *(Test 3 in `verify_celery.py` — `triggered_by='scheduler'`, `status='success'`, 1 StepRun written)*

---

## Phase 2 — Code Quality Badges (P1 — Trust Signals)

*These badges appear at the top of the README and immediately signal project maturity to visitors and recruiters.*

### 2.1 SonarCloud (Highest Priority Badge)
- [ ] Create a SonarCloud account and link the GitHub repo (free for open source)
- [ ] Add `sonarcloud.yml` GitHub Action to scan on every push
- [ ] Fix any critical / blocker issues SonarCloud flags before release
- [ ] Add badges to README: **Quality Gate**, **Bugs**, **Technical Debt**
- [ ] Take a screenshot of the SonarCloud dashboard for LinkedIn post

### 2.2 OpenSSF Scorecard (Security Credibility)
- [ ] Enable the Scorecard GitHub Action (`.github/workflows/scorecard.yml`)
- [ ] Review and fix the top-scoring checks: branch protection, signed commits, dependency pinning
- [ ] Add **Scorecard** badge to README
- [ ] Target score ≥ 7.0 / 10

### 2.3 OpenSSF Best Practices Badge (Self-Certification)
- [ ] Complete the self-certification questionnaire at bestpractices.dev
- [ ] Achieve at minimum the **Passing** tier
- [ ] Add **OpenSSF Best Practices** badge to README

### 2.4 Codecov (Test Coverage Visibility)
- [ ] Add `codecov.yml` and upload step to GitHub Actions CI
- [ ] Add **Coverage** badge to README
- [ ] Target ≥ 80% coverage (currently strong — 742+ tests)

### 2.5 README Badge Row
- [ ] Finalize the badge row at the top of README:
  `Tests | SonarCloud Quality Gate | Scorecard | OpenSSF Passing | Coverage`

---

## Phase 3 — Documentation Polish (P1 — Contributor Readiness)

### 3.1 CONTRIBUTING.md — Fast Setup (<5 minutes)
- [ ] Verify the local dev setup section works end-to-end in under 5 minutes
- [ ] Add a "Quick Dev Setup" section at the top (before the full guide):
  ```bash
  git clone ... && cd flowforge
  cp .env.test.example .env.test
  pip install -e ".[dev]"
  flowforge db upgrade && flowforge db seed
  cd frontend && npm install && npm run dev
  ```
- [ ] Add a "Running Tests" one-liner: `pytest tests/` and `npx vitest`

### 3.2 docs/security.md (New File)
- [ ] Credential encryption: AES-256-GCM, key derivation, where keys are stored
- [ ] JWT: signing secret separation, token lifetime, revocation via blocklist
- [ ] Access control model: role table, `require_role` decorator, frontend gating
- [ ] Audit log: what is logged, where it goes, rotation policy
- [ ] Key rotation procedure: how to rotate `FLOWFORGE_SECRET_KEY` without data loss
- [ ] Incident response: who to contact, how to report a vulnerability (`SECURITY.md`)

### 3.3 SECURITY.md (New File — GitHub Standard)
- [ ] Create `SECURITY.md` at repo root — GitHub recognizes this and links it in the Security tab
- [ ] Content: supported versions table, how to report a vulnerability (email or GitHub private advisory), response SLA

### 3.4 Getting-Started Quick Check
- [ ] Run through `docs/getting-started.md` end-to-end — verify all commands and screenshots are current
- [ ] Update any screenshots that show old UI (pre-multi-user)

---

## Phase 4 — GitHub Release Preparation ✅ COMPLETE

### 4.1 GitHub Release ✅
- [x] CI green (842 tests passing — fixed `test_unreadable_file_counts_as_error` Linux compat, commit `66a8aef`)
- [x] Tag pushed: `v1.0.0`
- [x] GitHub Release published: https://github.com/jagdeepvirdi/flowforge/releases/tag/v1.0.0 — marked Latest

### 4.2 Good First Issues ✅
- [x] 5 issues created (#1–#5), all labeled `good first issue`
- [x] `help wanted` added to issues #2, #3, #5

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

---

# V2.0 — TASKS

*Post-release hardening. Starts after v1.0 ships.*

---

## Phase 6 — Production Hardening (P1)

### 6.1 Gunicorn Deployment Guide
- [ ] Document `gunicorn -w 4 -k gevent flowforge.api.app:create_app()` in RUNBOOK.md
- [ ] Explain why Celery is required when running multiple Gunicorn workers
- [ ] Add Nginx reverse-proxy config example
- [ ] Add systemd unit for Gunicorn (alongside existing scheduler unit)

### 6.2 SQLAlchemy Pool Tuning
- [ ] Document `SQLALCHEMY_POOL_SIZE`, `SQLALCHEMY_MAX_OVERFLOW`, `SQLALCHEMY_POOL_TIMEOUT` in `.env.example`
- [ ] Add pool settings to `create_app()` from env vars
- [ ] Add PgBouncer note for deployments with 100+ concurrent pipelines

### 6.3 Prometheus Metrics Endpoint
- [ ] `GET /api/metrics` — plain-text Prometheus format
- [ ] Counters: `flowforge_runs_total{status}`, `flowforge_runs_active`, `flowforge_queue_depth`
- [ ] Expose via `prometheus_client` library (add to requirements)
- [ ] Document scrape config for Grafana / Prometheus stack

### 6.4 Flower Dashboard (Celery Monitoring)
- [ ] Add `flower` service to `docker-compose.yml` (port 5555)
- [ ] Add `FLOWER_BASIC_AUTH` env var for basic auth protection
- [ ] Document in RUNBOOK.md

### 6.5 Dependency Audit in CI
- [ ] Add `pip-audit` step to GitHub Actions — fail on CRITICAL CVEs
- [ ] `npm audit --audit-level=high` already runs; confirm it fails the build correctly
- [ ] Pin all dependencies to exact versions in `requirements.txt` (currently pinned ✅ — verify)

### 6.6 Audit Log `user_id` Attribution
- [ ] Emit `user_id=<uuid>` alongside `by=<username>` in `audit.py` entries
- [ ] Read from `g.current_user_id` (set by `require_auth` since MU-1)

---

## Phase 7 — Observability & Admin UI (P1)

### 7.1 Audit Log UI Page
- [ ] New page `/settings/audit` — admin-only
- [ ] Reads from `logs/audit.log` (or a dedicated `ff_audit_log` DB table — decide approach)
- [ ] Filters: user, action type (`LOGIN`, `PIPELINE_*`, `CONFIG_*`), date range
- [ ] Export to CSV

### 7.2 Run Retention Policies
- [ ] Add `FLOWFORGE_RUN_RETENTION_DAYS` env var (default: 90)
- [ ] Daily cleanup job in `scheduler.py` — delete `ff_pipeline_runs` + cascading `ff_step_runs` older than N days
- [ ] UI setting in Settings page: "Keep run history for N days"
- [ ] Audit log retention: separate `FLOWFORGE_AUDIT_RETENTION_DAYS` env var

### 7.3 Code Climate Badge (Optional)
- [ ] Set up Code Climate maintainability badge
- [ ] Add to README badge row if grade is A or B

---

## Phase 8 — Compliance Track (P2 — Regulated Environments)

*Required before FlowForge can be deployed in finance, healthcare, or SOC2-reviewed environments.*

### 8.1 Data Protection
- [ ] **Report file encryption at rest** — encrypt output files using `FLOWFORGE_SECRET_KEY`; decrypt transparently on download
- [ ] **Secrets scanning in CI** — add `detect-secrets` or `truffleHog` GitHub Action; block commits with credential patterns
- [ ] **GDPR data export** — `GET /api/admin/users/{id}/export` — all run history, pipeline config, and personal data for a user
- [ ] **GDPR data deletion** — `DELETE /api/admin/users/{id}?purge=true` — anonymize run history, remove credentials, delete user record

### 8.2 Identity Hardening
- [ ] **MFA (TOTP)** — `pyotp`; QR code enrollment in Settings; per-user or globally enforced by admin; backup codes
- [ ] **SSO / OAuth2 login** — "Sign in with Google" or "Sign in with Microsoft" using existing MSAL; map to internal user records by email
- [ ] **IP allowlisting** — `FLOWFORGE_ALLOWED_IPS=10.0.0.0/8,192.168.1.0/24`; reject at `before_request` middleware

### 8.3 Compliance Documentation
- [ ] **Data flow diagram** — which data FlowForge touches (query results, report files, email addresses), where stored, where transmitted
- [ ] **SAML support** — `python3-saml` for Okta / Azure AD / Ping enterprise IdP *(v2.x, lower priority)*

---

---

# V3.0 BACKLOG

*No fixed date. Community-driven. Good candidates for "good first issue" labeling.*

## New Connectors & Providers
- [ ] Snowflake / BigQuery / Redshift connectors
- [ ] AWS S3 / Azure Blob upload step
- [ ] MSSQL / SQL Server connection support
- [ ] Generic ODBC connection support
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
- [ ] Password reset flow via email (deferred from v2)
- [ ] Distributed Redis-backed concurrency lock (replaces per-process semaphore for horizontal scale)

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
