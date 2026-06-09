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
**Current score: 6.0 / 10** (2026-05-30) — target ≥ 8.0
Report: https://securityscorecards.dev/viewer/?uri=github.com/jagdeepvirdi/flowforge

#### Passing checks (no action needed)
- Binary-Artifacts: 10/10 — no binaries in repo ✅
- CI-Tests: 10/10 — 8/8 merged PRs checked by CI ✅
- Dangerous-Workflow: 10/10 — no unsafe GitHub Actions patterns ✅
- Dependency-Update-Tool: 10/10 — Dependabot configured ✅
- License: 10/10 — MIT license declared ✅
- Security-Policy: 10/10 — SECURITY.md with disclosure procedures ✅
- Token-Permissions: 10/10 — workflows use least-privilege ✅

#### Critical — fix immediately (score 0)

##### Vulnerabilities (0/10 — Critical)
- [x] Run `pip-audit` and `npm audit` locally, identify all 17 reported CVEs
- [x] Upgrade or patch every vulnerable dependency until `pip-audit` exits clean — `requirements.txt` updated to latest CVE-free versions; `npm audit` reports 0 vulnerabilities after upgrading vite→8.0.16, vitest→4.1.8, @vitejs/plugin-react→6.0.2, react-router-dom patched
- [ ] Re-run scorecard after fixes; confirm Vulnerabilities moves to 10

##### Code-Review (0/10 — Critical)
- [x] Enable **branch protection** on `master`: require at least 1 approving review before merge *(2026-06-09)*
- [x] In GitHub → Settings → Branches → Add rule: check "Require a pull request before merging" + "Require approvals (1)" *(2026-06-09)*
- [ ] Self-review all 9 existing un-reviewed merged PRs via a single "catch-up" review PR description (documents intent retroactively)
- [ ] Going forward: never push directly to `master`; always open a PR and self-approve before merging

##### Maintained (0/10 — Critical — time-based)
- [ ] No direct fix: score improves automatically after the repo has ≥ 90 days of commit activity
- [ ] Ensure at least 1 commit per week during the 90-day window to build history

#### Medium — improve score

##### Pinned-Dependencies (6/10 — Medium)
- [x] Pin `gunicorn==26.0.0` and `gevent==26.5.0` in `requirements.txt`; pin `flower==2.0.1` in Dockerfile; pin `pip-audit==2.10.0` and `bandit[toml]==1.9.4` in `test.yml`
- [x] Generated full hash-pinned `requirements.txt` via `pip-compile --generate-hashes requirements.in` (974 lines, 827 SHA-256 hashes covering all transitive deps). Dockerfile now uses `--require-hashes` to enforce hash verification at build time.
- [ ] Re-run scorecard to confirm Pinned-Dependencies score improves; confirm 5/5 pip invocations are covered

##### SAST (8/10 — Medium)
- [x] Investigated: `codeql.yml` already has `push: branches: ['**']` — ALL commits on ALL branches are scanned, not just PRs. Coverage gap was likely a transient Scorecard fetch issue.
- [x] `on: push: branches: [master]` trigger confirmed present (covered by `['**']`)
- [ ] Re-run scorecard to confirm SAST moves to 10/10

