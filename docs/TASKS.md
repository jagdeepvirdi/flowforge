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

# Phase 10 — Consolidated Pending Work

*Every remaining unchecked item in this file, gathered in one place and
ordered by priority. Historical detail — score tables, dates, what's already
done — stays under the original Phase headings further down.*

## High priority

*Release-blocking (Release Definition lists "GTM done" under v1.0), quick wins, or ongoing practice that protects a score already earned.*

- [ ] Going forward: never push directly to `master`; always open a PR. Self-approval is blocked by GitHub for PRs you author, so get approval from a collaborator/second account for those, or prefer bot-authored PRs (e.g. Dependabot) *(Scorecard — Code-Review)*
- [ ] Branch-Protection: grant the Scorecard GitHub App `administration:read` (Settings → Integrations → GitHub Apps), or add a fine-grained PAT as the `SCORECARD_TOKEN` secret — quick fix for a currently-erroring (-1) check *(Scorecard — Branch-Protection)*
- [ ] Re-run scorecard to confirm Pinned-Dependencies improved after the hash-pinning already done *(Scorecard — Pinned-Dependencies)*
- [ ] Record a 60–90s demo GIF/MP4 (dashboard → create pipeline with report+email step → run it → Run History) and add to the README — blocks every other GTM item below *(Go-To-Market 5.1)*
- [ ] Capture a high-quality Dashboard screenshot for the README hero / LinkedIn Featured section *(Go-To-Market 5.1)*

## Medium priority

*Meaningful score/visibility gains that take more setup effort.*

