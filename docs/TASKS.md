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

### 2.1 SonarCloud ✅ COMPLETE — Quality Gate Passed
- [x] SonarCloud account created, repo linked, `SONAR_TOKEN` added to GitHub secrets
- [x] `sonar-project.properties` added; SonarCloud scan step wired into `test.yml` (runs after pytest coverage)
- [x] First scan passed — CI green
- [x] **Quality Gate** badge added to README
- [x] **Quality Gate: Passed** — Security A, all bugs and hotspots resolved *(2026-05-27)*
- [ ] Take a screenshot of the SonarCloud dashboard for LinkedIn post

#### 2.1a Bugs — fix first (gate the Quality Gate)
- [x] Fix Python: `StepRun` referenced but not imported in `runs.py` (NameError at runtime on `/runs/<id>/anomalies` and `/step-runs/<id>/download`) — added to `from flowforge.db.models import` *(2026-05-27)*
- [x] Fix Python: Unused import `from pymysql import connections` in `connections/mysql.py` — removed *(2026-05-27)*
- [x] Fix Python: Unused exception variable `as e` in 13 `except` clauses across `runner.py`, `postgres.py`, `oracle.py`, `mysql.py`, `scheduler.py`, `launcher.py`, `shutdown.py` (S1481) — removed `as e` binding where `e` was never referenced *(2026-05-27)*
- [x] Fix React hooks called conditionally — `Users.tsx` (S6440) — all 4 hooks already above the early `return`; comment confirms intent *(verified 2026-05-27)*
- [x] Fix conditional always produces same value — `Dashboard.tsx` (S3923) — removed redundant `if (!r) return 'idle'` guard in bars map; use `r?.status` optional chaining so fallthrough handles the undefined case *(2026-05-27)*; `Connections.tsx:466` — no S3923 pattern found after full file review; may be resolved by prior refactor or false positive *(verified 2026-05-27)*
- [x] Fix click handlers with no keyboard listener — all 5 locations already fixed: `Layout.tsx`, `HelpDrawer.tsx`, `PageIntro.tsx`, `EmailEdit.tsx`, `Projects.tsx` — all have `role="button"`, `tabIndex={0}`, `onKeyDown` (S1082) *(verified 2026-05-27)*

#### 2.1b Security ✅ COMPLETE — Security rating: A
- [x] Fix NOSONAR comment syntax — `app.py:37` already reads `# NOSONAR` (no trailing text); issue resolved *(verified 2026-05-27)*
- [x] Accept `SECRET_KEY` false positive in SonarCloud UI — `app.py:37`: marked "False Positive" with justification *(2026-05-27)*
- [x] CSRF hotspot — marked Safe: API uses JWT Bearer token auth, no cookies, CSRF not applicable *(2026-05-27)*
- [x] Hardcoded DB password — added `# NOSONAR` to dev-only fallback URL + marked False Positive in UI *(2026-05-27)*
- [x] **Security rating: E → A** *(2026-05-27)*

#### 2.1c Critical Code Smells — Cognitive Complexity (Python)
- [x] Reduce cognitive complexity in `steps/bulk_load.py:26` (34 → ≤15) — extracted `_validate_bulk_cfg`, `_extract_data_rows`, `_derive_csv_columns`, `_derive_line_columns` helpers; all three loader functions now share these *(2026-05-27)*
- [x] Reduce cognitive complexity in `steps/bulk_load.py:369` (30 → ≤15) — same helper extraction above collapsed repeated header/footer slicing patterns *(2026-05-27)*
- [ ] Verify `engine/runner.py:53` — code already heavily refactored (helpers extracted); SonarCloud rescan will confirm if complexity ≤15 or further reduction needed
- [ ] Verify `steps/data_load.py:19` — code already heavily refactored (`_load_source`, `_table_exists`, `_create_table`, `_bulk_load` helpers); SonarCloud rescan will confirm
- [ ] Verify `steps/ai_analyze.py:166` — code already uses `_run_query_or_fail` / `_call_provider_or_fail`; SonarCloud rescan will confirm
- [ ] Verify `steps/db_query.py:47` — code already uses `_write_to_output_table` / `_build_query_result` helpers; SonarCloud rescan will confirm
- [ ] Verify `api/routes/pipelines.py:177,328` — code already uses many extracted helpers; SonarCloud rescan will confirm