##### CII-Best-Practices (5/10 — Medium)
Silver gaps addressed in code:
- [x] `code_of_conduct` — `CODE_OF_CONDUCT.md` added (Contributor Covenant 2.1)
- [x] `governance` / `roles_responsibilities` / `access_continuity` — `GOVERNANCE.md` added
- [x] `documentation_roadmap` — `ROADMAP.md` added (v1/v2/v3 plan)
- [x] `assurance_case` — `docs/threat-model.md` added (7 threats, mitigations, trust boundaries, security invariants)
- [x] `warnings_strict` — `ruff check .` and `npm run lint` added to CI; 465 issues auto-fixed; remaining 27 manually resolved; ruff now passes clean
- [x] `build_repeatable` — `requirements.txt` fully hash-pinned via `pip-compile --generate-hashes`
- [x] `signed_releases` — `release.yml` with SLSA attestation ✅
- [x] `dependency_monitoring` — `pip-audit` + `npm audit` in CI ✅
- [x] `coding_standards_enforced` — ruff + ESLint in CI ✅
Remaining Silver gaps requiring user action:
- [x] `test_statement_coverage80` — pushed from 72% → 88% (317 new tests across 17 files, merged PR #38 2026-06-05)
- [ ] `bus_factor` (SHOULD) — solo project; document or recruit a co-maintainer
- [ ] `dco` (SHOULD) — consider adding DCO sign-off requirement to PR template
- [ ] Complete the Silver questionnaire at https://bestpractices.dev once all MUST criteria are met
- [ ] Update badge URL in README once Silver is awarded

##### Fuzzing (0/10 — Medium)
- [x] Add `hypothesis>=6.0` to dev extras in `pyproject.toml`; create `tests_fuzz/test_fuzz.py` with 12 property-based tests covering `build()` invariants, `render()` crash safety, blocklist enforcement, `render_sql()` robustness, and pipeline var injection safety
- [x] Fuzz tests run in a separate `tests_fuzz/` directory (no DB required) so they can run anywhere
- [x] Add `pytest tests_fuzz/ -q --hypothesis-seed=0` step to CI `test.yml` after main test suite

#### Low / N/A — resolve when releasing

##### Signed-Releases (-1 — N/A, no releases yet)
- [x] Create `.github/workflows/release.yml` — triggers on `v*` tags; builds wheel + sdist; generates SLSA provenance via `actions/attest-build-provenance@v4.1.0`; creates GitHub Release with auto-notes and signed artifacts
- [x] Document release signing in RUNBOOK.md §12 (one-time setup, cutting a release, verifying attestation)
- [x] Cut v1.1.0 tag — GitHub Release v1.1.0 created with signed artifacts *(2026-06-08)*

##### Packaging (-1 — no publishing workflow)
- [x] Create `.github/workflows/publish.yml` — builds wheel + sdist, publishes to PyPI via OIDC trusted publishing (`pypa/gh-action-pypi-publish@v1.14.0`) with `attestations: true` for SLSA provenance; no API token needed
- [x] Configure PyPI Trusted Publisher — pypi.org → Publishing → `publish.yml` / environment `pypi` for project `flowforge-io` *(2026-06-09)*
- [x] Published `flowforge-io` v1.1.0 to PyPI via `workflow_dispatch` — package renamed from `flowforge` (name blocked by existing `flow-forge` on PyPI) *(2026-06-09)*

##### Branch-Protection (-1 — auth error during scan)
- [ ] Confirm the Scorecard GitHub App has sufficient read permissions on the repo (Settings → Integrations → Installed GitHub Apps)
- [ ] Re-run scorecard after branch protection rules are set — error should resolve *(branch protection enabled 2026-06-09)*

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
- [x] MSSQL / SQL Server connection support — `connections/mssql.py` via `pyodbc`; `flowforge-io[mssql]` optional extra *(2026-05-30)*
- [x] Generic ODBC connection support — `connections/odbc.py` via `pyodbc`; DSN or connection string config *(2026-05-30)*
- [x] SendGrid API email provider — `email_providers/sendgrid.py`; Web API v3; base64 attachments; `pip install flowforge-io[all]` *(2026-05-30)*
- [x] AWS SES email provider — `email_providers/ses.py`; boto3 SES client; raw MIME for attachments; `pip install flowforge-io[ses]` *(2026-05-30)*
- [x] Mailgun email provider — `email_providers/mailgun.py`; Messages API v3; US/EU region; multipart attachments *(2026-05-30)*
- [x] Telegram / Slack / Teams notification step — `steps/notification.py`; step_type `notification`; platform selector in StepEditor; Slack/Teams via incoming webhook; Telegram via Bot API *(2026-05-30)*

## Pipeline Features
- [x] Pipeline dependencies — `ff_pipeline_dependencies` table; cycle detection; `_trigger_downstream_pipelines()` in runner fires eligible downstreams after success; CRUD at `GET/POST/DELETE /api/pipelines/{id}/dependencies`; Dependencies card in PipelineEdit *(2026-05-30)*
- [x] Parallel step execution — `parallel_group VARCHAR(100)` on `ff_pipeline_steps`; runner groups steps into waves; same-group steps run in `ThreadPoolExecutor`; context snapshots per thread, outputs merged after wave; visual group badge + indigo border in StepEditor *(2026-05-30)*
- [x] Pipeline run diff view — `GET /api/runs/{id}/diff` compares step rows/duration/file-size vs prev successful run; collapsible DiffPanel with colour-coded delta badges in RunDetail *(2026-05-30)*
- [x] Report column formatting rules — `column_formatting JSONB` on `ff_report_configs`; Excel generator applies `number_format`, `width`, conditional `PatternFill`/`Font` per rule; ColumnFormattingCard UI in ReportEdit (presets + colour pickers) *(2026-05-30)*
- [x] Environment promotion workflow — `POST /api/pipelines/{id}/promote` clones to target project (disabled); warns on secret vars + unresolved references; Promote (↗) button on Pipelines page with project picker modal *(2026-05-30)*

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