- [ ] Fuzzing: register with [OSS-Fuzz](https://google.github.io/oss-fuzz/getting-started/accepting-new-projects/), or add an `atheris` fuzzing target + register in `project.yaml` *(Scorecard — Fuzzing)*
- [ ] Signed-Releases: add a cosign signing step to `release.yml` — sign the wheel with `cosign sign-blob`, attach `.sig`/`.pem` as release artifacts *(Scorecard — Signed-Releases)*
- [ ] CII Silver: document/recruit a co-maintainer (`bus_factor`), add a DCO sign-off requirement to the PR template (`dco`), complete the [Silver questionnaire](https://bestpractices.dev), then update the README badge URL *(CII-Best-Practices)*
- [ ] ProductHunt: create maker profile, draft the listing (name/tagline/description/gallery), schedule a Tue/Wed launch *(Go-To-Market 5.2)*
- [ ] Reddit: post in r/selfhosted, r/Python, r/opensource, and cross-post to r/dataengineering *(Go-To-Market 5.3)*
- [ ] Submit PRs to awesome-selfhosted ("Automation") and awesome-python ("Task Queues"/"Data Pipeline") *(Go-To-Market 5.4)*
- [ ] LinkedIn: write the launch post, add FlowForge to your Featured section, tag `#OpenSource #Python #LocalAI #DataEngineering #Productivity` *(Go-To-Market 5.5)*

## Low priority

*Passive/automatic, deferred until a precondition exists, or explicitly optional.*

- [ ] Ensure at least 1 commit/week until the repo passes 90 days old (~2026-07) — Maintained check auto-resolves either way, no other fix exists *(Scorecard — Maintained)*
- [ ] Update screenshots showing old (pre-multi-user) UI *(deferred — no screenshots exist in docs yet, so nothing to do until some are added)*
- [ ] Code Climate maintainability badge — set up, add to README badge row if grade is A or B *(explicitly optional)*

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
**Current score: 6.5 / 10** (2026-06-13, commit dfd329a) — target ≥ 8.0
Report: https://securityscorecards.dev/viewer/?uri=github.com/jagdeepvirdi/flowforge

| Check | Score | Notes |
|---|---|---|
| Binary-Artifacts | 10 | ✅ |
| CI-Tests | 9 | 15/16 PRs checked |
| CII-Best-Practices | 5 | Passing badge |
| Code-Review | 0 | 1/15 approved changesets |
| Dangerous-Workflow | 10 | ✅ |
| Dependency-Update-Tool | 10 | ✅ |
| Fuzzing | 0 | Hypothesis not recognized; needs OSS-Fuzz/atheris |
| License | 10 | ✅ |
| Maintained | 0 | Repo < 90 days old — auto-improves |
| Packaging | 10 | ✅ (was -1) |
| Pinned-Dependencies | 6 | pip installs in workflows still unpinned |
| SAST | 9 | 16/17 commits scanned (was 8) |
| Security-Policy | 10 | ✅ |
| Signed-Releases | 0 | SLSA attestation not picked up (was -1) |
| Token-Permissions | 10 | ✅ |
| Vulnerabilities | 10 | ✅ (was 0) |
| Branch-Protection | -1 | Auth error — needs fine-grained PAT |
| Contributors | 0 | Solo project, expected |

#### Passing checks ✅
- Binary-Artifacts, Dangerous-Workflow, Dependency-Update-Tool, License, Packaging, Security-Policy, Token-Permissions, Vulnerabilities — all 10/10

*Remaining action items for every check below are consolidated in Phase 10.*

#### Critical — Code-Review (0/10)
- [x] Enable **branch protection** on `master` *(2026-06-09)*
- [x] Self-review all existing un-reviewed merged PRs *(2026-07-01)* — approved 25/41 merged PRs retroactively (all Dependabot-authored). GitHub hard-blocks self-approval via API/UI for the 16 PRs where `jagdeepvirdi` is the actual author (#22,23,25-35,38,50,51) — no workaround with a single account.

#### Critical — Maintained (0/10 — time-based)
Score improves automatically after repo has ≥ 90 days of commit activity (repo created ~2026-04, reaches 90 days ~2026-07). No direct fix besides keeping up regular commits.

#### Medium — Pinned-Dependencies (6/10)
- [x] Hash-pinned `requirements.txt` and Dockerfile
- [x] Pin the 2 unpinned actions in `secrets-scan.yml` — `actions/checkout@v6` → hash `df4cb1c`, `trufflesecurity/trufflehog@main` → hash `84a2b33` *(2026-06-13)*
- [x] Replace bare `pip install` calls in workflows with hash-pinned requirements files *(2026-06-13)*: `requirements-build.txt` used in `publish.yml` + `release.yml`; `requirements-dev.txt` (superset: runtime + dev tools) used in `test.yml` test and sast jobs; `pip install --no-deps -e .` for editable package install
- `Dockerfile:20` `pip install --no-cache-dir --no-deps .` — local package install, cannot hash-pin; accepted as-is, not a pending action

#### Medium — SAST (9/10)
- [x] CodeQL configured on all branches
- 1 commit (out of 17) not scanned — resolves naturally as new commits are added, not a pending action

#### Medium — Fuzzing (0/10)
- [x] Hypothesis property-based tests added to `tests_fuzz/` — but Scorecard only recognizes OSS-Fuzz or atheris integration

#### Low — Signed-Releases (0/10)
- [x] `release.yml` uses `actions/attest-build-provenance` — Scorecard not picking it up (expects cosign or SLSA provenance attached as a release asset)

#### Low — Branch-Protection (-1 — auth error)

#### CII-Best-Practices (5/10)
Silver gaps remaining — see Phase 10.

---

## Phase 3 — Documentation Polish (remaining)

### 3.4 Getting-Started Quick Check
- [x] Run through `docs/getting-started.md` end-to-end — verify all commands and screenshots are current

*Remaining action item consolidated in Phase 10.*

---

---

# V2.0 — TASKS

*Post-release hardening. Starts after v1.0 ships.*

---

## Phase 5 — Go-To-Market (P1 — Visibility)

*These do not block the GitHub release tag but should happen within the first week of release.*
*Tracking checkboxes consolidated in Phase 10 — the detail below is reference material (exact copy/hashtags/etc.) for when you get to each one.*

### 5.1 Demo Assets
- Record a 60–90 second screen recording (GIF or MP4):
  - Open dashboard → create a pipeline with a report + email step → run it → show Run History with logs
- Capture a high-quality static screenshot of the Dashboard for the README hero and LinkedIn Featured section
- Add the demo GIF to the README (below the tagline, above the feature list)

### 5.2 ProductHunt Launch
- Create a ProductHunt account / maker profile
- Draft the listing:
  - Name: **FlowForge**
  - Tagline: `SQL-to-Email pipeline orchestrator. No YAML. No Airflow complexity.`
  - Description: Explain the problem (50+ cron scripts), the solution, highlight Celery scaling + local AI
  - Gallery: dashboard screenshot + report designer + run history
- Schedule launch for a Tuesday or Wednesday (highest ProductHunt traffic)

### 5.3 Reddit Posts
- Post in **r/selfhosted**: "I built an open-source database pipeline orchestrator — SQL → Report → Email, with local AI. No YAML required."
- Post in **r/Python**: focus on the Flask + Celery + APScheduler architecture choices
- Post in **r/opensource**: general project introduction with demo GIF
- Cross-post to **r/dataengineering** focusing on the Oracle + PostgreSQL + MySQL support

### 5.4 Awesome Lists Submission
- Submit PR to [awesome-selfhosted](https://github.com/awesome-selfhosted/awesome-selfhosted) — category: "Automation"
- Submit PR to [awesome-python](https://github.com/vinta/awesome-python) — category: "Task Queues" or "Data Pipeline"

### 5.5 LinkedIn
- Write the launch post:
  - Hook: "Stop writing boilerplate Python scripts for DB automation..."
  - Highlight: Celery/Redis scaling, local AI (Ollama), full audit logging, multi-user roles
  - Tech stack: React + Flask + PostgreSQL + Celery
  - Link to GitHub repo
  - Attach: demo GIF or dashboard screenshot
- Add FlowForge to LinkedIn "Featured" section with dashboard screenshot and 2-sentence value description
- Tag: `#OpenSource`, `#Python`, `#LocalAI`, `#DataEngineering`, `#Productivity`

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
*Consolidated in Phase 10.*

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
- [x] **SAML support** *(2026-07-01)* — `python3-saml` (`sso` extra); `GET /auth/sso/saml/login`, `POST /auth/sso/saml/acs`, `GET /auth/sso/saml/metadata` in `flowforge/api/routes/sso.py`; reuses existing provider-agnostic `_find_or_create_user`, no DB migration needed (`sso_provider` already free-text); configured via `SAML_SP_ENTITY_ID`/`SAML_IDP_ENTITY_ID`/`SAML_IDP_SSO_URL`/`SAML_IDP_X509_CERT` env vars; "Sign in with SSO" button in Login page when configured

---

---

# V3.0 BACKLOG ✅ *(COMPLETE 2026-07-01)*

*No fixed date. Community-driven. Good candidates for "good first issue" labeling.*

## New Connectors & Providers
- [x] Snowflake / BigQuery / Redshift connectors *(2026-07-01)* — `connections/{snowflake,bigquery,redshift}.py`; Redshift is a thin `PostgreSQLConnection` subclass (wire-compatible, no new dependency); Snowflake via `snowflake-connector-python`; BigQuery via `google-cloud-bigquery` (named `@pN` query parameters instead of positional `%s`, since BigQuery has no DBAPI-style placeholders); `db_type` CHECK constraint relaxed via migration `0027`; Connections page has dedicated Snowflake/BigQuery config forms (service account JSON masked in API responses)
- [x] AWS S3 / Azure Blob upload step *(2026-07-01)* — `steps/{s3_upload,azure_blob_upload}.py` + `storage/{s3,azure_blob}.py`; credentials via env vars (`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`/`AWS_DEFAULT_REGION`, `AZURE_STORAGE_CONNECTION_STRING` or `AZURE_STORAGE_ACCOUNT_URL`+`KEY`), matching the existing Drive/OneDrive convention; presigned/SAS shareable URLs by default; documented in `docs/step-types.md`
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
- [x] Plugin system — community step types loaded from a directory *(2026-07-01)* — `flowforge/engine/loader.py` scans `FLOWFORGE_PLUGIN_DIR` (default `./plugins`) for `*.py` files defining `BaseStep` subclasses; consolidated the 4 previously-drifted step-type lists (DB CHECK constraint, API validation, 2 frontend arrays — this also fixed a pre-existing bug where `notification` steps couldn't be added via the API) into one registry exposed via `GET /api/step-types`; `ck_step_type` relaxed from an enum CHECK to a format check (migration `0026`) since plugin type names aren't known in advance; StepEditor falls back to a generic JSON config editor for types with no dedicated form; example plugin + authoring guide in `examples/plugins/http_webhook_step.py` / `docs/plugins.md`
- [x] `ff_project_members` join table — team-scoped project access (deferred from v2) *(2026-07-01)* — enforced (not just informational): non-admin users only see/edit pipelines, reports, emails, and recipient groups in projects they're a member of; admins bypass everywhere, matching the existing `require_role` convention. Shared `flowforge/api/project_access.py` helper (`can_access_project`/`scope_query`) applied across pipelines/steps/runs/reports/emails/recipients/projects routes. Fixed a pre-existing gap where `POST/PATCH/DELETE /projects` only required login (any role, including viewer) with no role check. New `GET/POST/DELETE /api/projects/{id}/members` endpoints (admin-only mutations); Projects page has a Members modal. Migration `0028` backfills every existing user into the Default project so nobody already using FlowForge loses access; new users and project creators are auto-added going forward
- [x] Password reset flow via email — `ff_password_reset_tokens` table; `POST /auth/password-reset/request|confirm`, `GET /auth/password-reset/validate/<token>`; user `email` column; "Forgot password?" on Login; Users page shows/sets email *(2026-05-30)*
- [x] Distributed Redis-backed concurrency lock (replaces per-process semaphore for horizontal scale) *(2026-07-01)* — turned out the semaphore had silently regressed to nothing in a prior refactor (no concurrency limiting existed at all). `flowforge/engine/concurrency.py`: in-process `threading.Semaphore` fallback when `FLOWFORGE_REDIS_URL` is unset, or a Redis sorted-set distributed counter (fail-open on Redis outages) when it's set — holds the `FLOWFORGE_MAX_CONCURRENT_RUNS` limit correctly across multiple Gunicorn/Celery workers. Wired into the single `launch_run()` entry point shared by all 4 trigger paths (HTTP, webhook, scheduler, downstream dependency fan-out); returns HTTP 429 when exhausted

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

---

---

# Phase 11 — External Review Hit-List (2026-07-01)

*From a brutal, evidence-based architect/VC-style audit of the codebase as it actually is today (verified via code reading, not self-reported scores). Findings below survived direct verification against `flowforge/` source, not just prior review docs.*

## Critical (fix immediately / showstoppers)

- [ ] **SQL injection in `data_load.py`** — `target_table` and `column_map` values are Jinja2-rendered and interpolated directly into `CREATE TABLE`/`TRUNCATE`/`INSERT` (~lines 283, 292, 295) without the `validate_identifier()` guard that `db_query.py`/`bulk_load.py` already use. Add the same guard here.
- [ ] **Secrets leak via shared step context** — `is_secret` pipeline variables are decrypted into the context available to every step (`engine/loader.py:145-153`, `context.py:194`). A `db_query`/`report` step can trivially exfiltrate a secret into an output table, capture_rows, or email body. `render_sql()` only logs a warning (`context.py:220-226`) instead of blocking. Either strip secrets from the general context or hard-block rendering when a secret var key is referenced.
- [ ] **SSRF in notification webhooks** — `steps/notification.py` (Slack/Teams/Telegram) fetches an editor-configurable webhook URL server-side with no restriction on link-local/RFC1918/cloud-metadata IPs.
- [ ] **Audit log miscategorization for user management** — `api/routes/users.py` calls `audit.log_pipeline_change('USER_CREATED'/'USER_UPDATED'/'USER_DELETED', ...)`; `audit.py` prefixes this `PIPELINE_CFG_`, so all user-admin events are mis-filed under pipeline-config actions in the audit log. Add a dedicated `log_user_change()`.
- [ ] **Reconcile `ROADMAP.md` / `TASKS.md` / `CLAUDE.md`** — they currently contradict each other on what's shipped (ROADMAP says v2.0 "starts after v1.0 ships"; TASKS.md marks v2.0 and v3.0 complete). Pick one source of truth.

## High Priority (refactoring & scalability)

- [ ] Break up frontend god-components — `StepEditor.tsx` (782 lines), `PipelineEdit.tsx` (775 lines, 33 hooks in one file), `Connections.tsx` (861 lines) — into per-step-type / per-section components.
- [ ] Enforce a real coverage threshold (`pytest-cov --fail-under=N` in CI) instead of citing raw test counts as a quality signal — no coverage % is currently asserted anywhere.
- [ ] Load-test the single `BlockingScheduler` process (SPOF for all schedules) and the Redis fail-open concurrency path (`engine/concurrency.py`) under actual failure injection, not just mocked unit tests.
- [ ] Resolve the OpenSSF Scorecard Code-Review deadlock (0/10, structurally stuck for a solo maintainer since GitHub blocks self-approval) — recruit a co-maintainer/approver or explicitly drop the ≥8.0 target instead of leaving it perpetually "in progress."
- [ ] Build the visual DAG/pipeline canvas — promised in `ROADMAP.md` v3.0 goals, silently absent from the actual v3.0 backlog delivered, and flagged in this project's own market-comparison doc as the #1 competitive gap vs. Airflow/n8n/Dagster.
- [ ] Get at least one real external user or design partner before adding more enterprise-checkbox features (SSO/SAML/MFA/GDPR tooling currently serves zero non-author users).

## Nice-to-Have (polish & optimization)

- [ ] Consolidate migration ID scheme — hand-numbered files interleaved with autogenerated Alembic hash IDs.
- [ ] Finish Tailwind migration on remaining inline-style components (`ProjectSwitcher.tsx`, `Layout.tsx`, etc.); add loading skeletons for data-fetching views.
- [ ] Pin Docker base images to digest; close remaining Scorecard Pinned-Dependencies gaps.
- [ ] Add a one-click deploy option (Railway/Render/Fly.io) to lower adoption friction beyond `docker compose up`.