#### 2.1d Critical Code Smells — Cognitive Complexity (Frontend)
- [ ] Reduce cognitive complexity in `frontend/src/pages/RunDetail.tsx:71` (32 → ≤15) — extract render helpers / sub-components
- [ ] Reduce cognitive complexity in `frontend/src/pages/Connections.tsx:74` (26 → ≤15) — extract render helpers
- [ ] Reduce cognitive complexity in `frontend/src/pages/Settings.tsx:108` (17 → ≤15) — extract section components
- [ ] Fix deeply nested functions in `PipelineEdit.tsx:299,306,312,318` (S2004, >4 levels) — extract inner callbacks to named module-level functions

#### 2.1e Critical Code Smells — Duplicated String Literals ✅ COMPLETE
- [x] Define `_NOT_FOUND` constants in `api/routes/pipelines.py`, `routes/emails.py`, `routes/users.py`, `routes/runs.py`, `routes/projects.py`, `routes/bulk_loads.py`, `api/app.py` — all already defined
- [x] Define `_CASCADE` / `_SET_NULL` / `_FF_PROJECTS_ID` / `_FF_PIPELINES_ID` constants in `db/models.py` — all already defined at lines 14–17

#### 2.1f Major Code Smells
- [ ] Replace `logger.error("...: %s", e)` with `logger.exception("...")` in all `except` blocks — `runner.py:219,248,268`, `scheduler.py:96,153,164`, `launcher.py:67,96`, `shutdown.py:153,155`, `bulk_load.py:143`, `data_load.py:138,159`, `ai_analyze.py:116,147`, `sftp_transfer.py:195,285`, `onedrive_upload.py:34`, `mysql.py:88`, `gmail.py:95`, `microsoft365.py:102`, `smtp.py:92` (~20 one-line changes)
- [ ] Fix Flask catch-all routes to declare HTTP method — `app.py:149,150`: change `@app.route('/')` / `@app.route('/<path:path>')` → `@app.get()`
- [ ] Fix array index used as React key — use stable `item.id` instead of `idx` — `Layout.tsx:186`, `HelpDrawer.tsx:51,91,126`, `ChartPreview.tsx:101`, `Dashboard.tsx:94,218,253`, `PipelineEdit.tsx:294,616,640`, `BulkLoads.tsx:44`, `EmailEdit.tsx:176`, `ReportEdit.tsx:216`, `RunHistory.tsx:94`
- [ ] Associate form labels with inputs (add `htmlFor`/`id` pairs) — `Settings.tsx:74,79,84`, `Users.tsx:118,128,138`, `Projects.tsx:87,97,106`, `BulkLoadEdit.tsx` (15 instances at lines 150–278), `EmailEdit.tsx:274,282`
- [ ] Fix non-native interactive elements — replace `<div onClick>` with `<button>` or add `role="button"` + `tabIndex={0}` + keyboard handler — `Layout.tsx:68`, `HelpDrawer.tsx:185`, `PageIntro.tsx:35`, `TopBar.tsx:154`, `EmailEdit.tsx:380`, `Projects.tsx:149`
- [ ] Fix nested ternary operations — extract to named `const` before JSX — `Connections.tsx:133,456,466,495,503`, `Dashboard.tsx:67`, `RunDetail.tsx:163,242,404,405`, `ReportEdit.tsx:324`, `PipelineEdit.tsx:468,562`, `Settings.tsx:144`, `Projects.tsx:124`, `Users.tsx:169`
- [ ] Fix CSS contrast ratio below WCAG AA (4.5:1) — `frontend/src/index.css:305,306` — increase foreground/background contrast
- [ ] Replace `<div role="dialog">` with native `<dialog>` element — `HelpDrawer.tsx:197`
- [ ] Add explicit `{' '}` between inline JSX elements — `Layout.tsx:103,148`, `Projects.tsx:232`, `PipelineEdit.tsx:313`, `BulkLoadEdit.tsx:186`

