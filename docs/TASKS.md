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

- [ ] Going forward: never push directly to `master`; always open a PR. Self-approval is blocked by GitHub for PRs you author, so get approval from a collaborator/second account for those, or prefer bot-authored PRs (e.g. Dependabot) *(Scorecard — Code-Review)* — **partially addressed 2026-07-06**: `enforce_admins` disabled on `master`'s branch protection so admin-override merges (`gh pr merge --admin`) are possible without a collaborator (PRs #94, #95 merged this way). This unblocks the solo-maintainer workflow but does **not** raise the Scorecard Code-Review score — admin-override merges still count as unreviewed, so the score stays near 0 until a real second reviewer is in the loop. See Phase 11's Code-Review deadlock item below.
- [x] Branch-Protection: grant the Scorecard GitHub App `administration:read` (Settings → Integrations → GitHub Apps), or add a fine-grained PAT as the `SCORECARD_TOKEN` secret — quick fix for a currently-erroring (-1) check *(Scorecard — Branch-Protection)* — **done 2026-07-06**: `SCORECARD_TOKEN` (fine-grained PAT, `administration:read`) wired into `.github/workflows/scorecard.yml` (PR #94). Awaiting next Scorecard run to confirm the check no longer shows -1.
- [ ] Re-run scorecard to confirm Pinned-Dependencies improved after the hash-pinning already done *(Scorecard — Pinned-Dependencies)*
- [ ] Record a 60–90s demo GIF/MP4 (dashboard → create pipeline with report+email step → run it → Run History) and add to the README — blocks every other GTM item below *(Go-To-Market 5.1)*
- [ ] Capture a high-quality Dashboard screenshot for the README hero / LinkedIn Featured section *(Go-To-Market 5.1)*

## Security — SonarCloud residual finding needs manual resolution *(found 2026-07-06)*

- [x] **Env-var exfiltration via bulk-load preview endpoint** — the new `/bulk-load-configs/validate-raw` endpoint (merged in #94) let any authenticated user, regardless of role, exfiltrate any env var not in the (then 7-entry) `_SafeEnv` blocklist by crafting a `source_directory`/`target_table` like `{{ env.FLOWFORGE_DB_URL }}`; the rendered value was echoed verbatim into the returned error/warning message. Fixed in #95: expanded `_ENV_BLOCKLIST` (added `FLOWFORGE_DB_URL`/`REDIS_URL`, AWS/Azure/SSO/SAML secrets, `DB_PASSWORD`) plus a name-pattern check (`_looks_like_credential_name`) so future credential-shaped env vars are blocked by default; `preview_bulk_load()` no longer reflects rendered template values in messages, only the original template string. 23 new/updated tests.
- [ ] **Manually resolve the residual SonarCloud finding** (`pythonsecurity:S5496`, issue key `AZ82Oyzt-6VzRaR01a4L`, `flowforge/engine/context.py`) as Won't Fix / False Positive in the SonarCloud UI — the rule flags the `render()` call-site pattern itself (Jinja2 template from user-controlled input) regardless of the mitigations above, and will keep failing `master`'s Quality Gate until either manually resolved or it ages out of the New Code period on its own. Justification: `_jinja` is already a `SandboxedEnvironment` (blocks RCE-class gadgets), the blocklist/pattern now covers known and future credential names, and rendered values are no longer reflected — this is the same `{{ current_date }}`-style templating used intentionally everywhere else in the app, not a coding mistake in this one spot. Requires SonarCloud login (not available to Claude).
- [ ] **Second residual SonarCloud finding, same category** (`pythonsecurity:S3649` — SQL injection, issue key `AZ83ITEjNp5vzm4zlnz0`, `flowforge/steps/bulk_load.py:614` in `_dry_run_insert_rows()`, introduced by the bulk-load dry-run V2 feature on 2026-07-06) — also needs manual Won't Fix / False Positive resolution in the SonarCloud UI; failing `master`'s Quality Gate (New Code Security Rating) the same way S5496 does. The taint tracker flags `target_table`/`columns` flowing into the f-string-built `INSERT` statement, but both are validated with `validate_identifier()` (regex allowlist: letters/digits/underscore/dot only, raises otherwise) by the caller (`preview_bulk_load` validates `target_table`; `_derive_csv_columns` validates each column name) **and** redundantly re-validated inside `_dry_run_insert_rows()` itself (added specifically to try to satisfy this finding) — SonarCloud's Python security rules don't recognize a project-local validation function as a sanitizer boundary regardless of where it's called from, so the finding persists even with the belt-and-suspenders fix in place. Same remediation path as S5496: requires SonarCloud login (not available to Claude) to mark resolved.

## Local environment — email providers broken *(found 2026-07-03, blocks dev testing)*

*Both SMTP and Gmail sending were failing locally. SMTP is now fixed (port/`use_ssl` mismatch + AVG Email Shield). Gmail is still broken — steps below.*

- [ ] **AVG Web Shield is intercepting `oauth2.googleapis.com`** — same class of issue as the SMTP one (AVG Email Shield), but a different shield since this is a plain HTTPS call, not SMTP. Confirmed via `SSLCertVerificationError: unable to get local issuer certificate` when attempting a token refresh. Fix: AVG → Settings → Protection → Web & Email → disable **Web Shield**, or add a domain exception for `googleapis.com`.
- [ ] **Re-authorize Gmail — refresh token expired** — `RefreshError: invalid_grant: Bad Request`. Root cause: the stored refresh token is 40 days old, and the Google OAuth consent screen is in **Testing** publishing status, where Google hard-expires refresh tokens after 7 days regardless of activity. Fix: re-run Step 5 in `docs/gmail-oauth2-setup.md` to mint a new refresh token, then update the "Personal Gmail" provider in **Connections → Email Providers**.
- [ ] **Stop this recurring every ~7 days** — publish the OAuth consent screen to "In production" in Google Cloud Console. Caveat: the app currently requests the full `drive` scope, which Google classifies as *restricted* and normally requires a verification review to publish for real use. Two options: go through verification, or narrow the scope to `drive.file` (not restricted, no review needed) if full-Drive access isn't actually required — would need a small code change plus re-consent.
- [ ] **Doc gap**: `docs/gmail-oauth2-setup.md`'s "Keeping the App in Testing vs Publishing" section (line ~158) says Testing mode is fine "indefinitely" but doesn't mention the 7-day refresh-token expiry — add a warning there so this doesn't surprise the next person.

## Medium priority

*Meaningful score/visibility gains that take more setup effort.*

- [ ] Fuzzing: register with [OSS-Fuzz](https://google.github.io/oss-fuzz/getting-started/accepting-new-projects/), or add an `atheris` fuzzing target + register in `project.yaml` *(Scorecard — Fuzzing)*
- [ ] Signed-Releases: add a cosign signing step to `release.yml` — sign the wheel with `cosign sign-blob`, attach `.sig`/`.pem` as release artifacts *(Scorecard — Signed-Releases)*
- [ ] CII Silver: document/recruit a co-maintainer (`bus_factor`), add a DCO sign-off requirement to the PR template (`dco`), complete the [Silver questionnaire](https://bestpractices.dev), then update the README badge URL *(CII-Best-Practices)*
- [ ] ProductHunt: create maker profile, draft the listing (name/tagline/description/gallery), schedule a Tue/Wed launch *(Go-To-Market 5.2)*
- [ ] Reddit: post in r/selfhosted, r/Python, r/opensource, and cross-post to r/dataengineering *(Go-To-Market 5.3)*
- [ ] Submit PRs to awesome-selfhosted ("Automation") and awesome-python ("Task Queues"/"Data Pipeline") *(Go-To-Market 5.4)*
- [ ] LinkedIn: write the launch post, add FlowForge to your Featured section, tag `#OpenSource #Python #LocalAI #DataEngineering #Productivity` *(Go-To-Market 5.5)*
- [x] Add `run_id` to `EMAIL_SENT`/`REPORT_EXPORTED` audit entries so they can be joined to `step_runs`/`pipeline_runs` directly *(Observability 7.4)* — done 2026-07-06
- [x] Build an aggregated performance-over-time view (duration/rows trends per step type or pipeline) on top of the `step_runs` data already being captured *(Observability 7.5)* — done 2026-07-06

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

### 7.4 Audit Log — link `run_id` for cross-referencing *(scoped 2026-07-05, shipped 2026-07-06)*
*Consolidated in Phase 10.*

`PIPELINE_STARTED`/`PIPELINE_SUCCESS`/`PIPELINE_FAILED` audit entries already carried `run_id` (`runner.py:260,316`), but `log_email_sent()` and `log_report_exported()` (`flowforge/audit.py`) only stored `pipeline_name`/`step_name` — no `run_id`. Added a `run_id: str = ''` parameter (appended, default `''`, so existing positional call sites/tests are unaffected) to both functions — included in the log line (`run_id=<id>` or `run_id=unknown`) and in the `details` JSONB written to `ff_audit_log`. Threaded through from `email_step.py`/`report.py` via `context.get('run_id', '')` (already set by the runner on every pipeline context). No frontend change needed — the Audit Log page's Details column already `JSON.stringify`s the full `details` dict, so `run_id` shows up automatically and can be cross-referenced against Run History without fuzzy-matching on name + timestamp.

### 7.5 Step performance trends over time *(scoped 2026-07-05, shipped 2026-07-06)*
*Consolidated in Phase 10.*

`step_runs` already recorded `duration_ms`, `rows_affected`, and `status` for every step type (bulk load, SFTP, db_procedure, report, email, etc.) — `_write_step_run()` in `runner.py:425` is called generically regardless of step type, so the raw data already existed; this only adds a view over it, no new collection. New `GET /api/step-runs/trends` endpoint (`flowforge/api/routes/runs.py`, same blueprint as the existing anomalies/diff endpoints) accepts `step_type`, `pipeline_id`, `project_id` (access-scoped like `list_runs`), and `days` (default 30, clamped to [1, 180]); buckets matching `step_runs` rows by day and returns per-bucket `run_count`/`success_count`/`failure_count`/`avg_duration_ms`/`p95_duration_ms`/`avg_rows_affected`, plus `available_step_types` for populating a picker. Aggregated in Python (`statistics.mean` + a nearest-rank `_percentile()` helper) rather than DB-side percentile functions, matching this file's existing `_check_anomaly` convention instead of introducing a Postgres-only SQL construct. Frontend: new collapsible `StepTrendsPanel` component (lazy-loaded on expand, mirroring `DiffPanel`'s pattern) rendered on the Run History page, with a step-type dropdown, a 7d/30d/90d window picker, and a Recharts line chart (avg + p95 duration) styled to match `ChartPreview.tsx`'s existing palette/tooltip/axis conventions.

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
- [x] **Bulk load dry-run (V2)** *(scoped 2026-07-04, V1 shipped same day; error-grouping requirement added 2026-07-05; V2 shipped 2026-07-06)* — V1 (`preview_bulk_load()` in `flowforge/steps/bulk_load.py`, "Test File" button in `BulkLoadEdit`/`BulkLoads`) checks file discovery, header parsing, and target-column existence, but CSV values are untyped text — it can't catch type-coercion or constraint errors (NOT NULL, unique/PK, length overflow) that only surface once a real insert runs. V2 adds an opt-in "Attempt insert (rolled back)" checkbox in `BulkLoadEdit` that passes `dry_run=true` through `POST /bulk-load-configs/{id}/validate` and `.../validate-raw` to `preview_bulk_load(cfg, dry_run=True)`: it builds the exact same parameterized `INSERT` statement `_load_python_fallback` uses (reusing the real code path, not a heuristic type-check) and attempts each sampled row individually against the real target table inside a `SAVEPOINT`, rolling the whole transaction back at the end — nothing is ever committed. Per-row execution (rather than reusing the batch COPY/executemany calls verbatim) was a deliberate deviation from the original literal wording, since a batched statement aborts at the first bad row and can't surface a second, unrelated failure — savepoint-per-row was the only way to satisfy the error-grouping requirement below while still hitting the real DB engine's real constraint/type checking. Scoped to PostgreSQL + the Python-fallback path only; skipped for the Oracle `sqlldr` path (manages its own commits) with a warning surfaced both dynamically (`preview_bulk_load` warnings) and statically in the "Use SQL\*Loader" checkbox's UI copy in `BulkLoadEdit.tsx`.
  - **Error reporting groups by error signature, not per-row.** `_classify_insert_error()` maps driver exceptions to `(error_type, column)` — psycopg2's `.diag.sqlstate`/`.diag.column_name` when available, else ORA-code / substring matching. `_group_insert_errors()` groups all rows hitting the same `(column, error_type)` into one entry `{row_indices, column, error_type, message, count}`, sorted by count descending. `_insert_error_summary()` produces the lead line (e.g. "3 error types across 14 of 20 sampled rows"). `BulkLoadEdit.tsx` renders the summary + grouped detail above the sample-rows table, caps the row numbers shown per group to first 3 + "and N more" (`formatRowNumbers()`), and highlights every affected row/cell in the table (not just the capped ones) by cross-referencing `row_indices`/`column` against the rendered grid.

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

- [x] **SQL injection in `data_load.py`** *(2026-07-02)* — added `validate_identifier()` guard for `target_table` (post-render) and every column name (post-`column_map`) before they're interpolated into `CREATE TABLE`/`TRUNCATE`/`INSERT`, matching `db_query.py`/`bulk_load.py`. Query-source rendering also switched from `render()` to `render_sql()`.
- [x] **Secrets leak via shared step context** *(2026-07-02)* — `render_sql()` now hard-blocks (raises `SecretLeakError`) instead of warning when a secret pipeline variable is referenced. Added `render_guarded()` in `engine/context.py` and applied it to every sink where a secret could be persisted/transmitted outside the pipeline: `email_step.py` (subject/body/drive-share message), `notification.py` (message/title), `ai_analyze.py` (query/prompt), and `data_load.py`'s query source. Legitimate secret sinks (`db_procedure` params — true bind variables, SFTP/S3/Azure credentials) are untouched.
- [x] **SSRF in notification webhooks** *(2026-07-02)* — new `flowforge/net_guard.py` (`assert_public_url()`) rejects link-local/RFC1918/loopback/multicast/unspecified resolved IPs; wired into `notification.py`'s Slack and Teams webhook senders before any outbound request. Telegram's API host is fixed (not editor-configurable), so no guard needed there.
- [x] **Audit log miscategorization for user management** *(2026-07-02)* — added `audit.log_user_change()` (writes `USER_CREATED`/`USER_UPDATED`/`USER_DELETED`); `api/routes/users.py` now calls it instead of `log_pipeline_change()`.
- [x] **Reconcile `ROADMAP.md` / `TASKS.md` / `CLAUDE.md`** *(2026-07-02)* — `docs/TASKS.md` designated as the authoritative, evidence-based tracker. `ROADMAP.md` rewritten to match actual shipped state (verified against code) and now explicitly defers to TASKS.md; also calls out the one confirmed real gap (visual DAG canvas never built). `CLAUDE.md`'s stale "Non-Goals (v1)" and "Authentication (v1)" sections (still describing multi-user auth/Slack-Teams/S3-Azure as unbuilt) corrected and pointed at ROADMAP.md/TASKS.md.

## High Priority (refactoring & scalability)

- [x] **Break up frontend god-components** *(2026-07-02)* — `StepEditor.tsx` 782→168 lines: each step-type form moved to `components/pipeline/stepForms/*.tsx` (10 forms + shared `Field`/`types` + a `STEP_FORMS` registry StepEditor dispatches through). `PipelineEdit.tsx` 775→352 lines: `PipelineVariablesCard`, `DependenciesCard`, `WebhookCard`, `CronBuilder` extracted to `components/pipeline/*.tsx`. `Connections.tsx` 861→484 lines: per-DB-type (`DbFieldsGeneric/Odbc/Snowflake/BigQuery`) and per-provider-type (`MailFieldsSmtp/OAuth/Sendgrid/Ses/Mailgun`) field components plus `DbConnectionRow`/`EmailProviderRow` extracted to `components/connections/*.tsx`. All three verified live in-browser (every step type / DB type / provider type rendered and interacted with, zero console errors) in addition to `tsc`/`eslint`/production build passing.
- [x] **Enforce a real coverage threshold** *(2026-07-02)* — this finding was stale: `--cov-fail-under=72` had already existed in `test.yml` since an earlier commit, but a later commit (`8236da5`) pushed actual coverage to 88%+ without raising the floor, leaving a ~19-point regression window. Verified all pending work was purely additive, measured actual coverage locally (90.6%–91%), and raised `--cov-fail-under` 72→88 in `test.yml` plus `codecov.yml`'s `project.default.target` 70%→88% and `patch.default.target` 60%→75% (threshold widened 5%→10% to tolerate normal per-PR variance) so both gates now track reality instead of a stale historical floor.
- [x] **Load-test the scheduler and Redis fail-open concurrency path** *(2026-07-02)* — used a real Docker Redis container (`docker pause`/`unpause`) plus a real hanging TCP server and real Postgres jobstore for genuine failure injection, not mocks:
  - **Found and fixed a real bug**: `_redis_client()` set `socket_connect_timeout` but not `socket_timeout`, so a Redis that accepted the TCP connection but then hung (frozen/overloaded/blackholed mid-command — reproduced via `docker pause`) caused `try_acquire()` to block **indefinitely**, silently defeating the documented fail-open guarantee. Fixed by adding `socket_timeout=3`; verified the same `docker pause` scenario now fails open in ~3s. Permanent regression test added (`tests/test_concurrency_failure_injection.py`) using a real hanging TCP socket server, so this is caught in CI without a Docker dependency.
  - Verified with real concurrent load against a real Redis (50 threads, 50 concurrent `try_acquire()` calls, limit=10): the Lua acquire script grants **exactly** 10 slots with zero duplicates — atomicity holds under genuine concurrency, not just sequential mocks. Added a `redis:7-alpine` service to `test.yml` so this runs in CI too (`FLOWFORGE_TEST_REDIS_URL`), not just locally.
  - Verified the scheduler's "jobs survive scheduler restarts" claim against a real Postgres-backed `SQLAlchemyJobStore`, with a genuinely hard-killed scheduler process (no graceful `shutdown()` — matching what an actual crash looks like, not just a clean restart): jobs and their latest schedule updates both survive. Claim holds. Test added in `tests/test_scheduler_jobstore_persistence.py`.
- [ ] Resolve the OpenSSF Scorecard Code-Review deadlock (0/10, structurally stuck for a solo maintainer since GitHub blocks self-approval) — recruit a co-maintainer/approver or explicitly drop the ≥8.0 target instead of leaving it perpetually "in progress." **Not resolved by disabling `enforce_admins` (2026-07-06)** — that change only unblocks the solo-maintainer merge workflow (see Phase 10 note above); admin-override merges still don't count as reviewed, so the score is unaffected.
- [ ] Build the visual DAG/pipeline canvas — promised in `ROADMAP.md` v3.0 goals, silently absent from the actual v3.0 backlog delivered, and flagged in this project's own market-comparison doc as the #1 competitive gap vs. Airflow/n8n/Dagster.
- [ ] Get at least one real external user or design partner before adding more enterprise-checkbox features (SSO/SAML/MFA/GDPR tooling currently serves zero non-author users).

## Nice-to-Have (polish & optimization)

- [x] Consolidate migration ID scheme *(2026-07-06)* — the 4 autogenerated hash-named files (`6158f44dafca`, `b7a76582c1ea`, `9c08f36f9ef8`, `c4e8f2a1b9d3`) sat between `0019` and `0020` in the actual `revision`/`down_revision` chain but sorted out of order alphabetically. Renamed to `0019a`/`0019b`/`0019c`/`0019d_*.py` (via `git mv`, preserving history) so directory order now matches execution order. Filenames only — the `revision =` ID strings inside are untouched, since those are what's recorded in any already-deployed database's `alembic_version` table; changing them would require a bridging migration and wasn't worth the risk for a cosmetic fix. Verified: `ScriptDirectory.walk_revisions()` still resolves to a single head (`0028_project_members`) with the same full chain, and the full test suite (which runs `alembic upgrade head` per session) passes unchanged (1896 tests).
- [ ] Finish Tailwind migration on remaining inline-style components (`ProjectSwitcher.tsx`, `Layout.tsx`, etc.); add loading skeletons for data-fetching views.
- [x] Pin Docker base images to digest *(2026-07-06)* — the app `Dockerfile` was already digest-pinned on both stages; the gap was service images referenced by mutable tag only: `postgres:16-alpine` and `redis:7-alpine` in `docker-compose.yml`, `gvenzl/oracle-free:23-slim` in `docker-compose.oracle.yml`, `postgres:16-alpine` in `docker-compose.sample-db.yml`, and the `postgres`/`redis` CI service containers in `.github/workflows/test.yml`. All resolved via `docker buildx imagetools inspect` and pinned `tag@sha256:digest` (keeps the tag readable alongside the immutable digest, matching the Dockerfile's existing style). Verified with `docker compose config` against the merged stacks. Added a `docker` ecosystem entry to `.github/dependabot.yml` (directory `/`, monthly) to track the Dockerfile + all 3 `docker-compose*.yml` files going forward — **known gap**: Dependabot's `docker` ecosystem doesn't scan `image:` strings inside GitHub Actions workflow YAML, so the two CI service-container pins in `test.yml` won't auto-update and need re-pinning by hand if they drift.
- [ ] Add a one-click deploy option (Railway/Render/Fly.io) to lower adoption friction beyond `docker compose up`.