#### 2.1g Minor Code Smells (fix opportunistically)
- [ ] Mark React props as `Readonly<Props>` — 18 components: `App.tsx`, `Skeleton.tsx`, `Recipients.tsx`, `Users.tsx`, `Dashboard.tsx`, `Settings.tsx`, `Connections.tsx`, `HelpDrawer.tsx`, `RunDetail.tsx`, `ChartPreview.tsx`, `PipelineEdit.tsx`, `Pipelines.tsx`, `PageIntro.tsx`, `Projects.tsx`, `ProjectSwitcher.tsx`, `StepEditor.tsx`, `FieldTooltip.tsx`, `TopBar.tsx`
- [ ] Replace `window.*` with `globalThis.*` — `api.ts:26,205`, `TopBar.tsx:44,45`, `HelpDrawer.tsx:178,179`, `PipelineEdit.tsx:394`, `BulkLoads.tsx:142`, `Projects.tsx:194`, `RouteErrorBoundary.tsx:50`, `Users.tsx:86`
- [ ] Remove unnecessary type assertions (`as SomeType`) — `PipelineEdit.tsx:128`, `Pipelines.tsx:92`, `ReportEdit.tsx:196`, `RunDetail.tsx:331`, `ProjectSwitcher.tsx:39`, `BulkLoadEdit.tsx:22,99`, `StepEditor.tsx:223,267`, `FieldTooltip.tsx:18`
- [ ] Replace `parseInt(x, 10)` → `Number.parseInt(x, 10)` — `StepEditor.tsx:186,627`, `BulkLoadEdit.tsx:248,252`, `Pipelines.tsx:17,18,23,36,40`, `PipelineEdit.tsx:537–541`
- [ ] Fix unexpected negated conditions — `Layout.tsx:182`, `RunDetail.tsx:225`, `BulkLoads.tsx:78`
- [ ] Use `[[` instead of `[` in shell — `tests/run_tests.sh:27,29,35`
- [ ] Add default `*)` case to switch in `tests/run_tests.sh:17`
- [ ] Replace `FileReader.readAsText(blob)` with `await blob.text()` — `Pipelines.tsx:93`
- [ ] Replace `dict()` / `list()` constructor calls with literals `{}` / `[]` — `sftp_transfer.py:56`

### 2.2 OpenSSF Scorecard (Security Credibility)
- [x] `.github/workflows/scorecard.yml` added — runs on push + weekly Saturday cron; publishes results to GitHub Security tab
- [x] **Scorecard** badge added to README
- [x] CodeQL workflow (`codeql.yml`) added — satisfies SAST check *(on `fix/ci-dependabot-node24` branch)*
- [x] `pip-audit` step added to `test.yml` — satisfies Vulnerabilities check *(on `fix/ci-dependabot-node24` branch)*
- [x] Docker base images pinned to SHA digest — `Dockerfile:2,10` *(already done)*
- [x] All GitHub Actions in all workflows pinned to SHA — stale alerts will clear on next weekly run
- [x] **Merge `fix/ci-dependabot-node24` branch** — PR #27 merged 2026-05-27; CodeQL + pip-audit + Node 24 upgrades now on master
- [x] **Branch protection enabled on `master`** — requires PR + 1 approval + status checks (`test`, `sast`, `frontend`) + up-to-date branch + enforce_admins; clears `BranchProtection` and `CodeReview` Scorecard checks
- [x] Accept `PinnedDependencies (pip hashes)` penalty — `pip install --require-hashes` incompatible with editable installs
- [x] Accept `Fuzzing` penalty — OSS-Fuzz not practical for v1; revisit in v2
- [ ] Review final Scorecard score after next weekly run (Saturday); target ≥ 7.0

### 2.3 OpenSSF Best Practices Badge ✅ COMPLETE
- [x] Complete the self-certification questionnaire at bestpractices.dev
- [x] Achieved **Passing** tier — project #13002 *(2026-05-27)*
- [x] **OpenSSF Best Practices** badge added to README *(PR #29)*

### 2.4 Codecov ✅ COMPLETE
- [x] `pytest --cov=flowforge --cov-report=xml` + `codecov/codecov-action@v4` added to `test.yml`
- [x] **Coverage** badge added to README
- [x] Added `--cov-branch` for branch coverage measurement *(PR #30)*
- [x] Added `codecov.yml` with 70% project target, 60% patch target *(PR #30)*
- [x] Local coverage: **78% branch / 80% line** across 842 passing tests *(2026-05-27)*
- [x] Add `CODECOV_TOKEN` secret to GitHub repo settings (Settings → Secrets → Actions)

### 2.5 README Badge Row ✅ COMPLETE
- [x] Tests + Codecov + Scorecard badges in README
- [x] SonarCloud Quality Gate badge — already in README (`sonarcloud.io` badge, line 7)
- [x] OpenSSF Best Practices badge added to README *(PR #29, 2026-05-27)*

---

## Phase 3 — Documentation Polish (P1 — Contributor Readiness)

### 3.1 CONTRIBUTING.md — Fast Setup (<5 minutes) ✅
- [x] "Quick Dev Setup" section added at the top (5-command block, login hint)
- [x] "Running Tests" one-liners for pytest and vitest

### 3.2 docs/security.md ✅
- [x] Created — covers: AES-256-GCM encryption, key rotation, JWT + revocation, RBAC roles, audit log, template sandbox, input validation, transport security

### 3.3 SECURITY.md ✅
- [x] Created at repo root — supported versions table, GitHub private advisory + email disclosure, response SLA

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
