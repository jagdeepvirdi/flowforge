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
- [x] Finish Tailwind migration on remaining inline-style components — 54 of 62 page/component files still use inline `style={{...}}` as the primary styling mechanism (1,125 occurrences); only `Dashboard.tsx` mostly uses real Tailwind utility classes. Scoped into 14 chunks in **Phase 12** *(scoped 2026-07-06, completed 2026-07-08)* — see Phase 12 below for the full per-chunk breakdown, including a cross-cutting `!important`-for-unlayered-CSS bug found and fixed partway through (chunk 12.7) that also required retroactive fixes to chunks 12.2–12.6 and an audit of Dashboard.tsx's pre-existing Tailwind code in 12.13.
- [x] Add loading skeletons for data-fetching views *(2026-07-06)* — 9 pages previously showed a bare `<Spinner/>` on an otherwise blank screen while loading: `AuditLog`, `BulkLoadEdit`, `Emails`, `Pipelines`, `Projects`, `Recipients`, `Reports`, `RunDetail` got full content-shaped skeleton layouts (title/table/card placeholders via the existing `Sk`/`Skeleton` component, matching the pattern already used on `Dashboard`/`BulkLoads`/`RunHistory`/etc.); `Settings` didn't block on a blank page (each card already rendered immediately with the page shell), so its 4 small per-card status-badge spinners were swapped for skeleton pills instead, for visual consistency. Added a `ResizeObserver` stub to `src/__tests__/setup.ts` (unrelated prerequisite hit while re-running the suite). Verified live: started the Flask backend + Vite dev server, logged in via Playwright, and screenshotted all 9 pages with real dev data (including triggering a real pipeline run for `RunDetail` and opening a real bulk-load config for `BulkLoadEdit`) — zero console/runtime errors on any page.
- [x] Pin Docker base images to digest *(2026-07-06)* — the app `Dockerfile` was already digest-pinned on both stages; the gap was service images referenced by mutable tag only: `postgres:16-alpine` and `redis:7-alpine` in `docker-compose.yml`, `gvenzl/oracle-free:23-slim` in `docker-compose.oracle.yml`, `postgres:16-alpine` in `docker-compose.sample-db.yml`, and the `postgres`/`redis` CI service containers in `.github/workflows/test.yml`. All resolved via `docker buildx imagetools inspect` and pinned `tag@sha256:digest` (keeps the tag readable alongside the immutable digest, matching the Dockerfile's existing style). Verified with `docker compose config` against the merged stacks. Added a `docker` ecosystem entry to `.github/dependabot.yml` (directory `/`, monthly) to track the Dockerfile + all 3 `docker-compose*.yml` files going forward — **known gap**: Dependabot's `docker` ecosystem doesn't scan `image:` strings inside GitHub Actions workflow YAML, so the two CI service-container pins in `test.yml` won't auto-update and need re-pinning by hand if they drift.
- [ ] Add a one-click deploy option (Railway/Render/Fly.io) to lower adoption friction beyond `docker compose up`.

---

# Phase 12 — Tailwind Migration (2026-07-06)

*Styling cleanup only — no behavior changes. `tailwindcss@4` + `@tailwindcss/postcss` are already
installed and configured (`tailwind.config.ts`, content globs cover `src/**/*.{ts,tsx}`); adoption is
just inconsistent. 54 of 62 `.tsx` files under `pages/`/`components/` still use inline
`style={{...}}` as their primary styling mechanism — **1,125 occurrences total** — while only
`Dashboard.tsx` mostly uses real Tailwind utility classes (`className="flex items-center gap-3"` etc.).
This phase converts the remaining 53 files, broken into 14 independently-completable chunks so no
single session has to touch the whole frontend at once.*

## Ground rules (apply to every chunk below)

- **Styling only.** Don't rename props, restructure components, or change behavior while converting a
  file — if something looks like it also needs a logic fix, note it and leave it for a separate task.
- **Inline styles that are fine to keep** (not part of this migration's scope): genuinely dynamic
  per-instance values that can't be expressed as a static utility class — e.g. `ProjectCard`'s
  user-chosen hex `color`, computed bar widths/heights in `Dashboard`'s mini run-history bars, and
  `Sk`/skeleton placeholder dimensions (deliberately one-off pixel widths approximating real content,
  not a real design token). Leave `style={{ width: dynamicValue }}`-shaped code exactly as-is.
- **Per-chunk definition of done:**
  1. No remaining `style={{...}}` in the chunk's files except the accepted exceptions above.
  2. `tsc --noEmit` and `eslint` clean.
  3. `npx vitest run` still green (existing component tests must not need rewrites — if a test asserts
     on inline style values, that's a sign the conversion changed observable behavior, not just markup).
  4. **Visually verified live** — start the backend + `npm run dev`, log in, and drive every affected
     page/state in a browser (see the project's `verify`/`webapp-testing` skills). Styling regressions
     don't show up in `tsc`/`eslint`/unit tests; screenshots before/after are the only real check.
  5. Committed as its own commit (or small PR) — don't bundle multiple chunks together, so a visual
     regression in one chunk is easy to `git revert` without losing unrelated work.
- **Order matters:** components before pages (chunks 12.1–12.4 before 12.5–12.13), since every page
  renders several of these shared components — converting them first means later page-level chunks
  aren't fighting a moving target.
- **`!important` is required to override `.card`/`.input`/`.textarea`/`.select`/`.btn`/`.btn-*`/`.chip`/
  `.tbadge`/`.pill`/`.tbl`/`.field`/`.label` on any property those classes already set.** *(found
  2026-07-08, during 12.7)* These custom classes live in `index.css` as plain (unlayered) CSS, while
  every Tailwind utility compiles into `@layer utilities`. Per the CSS Cascade Layers spec, unlayered
  CSS always wins over layered CSS for normal declarations, regardless of class order or specificity —
  so a plain utility class (`p-0`, `h-7`, `text-xs`, `bg-bg`, `text-failure-text`, etc.) placed after
  one of these class names to override one of its properties **silently does nothing**; the custom
  class's value renders instead. Verified via `getComputedStyle` against the live app, not just
  theory — e.g. `className="card p-0"` computed to `padding: 16px`, not `0px`. Fix: prefix the
  overriding utility with `!` (e.g. `!p-0`, `!h-7`, `!text-failure-text`) — Tailwind's `!important`
  modifier beats any non-important declaration regardless of layer, and `index.css` never uses
  `!important` itself, so this is always safe. `PipelineVariablesCard.tsx` and one spot in
  `WebhookCard.tsx` (both pre-Phase-12 conversions, outside any tracked chunk) already used this
  pattern correctly — but `WebhookCard.tsx` had two more instances that didn't (`btn btn-sm
  text-[var(--text-muted)]`/`text-[var(--failure-text)]`, silently rendering in `.btn`'s default text
  color instead); fixed those two in passing since they were trivial once diagnosed. The gap was not
  applying the pattern consistently, not not knowing about it. **Before marking any chunk done, grep
  the chunk's files for one of these class names combined with a same-property utility that lacks
  `!`** — sizing/spacing/color utilities are the highest-risk combination; `flex`/`gap`/`grid`/layout
  utilities on these classes are safe
  since none of them set layout properties.

## 12.0 Foundation — sync Tailwind theme with the full design-token set

- [x] `tailwind.config.ts`'s `theme.extend.colors` only maps 16 of the ~32 CSS custom properties
  defined in `src/index.css` (missing `text-3`, `failure`/`failure-text`, `success-text`,
  `running-text`, `accent-text`, `border-strong`, `bg-code`, `surface-hover`, and the `-soft`/`-glow`
  rgba variants), and there's no `boxShadow`/extended `borderRadius` mapping for `--shadow`/`--r-sm`
  /`--r`/`--r-lg`/`--r-xl` either. Extend the config to cover every token in `index.css` before
  converting any file — otherwise every chunk below has to fall back to arbitrary-value syntax
  (`text-[var(--text-3)]`) for half the tokens, which defeats the point and produces inconsistent
  conventions across chunks. Purely additive (no existing class changes), so this step alone should
  produce zero visual diff — confirm with a quick before/after screenshot of any one page.
  **Done 2026-07-07**: added the 15 missing color keys (`text-3`, `border-strong`, `accent-soft`,
  `accent-glow`, `success-soft`, `failure`, `failure-soft`, `running-soft`, `warn-soft`,
  `failure-text`, `success-text`, `running-text`, `accent-text`, `bg-code`, `surface-hover`) plus
  `borderRadius.{r-sm,r,r-lg,r-xl}` and `boxShadow.card`, all as `var(--...)` references into
  `index.css` (not hardcoded hex, unlike the pre-existing 16 keys) so they can never drift from the
  CSS source of truth. New keys use distinct names (e.g. `rounded-r-lg`, not `rounded-lg`) rather than
  overloading Tailwind's built-in radius/shadow scale, since a handful of files already use Tailwind's
  default `rounded-md`/`rounded-full` and overwriting those scale entries would have caused a real
  (not just theoretical) visual diff. Verified zero diff: `tsc --noEmit` and `eslint` clean, `npm run
  build` succeeds, and live-checked in-browser (Dashboard, Pipelines, Connections, Run History,
  Settings) via Playwright screenshots with zero console/API errors — all pixel-identical to
  pre-change appearance since no existing class or hardcoded value was touched.

## 12.1 Shared layout/chrome components — highest leverage, rendered on every page

- [x] `components/shared/Layout.tsx` (5 inline styles), `TopBar.tsx` (15), `ProjectSwitcher.tsx` (14),
  `PageIntro.tsx` (10), `HelpDrawer.tsx` (50), `RouteErrorBoundary.tsx` (9), `FieldTooltip.tsx` (6),
  `Skeleton.tsx` (1), `Spinner.tsx` (1) — 9 files, ~111 occurrences.
  Since these render on literally every page, test broadly: nav (collapsed/expanded), TopBar on at
  least 3 different pages, the project switcher dropdown, a help drawer open, and a forced route
  error (bad pipeline id) to check `RouteErrorBoundary`.
  **Done 2026-07-07**: converted all 9 files to Tailwind utility classes, using the tokens added in
  12.0 (`text-primary`, `text-muted`, `text-3`, `failure`, `bg-code`, `surface-hover`, `border-strong`,
  `rounded-r`/`rounded-r-sm`, etc.) instead of arbitrary `[var(--x)]` syntax wherever an exact-match
  token existed; fell back to arbitrary bracket values only for one-off pixel sizes, custom shadows, and
  the one hardcoded non-token hex (`#3D4460` in `ProjectSwitcher`'s open-state border) to avoid silently
  changing its value. JS `onMouseEnter`/`onMouseLeave` color-swap handlers (TopBar search results,
  ProjectSwitcher trigger button, PageIntro/FieldTooltip dismiss buttons) were replaced with CSS
  `hover:` variants — same visual outcome, no behavior change — including preserving hover-only-when-
  not-open conditionals via conditional class strings. Kept 4 `style={{}}` as accepted dynamic-value
  exceptions: `Layout.tsx`'s sparkbar bar height, `ProjectSwitcher`'s user-chosen project color,
  `Skeleton.tsx`'s `h`/`r` props (extracted the static `background`/`width` into a class, left the
  per-instance dimensions inline), and `Spinner.tsx`'s `size` prop (verified callers pass 11/12/13/20 —
  genuinely per-instance, not a static token).
  **One test-driven exception**: `HelpDrawer.test.tsx` asserts the dialog's inline `display` style
  directly (`toHaveStyle({ display: 'flex' })`); jsdom doesn't compile Tailwind so a `flex`/`hidden`
  class swap reads as `display: block` in tests despite being visually identical in a real browser.
  Per this phase's ground rules ("if a test asserts on inline style values, that's a sign the
  conversion changed observable behavior"), kept `style={{ display: open ? 'flex' : 'none' }}` on the
  `<dialog>` and converted every other property on it to classes — no test rewrite needed.
  Verified: `tsc --noEmit` and `eslint` clean, `npx vitest run` — 97/97 passing (including the
  HelpDrawer test unmodified), `npm run build` succeeds. Live-verified in-browser via Playwright:
  Dashboard, TopBar search dropdown, ProjectSwitcher dropdown, Help drawer (Help tab, Glossary tab,
  Settings-page provider guides with a step expanded), mobile viewport (hamburger + slide-out sidebar
  overlay), and a forced bad-pipeline-id route — zero console/API errors beyond the expected 404s for
  the nonexistent ID.

## 12.2 Pipeline step-form components + StepEditor

- [x] `components/pipeline/stepForms/*.tsx` (11 files: `BulkLoadForm` 7, `DataLoadForm` 22,
  `DbProcedureForm` 2, `DbQueryForm` 12, `DriveUploadForm` 1, `EmailForm` 14, `Field` 1,
  `NotificationForm` 4, `ReportForm` 1, `S3UploadForm` 3, `AzureBlobUploadForm` 3) plus
  `components/pipeline/StepEditor.tsx` (22) and `DependenciesCard.tsx` (3) — 13 files, ~95 occurrences.
  Test via Pipeline Builder: add one step of every type (11 step types) and confirm each form renders
  correctly, plus the Dependencies card.
  **Done 2026-07-07**: converted all 13 files. Notable finds along the way:
  - Every `<select className="input" style={{ height: 34 }}>` was pure dead weight — `.input` in
    `index.css` already sets `height: 34px`, so these were removed outright rather than converted to a
    class (fewer than the ~95 count implies actually needed a real conversion).
    `<textarea className="input mono-input" style={{ height: 'auto', resize: 'none' }}>` is the
    opposite case: NOT redundant, since these textareas use the `.input` class (not `.textarea`), so
    the override was necessary — converted to `h-auto resize-none` classes rather than dropped.
  - `StepEditor.tsx`'s parallel-group indigo accents (`rgba(99,102,241,0.5)`, `#6366f1`, `#818CF8`,
    `rgba(99,102,241,0.15)`) turned out to be exact matches for Tailwind's built-in `indigo-500`/
    `indigo-400` palette — used `border-indigo-500/50`, `border-l-indigo-500`, `bg-indigo-500/15`,
    `text-indigo-400` instead of arbitrary values, no config changes needed.
  - The `'#1a2e1a'` one-off "already attached" background (in `EmailForm`'s and `DataLoadForm`'s
    quick-attach buttons for preceding report/file steps) isn't a design token — kept as a literal
    `bg-[#1a2e1a]` arbitrary value rather than substituting a token with a different value.
  - `StepEditor.tsx`'s outer `<div style={{ ...style, marginBottom: 6 }}>` mixes a genuinely dynamic
    value (the `@dnd-kit/sortable` drag transform/transition object) with a static one — split them:
    `style={style}` stays inline (accepted dynamic-value exception), `marginBottom` moved to `mb-1.5`.
  - Caught and fixed two duplicate-`className` mistakes introduced mid-edit in `DataLoadForm.tsx`
    (leftover old `className="input mono-input"` line not removed when the replacement `className`
    was added a few lines below) before running any checks — would have been silently overwritten by
    JSX's "last prop wins" behavior otherwise, with the first `h-auto resize-none` value discarded.
  Verified: `tsc --noEmit` and `eslint` clean, `npx vitest run` — 97/97 passing, `npm run build`
  succeeds. Live-verified in Pipeline Builder via Playwright: added one step of all 10 built-in step
  types (`ai_analyze` has no dedicated form) and screenshotted every form — DbProcedureForm,
  DbQueryForm, ReportForm, EmailForm (including the report-attachment quick-add button states),
  DriveUploadForm, BulkLoadForm, DataLoadForm (source-type toggle, quick-attach button, Advanced
  options panel expanded), S3UploadForm, AzureBlobUploadForm, NotificationForm (switched to Telegram
  to confirm the conditional Bot token/Chat ID fields) — plus `DependenciesCard` with an actual
  dependency added (chip + delete button). Zero console/API errors throughout.
  **Retroactive fix 2026-07-08**: every `h-auto resize-none`/`h-auto resize-y` textarea override in
  this chunk (`StepEditor.tsx`, `DataLoadForm.tsx`, `DbProcedureForm.tsx`, `DbQueryForm.tsx`,
  `EmailForm.tsx`, `NotificationForm.tsx`) plus `StepEditor.tsx`'s compact retry/delay/parallel-group
  inputs, its on-error `<select>`, and `DependenciesCard.tsx`'s dependency `<select>` were silently not
  applying — see the new Ground rules entry above (unlayered `.input`/`.textarea` CSS beats layered
  Tailwind utilities without `!important`). Re-verified with `getComputedStyle` after adding `!` to
  each: heights/widths/font-sizes now match intent instead of falling back to `.input`'s 34px/13px
  defaults. Also caught and fixed the same issue on `StepEditor.tsx`'s delete button
  (`hover:text-failure-text` → `hover:!text-failure-text`, since `.btn-ghost:hover` is itself an
  unlayered rule).

## 12.3 Connections sub-components

- [x] `components/connections/*.tsx` (12 files: `DbFieldsGeneric` 4, `DbFieldsOdbc` 1,
  `DbFieldsSnowflake` 3, `DbFieldsBigQuery` 1, `MailFieldsSmtp` 5, `MailFieldsOAuth` 2,
  `MailFieldsSes` 1, `MailFieldsMailgun` 2, `Field` 1, `StatCol` 3, `DbConnectionRow` 12,
  `EmailProviderRow` 12) — ~47 occurrences.
  Test via Connections page: open the add/edit form for every DB type and every email provider type.
  **Done 2026-07-07**: converted all 12 listed files (`MailFieldsSendgrid.tsx`, the 13th file in this
  directory, already had zero inline styles — nothing to do there). Notable finds:
  - `DbConnectionRow.tsx`'s and `EmailProviderRow.tsx`'s type-icon boxes: `DbConnectionRow`'s uses a
    genuinely dynamic per-db-type color (`DB_COLORS` map, 8 values) combined with computed hex-alpha
    suffixes (`${color}22`/`${color}55`) for background/border — kept as an inline-style exception
    (same category as the already-accepted `ProjectSwitcher`/`ProjectCard` "user-chosen color"
    pattern), only extracting the static `width`/`height`/`borderRadius`/layout properties to a class.
    `EmailProviderRow`'s icon box, by contrast, uses a **fixed** literal color regardless of provider
    type — its background matched `--accent-soft` exactly (`bg-accent-soft`), but its border
    (`rgba(249,115,22,0.3)`) didn't match any existing token (`--accent-glow` is 0.25, not 0.3), so
    that one stayed an arbitrary `border-[rgba(249,115,22,0.3)]` rather than being coerced onto a
    close-but-not-equal token.
  - Every `<select className="input" style={{ height: 34 }}>` (in `MailFieldsMailgun.tsx`) was
    redundant for the same reason found in chunk 12.2 — `.input`'s own CSS already sets `height: 34px`
    — so removed rather than converted.
  Verified: `tsc --noEmit` and `eslint` clean, `npx vitest run` — 97/97 passing, `npm run build`
  succeeds. Live-verified on the Connections page via Playwright: opened the Add Connection modal and
  cycled through all 8 DB types (PostgreSQL, Oracle, MySQL/MariaDB, SQL Server, Generic ODBC, Redshift,
  Snowflake, BigQuery) and all 6 email provider types (SMTP, Gmail, Microsoft 365, SendGrid, AWS SES,
  Mailgun) via the modal's internal Database/Email Provider toggle, screenshotting every form — plus
  the underlying `DbConnectionRow`/`EmailProviderRow` list views (3 DB connections, 3 email providers)
  visible around the modal. Zero console/API errors throughout.
  **Retroactive fix 2026-07-08**: `DbFieldsBigQuery.tsx`'s `h-auto resize-none` credentials-JSON
  textarea had the same silently-ignored-override bug as chunk 12.2 (see Ground rules) — fixed to
  `!h-auto !resize-none`.

## 12.4 Misc remaining components

- [x] `components/bulkloads/BulkLoadRow.tsx` (13), `components/runs/StepTrendsPanel.tsx` (12),
  `components/report/ChartPreview.tsx` (10) — 3 files, ~35 occurrences.
  Test via Bulk Loads list (Test button states), Run History's Performance Trends panel (expanded,
  with real data), and Report Designer's chart preview (each of the 5 chart types).
  **Done 2026-07-07**: converted all 3 files. Notable finds:
  - `BulkLoadRow.tsx`'s `const ACCENT = '#FB923C'` looked like the same "dynamic per-instance color"
    exception as `DbConnectionRow`'s icon box (chunk 12.3), but isn't — it's a fixed module-level
    constant, not derived from data, so it was fully converted to classes (`bg-[#FB923C22]
    border-[#FB923C55] text-[#FB923C]`, preserving the exact 8-digit-hex alpha bit-for-bit) and the
    now-unused constant deleted, rather than kept as a `style={{}}` exception.
  - `ChartPreview.tsx`/`StepTrendsPanel.tsx` both define `axisStyle`/`gridStroke`/`tipStyle` objects
    passed to Recharts component props (`tick={axisStyle}`, `{...tipStyle}`) — these configure SVG
    chart internals via Recharts' own prop API, not a JSX `style={{}}` DOM attribute, so they're out of
    this migration's scope and were left untouched (Recharts doesn't accept Tailwind classes here).
  - `ChartPreview.tsx`'s `selectStyle` object (applied to the X/Y axis `<select>`s) was fully static
    (not data-dependent) and got converted to a shared `selectClass` string reused on both selects.
  - Chart-pill active-state colors in both files use literal `rgba(249,115,22,0.12/0.45)` — close to
    but not matching `--accent-soft` (0.14) or `--accent-glow` (0.25) — kept as arbitrary values rather
    than snapped onto a similar-but-wrong existing token, same judgment call as chunk 12.3.
  Verified: `tsc --noEmit` and `eslint` clean, `npx vitest run` — 97/97 passing, `npm run build`
  succeeds. Live-verified via Playwright: Bulk Loads list showing both the "ok" and "warn" (yellow dot)
  `Test` states with real preview data; Run History's Performance Trends panel expanded with the day
  window pill toggle (7d/30d/90d) exercised, confirming active/inactive pill styling; Report Designer's
  chart toolbar (title, all 5 chart-type pills, X/Y column selects) cycled through Bar/Line/Area/Pie/
  Scatter on a real 20-row query result. One dead end investigated and resolved: the actual chart body
  (bars/lines/points) rendered as an empty SVG canvas in the headless Playwright run — traced this down
  to a `ResponsiveContainer`/`ResizeObserver` measurement issue by confirming via `getBoundingClientRect`
  that the container had the correct computed dimensions and zero console/React errors, then proved it
  wasn't a regression by `git stash`-ing this chunk's `ChartPreview.tsx` change and reproducing the
  identical blank-canvas behavior against the pre-conversion inline-style code — same result, confirming
  it's a pre-existing headless-browser/Recharts environment quirk unrelated to this styling pass.
  **Retroactive fix 2026-07-08**: `ChartPreview.tsx`'s and `StepTrendsPanel.tsx`'s `card p-0
  overflow-hidden` wrapper had the silently-ignored-`p-0` bug (see Ground rules) — fixed to
  `card !p-0 overflow-hidden`; `getComputedStyle` confirmed padding now computes to `0px`.

## 12.5 `pages/RunDetail.tsx` — standalone (111 occurrences, most complex page)

- [x] Header, stats grid, progress bar, diff panel, anomaly badges, AI narrative modal, timeline steps
  (success/failed/running/skipped), and the loading skeleton added 2026-07-06. Test with a real
  success run, a real failed run if one exists, and the loading state.
  **Done 2026-07-08**: converted the whole file (all 9 components: `AnomalyRow`, `StepStatusIcon`,
  `StepLogsTab`, `StepOutputTab`, `StepInfoTab`, `DiagnosisPanel`, `AnomalyPanel`, `TimelineStep`,
  `DeltaBadge`, `DiffPanel`, plus the page component itself). Notable finds:
  - The per-status color lookups (`STATUS_COLOR` for the rail icon/border, a local `statusColors` for
    the duration text) were plain CSS-var strings fed into inline `style`, but each only ever takes one
    of 3-4 known values — replaced with `STATUS_TEXT_CLS`/`STATUS_BORDER_CLS`/`DURATION_TEXT_CLS`
    lookup tables of Tailwind classes instead, so the "dynamic" value is a conditional class swap (same
    pattern already used for tab/step-type styling elsewhere), not a genuine exception. Same treatment
    for the progress bar's per-step `barBackground` (success/running-gradient/failed/pending) — only
    the `flex` proportional-to-`duration_ms` value stays inline, since that's a real continuous number.
  - `StepStatusIcon` took an unused-outside-itself `statusColor` CSS-var prop just to color one 6px
    "running" dot — dropped the prop entirely and hardcoded `bg-running` on that one span, since it's
    the only state that ever renders it (simpler than threading a class through).
  - Extensive `rgba(249,115,22,0.NN)` "AI/anomaly" orange tints throughout (`AnomalyRow`,
    `DiagnosisPanel`, `AnomalyPanel`) use six different alpha values (0.03/0.06/0.1/0.15/0.2/0.3), none
    of which match `--accent-soft` (0.14) or `--accent-glow` (0.25) — kept every one as an arbitrary
    `bg-[rgba(...)]`/`border-[rgba(...)]` value rather than coercing onto a close token, same judgment
    call as chunks 12.3/12.4. Solid `#F97316` uses (icon/text colors, not tints) converted to `text-accent`
    since that's an exact match. The diff table's `#818CF8`/`rgba(99,102,241,...)` "new step" indigo
    badge got the same treatment as chunk 12.2's `StepEditor` indigo accents — `text-indigo-400` for
    the exact Tailwind-palette match, arbitrary `bg-[rgba(99,102,241,0.15)]` for the non-matching tint.
  - `borderRadius: 6` and `borderRadius: 8` look interchangeable at a glance but map to two different
    tokens (`--r-sm` vs `--r`) — checked each of the file's 6 distinct radius values individually rather
    than assuming; `4` turned out to exactly match Tailwind's own unthemed `DEFAULT` (`rounded`, 4px),
    so that one needed no custom token or arbitrary value at all.
  - The component-local `<style>{'@keyframes shimmer {...}'}</style>` (progress-bar running-step
    shimmer) was the only keyframe defined inside a component in the whole codebase, while an
    equivalent `ff-pulse` already lives in `index.css` — moved `shimmer` into `index.css` next to it and
    referenced both via `animate-[name_timing]` arbitrary values, deleting the local `<style>` tag.
    Zero visual diff, just consistency with how the one other custom keyframe is already handled.
  - Left every `<Sk .../>` skeleton placeholder's `style={{ width, marginBottom, flexShrink }}` prop
    completely untouched (matching the already-converted `Dashboard.tsx` precedent for the same
    component) — these are accepted per this phase's ground rules as one-off content-approximating
    dimensions, not real design tokens.
  Verified: `tsc --noEmit` and `eslint` clean, `npx vitest run` — 97/97 passing, `npm run build`
  succeeds. Live-verified via a real dev Postgres + Flask + Vite stack (Playwright, headless): the
  one pre-existing real success run (header, stats grid, green progress bar, expanded timeline step,
  all 3 tabs — Logs/Output/Info — and the "Diff vs previous run" toggle); a genuine failed run created
  on the fly (a throwaway pipeline with a deliberately-broken `db_query` step, run via the API and
  deleted again afterward) confirming the FAILED badge, red progress bar, red error banner, red
  timeline circle/border, and the "Explain this error" → expanded AI Diagnosis panel (fell back to
  "Could not reach Ollama" text since Ollama isn't running locally — expected, not a regression); and
  the loading skeleton, captured by delaying the run-detail API response via Playwright route
  interception. Zero console/React errors in any state (aside from the expected 503 when probing the
  unavailable local Ollama). Anomaly-panel styling (rows/duration outlier badges) could not be
  live-triggered — it requires 30 prior runs of real statistical history that don't exist in a fresh
  dev DB — so it was verified by inspection instead: it reuses the same `AnomalyRow`/arbitrary-rgba
  classes already exercised and screenshotted in the diagnosis-panel state above.
  **Retroactive fix 2026-07-08**: found (while starting chunk 12.7) that `.card`/`.chip` are unlayered
  CSS that Tailwind utilities can't override without `!important` (see new Ground rules entry) — this
  chunk had 4 silent instances: the diff-panel's `card p-0` (would-be 16px padding instead of flush),
  the 3 stat cards' `card py-3.5 px-4` (16px vertical padding instead of the intended 14px), and the
  email-recipient `chip h-5 text-[11px]` (stuck at the default 24px/12px instead of the intended
  compact size). All fixed with `!`; re-verified via `getComputedStyle`.

## 12.6 `pages/ReportEdit.tsx` — standalone (104 occurrences)

- [x] Includes the CodeMirror SQL editor panel and `ChartPreview` integration (already converted in
  12.4 — don't reconvert). Test create-new and edit-existing, all 3 formats (Excel/CSV/PDF), and the
  query preview table.
  **Done 2026-07-08**: converted the whole file (`ColumnFormattingCard` plus the page component).
  Notable finds:
  - The "SQL editor" is actually a plain styled `<textarea>`, not CodeMirror — `CLAUDE.md` names
    CodeMirror 6 as the intended stack but it was never wired up here. Out of scope for a styling-only
    pass; converted the textarea's inline styles as-is and left a note rather than touching behavior.
  - The format-selector buttons (Excel/CSV/PDF/JSON) are a clean 2-state-per-button toggle (active vs.
    inactive) fed by CSS-var strings in inline `style` — same pattern as chunk 12.5's status colors,
    same fix: a single conditional class string per button instead of inline style, so the "dynamic"
    part is which of two known class sets applies, not a real per-instance value.
  - Two more `<select className="input" style={{ height: 34 }}>` dead-weight overrides found (Data
    source connection picker) — removed rather than converted, same as chunks 12.2/12.3's finding that
    `.input`'s own CSS already sets `height: 34px`.
  - `#3B82F6` (the data-profiling consent banner's `Activity` icon) is an exact match for `--running`,
    converted to `text-running` even though the surrounding banner has nothing to do with run status —
    token match is about the color value, not the semantic context.
  - The optimization/explanation/profile panels' "original vs. suggested" tinted backgrounds
    (`rgba(239,68,68,0.02/0.04)`, `rgba(34,197,94,0.02/0.05)`) are faint one-off diff-view tints, not
    reused anywhere else — kept as arbitrary values (none are close to the failure/success-soft tokens
    either, at 0.14).
  Verified: `tsc --noEmit` clean, `eslint` clean (one pre-existing unrelated warning on
  `react-hooks/incompatible-library` for `useForm().watch()`, untouched by this change), `npx vitest
  run` — 97/97 passing, `npm run build` succeeds. Live-verified via the same dev Postgres + Flask +
  Vite stack as 12.5 (Playwright, headless): created a new report and cycled all 4 formats (Excel/CSV/
  PDF/JSON — confirming the Sheet-name/Title/Column-Formatting fields correctly show/hide per format),
  filled and saved it, then deleted it again afterward; opened a real pre-existing Excel report
  ("Product Stock Summary"), added a column-formatting rule plus a conditional sub-rule to check that
  card's full row layout, and ran a real query preview against Retail-DB (20-row mono table, "Visualize"/
  "Summarise" actions appearing in the TopBar once preview data existed). Zero console/React errors
  throughout.
  **Retroactive fix 2026-07-08**: this was the chunk where the unlayered-CSS-vs-Tailwind-utility bug
  (see new Ground rules entry) was actually discovered, while starting 12.7. Every `card p-0
  overflow-hidden` panel (SQL editor, optimization diff, explanation, preview table, profile result —
  6 instances), the entire `ColumnFormattingCard`'s compact-sized inputs/selects (6 instances), the SQL
  editor's flush-styled textarea (`bg-bg`/`border-none`/`rounded-none`/custom padding/`text-text-2`),
  and one `btn btn-sm text-[11px]` "Add condition" button were all silently not applying — the page
  visually looked "close enough" in screenshots (e.g. a 16px vs. 0px card padding difference is subtle
  at screenshot resolution) but every one of these was confirmed broken via `getComputedStyle` and
  fixed with `!`. Re-verified after the fix: SQL editor textarea now computes to `background:
  rgb(15,17,23)` (`--bg`, not `--surface`), `padding: 14px 16px`, `border: 0px none`; the column-name
  input now computes to `height: 28px, font-size: 12px` instead of `.input`'s 34px/13px defaults.

## 12.7 `pages/Settings.tsx` + `pages/BulkLoadEdit.tsx` (75 + 73 = 148 occurrences)

- [x] `Settings.tsx`: all 4 tabs (Account, Email & AI, System, Docs), MFA enrollment flow.
  `BulkLoadEdit.tsx`: new + edit, Test File preview (with and without dry-run insert errors), the
  loading skeleton.
  **Done 2026-07-08**: converted both files (`Settings.tsx`'s `StatusBadge`/`CodeBlock`/`InlineCode`/
  `ChangePasswordCard`/`GoogleOAuthCard`/`Microsoft365Card`/`AiOllamaCard`/`YamlCard`/`DocsCard`/
  `MfaCard`/`RetentionCard` plus the page shell; `BulkLoadEdit.tsx`'s loading skeleton and the full
  `BulkLoadForm`). This was the chunk where the `!important`-for-unlayered-CSS bug (see Ground rules,
  and the retroactive-fix notes on 12.2–12.6 above) was actually discovered and fixed — every override
  written for this chunk used the correct `!` pattern from the start; see the dedicated fix commit for
  the retroactive repair of 12.2–12.6. Notable finds specific to this chunk:
  - Three `onMouseEnter`/`onMouseLeave` handlers toggling `e.currentTarget.style.textDecoration`
    (`GoogleOAuthCard`, `Microsoft365Card`, `DocsCard`'s doc links) replaced with `hover:underline` —
    same pattern chunk 12.1 established for `TopBar`/`ProjectSwitcher`.
  - The MFA status pill (`Active`/`Disabled`) and the Settings tab-row buttons are both clean 2-state
    toggles fed by CSS-var strings in inline `style` — converted to conditional Tailwind class strings
    (same treatment as chunk 12.5's status-color maps and RunDetail's tab buttons), not a genuine
    per-instance-value exception.
  - `BulkLoadEdit.tsx`'s "Output variables" hint card intentionally overrides `.card`'s own background/
    border with a distinct orange tint (`rgba(251,146,60,0.04)`/`0.15`) — this is exactly the
    unlayered-CSS conflict from the new Ground rules entry, so it needed `!bg-[...] !border-[...]`
    from the start; confirmed via `getComputedStyle` that both properties compute to the intended
    values, not `.card`'s defaults.
  - `TriangleAlert`'s warning-banner color `#EAB308` is an exact match for Tailwind's built-in
    `yellow-500` — used `text-yellow-500` instead of an arbitrary value.
  - Found and fixed two more instances of the same `!`-less bug while auditing this chunk's
    surroundings: `WebhookCard.tsx`'s dismiss/revoke buttons (`btn btn-sm text-[var(--...)]`, outside
    any tracked chunk) — see the dedicated fix commit.
  Verified: `tsc --noEmit` clean, `eslint` clean (same pre-existing unrelated `watch()` warning as
  12.6, in an unrelated file), `npx vitest run` — 97/97 passing, `npm run build` succeeds.
  Live-verified via the same dev stack as 12.5/12.6 (Playwright, headless): all 4 Settings tabs
  screenshotted (Account's Change Password + MFA cards, Email & AI's three provider/AI cards, System's
  retention + YAML cards, Docs' link list); started real MFA enrollment (real QR code rendered,
  6-digit code input showing the intended large letter-spaced styling — confirming the `!text-lg`
  fix). For `BulkLoadEdit.tsx`: the New Bulk Load form's full 2-column layout, client-side field
  validation errors (Name/Source directory/Target table), the Test File error banner (no source dir),
  and a real Test File run against a throwaway 3-row CSV + `FlowForge DB` connection with a
  deliberately-nonexistent target table — confirming the warning banner (yellow), the flush `!p-0`
  preview card (header/table right up to the card edges, matching the pre-conversion design), and the
  mono data table. Cleaned up the test CSV/directory afterward (no bulk-load config was ever saved, so
  no DB cleanup needed). Zero console/React errors throughout.

## 12.8 `pages/Connections.tsx` + `pages/EmailEdit.tsx` (55 + 53 = 108 occurrences)

- [x] `Connections.tsx`: list + add/edit for at least 2 DB types and 2 provider types (their sub-forms
  were converted in 12.3 — don't reconvert). `EmailEdit.tsx`: new + edit, recipient group picker,
  preview modal.
  **Done 2026-07-08**: converted both files. Notable finds:
  - `Connections.tsx`'s `TEST_STYLES` object (bg/border/color/dot CSS-var strings keyed by
    `ok`/`fail`/`idle`) fed inline `style` the same way chunk 12.5's `STATUS_COLOR` did — replaced with
    `TEST_CLS`/`TEST_DOT_CLS` Tailwind-class lookup tables (same fix, same reasoning: a fixed 3-state
    enum isn't a genuine per-instance dynamic value). Same treatment for the modal's Database/Email
    Provider toggle buttons and the page's own Databases/Email Providers tab row.
  - The `<div className="card" style={{ padding: 16 }}>` skeleton-row wrapper (used twice, once per
    tab's loading state) turned out to be fully redundant — `.card`'s own CSS already sets
    `padding: 16px` — so the override was dropped entirely rather than converted, same category as
    chunk 12.2/12.3's dead `height: 34` finds.
  - `EmailEdit.tsx`'s `ChipInput` (used for To/CC/BCC addresses) was already written in Tailwind
    (pre-dating Phase 12) but referenced `className="badge-muted"` for each address pill — a class
    that is **not defined anywhere in `index.css`**, so every pill rendered completely unstyled (no
    background, border, or padding — just bare text). Replaced with the existing `.chip` class (same
    "removable pill" semantics already used elsewhere, e.g. `RunDetail.tsx`'s email-recipient chips)
    and added the missing `className="x"` to the remove button so it also picks up `.chip .x`'s
    hover-color treatment. `Recipients.tsx` has an identical copy of `ChipInput` with the same dead
    class — left as-is for its own chunk (12.11), noted here so it isn't missed.
  - The body-template and drive-share-message textareas needed care distinguishing real conflicts from
    false alarms: `mono-input` already sets `font-size: 12.5px` (unlayered), which happens to exactly
    match the body textarea's intended size — so no `!` was needed there, but the drive-message
    textarea wanted `11.5px`, a real mismatch, so that one got `!text-[11.5px]`. Neither textarea
    needed `!` for its `min-h-[...]`/`resize-y` despite `.input` setting a fixed `height`/no explicit
    `resize` — `.textarea`'s `resize: none` only matches elements with the literal class `textarea`
    (neither element has it), and `min-height` naturally wins over a smaller `height` per the CSS box
    model regardless of cascade layer, so both apply correctly without an override marker. Verified via
    `getComputedStyle`, not just this reasoning: computed height 420px, font-size 12.5px/11.5px,
    resize: vertical on both.
  - `PipelineEdit.tsx` (not yet converted, chunk 12.9) already had one line using `accent-[var(--accent)]`
    for a checkbox — reused that exact convention for `EmailEdit.tsx`'s attachment-size range slider
    instead of introducing a different pattern.
  Verified: `tsc --noEmit` clean, `eslint` clean (same pre-existing unrelated `watch()` warning),
  `npx vitest run` — 97/97 passing, `npm run build` succeeds. Live-verified via the same dev stack
  (Playwright, headless): Connections' Databases and Email Providers tabs; the Add Connection modal
  cycled through both Database/Email Provider toggle states, selected Snowflake to check its
  sub-fields, and ran a real Test that failed (`snowflake-connector-python` not installed) — confirming
  the red fail-state banner and red status dot render correctly, not just the default idle state. For
  `EmailEdit.tsx`: the full new-config form (all cards, the attachment-size slider, the now-tall body
  textarea, the variable-reference chips) and added two real To-address chips to confirm the
  `badge-muted` → `.chip` fix actually renders visible pills. Zero console/React errors throughout.

## 12.9 `pages/Projects.tsx` + `pages/RunHistory.tsx` (53 + 51 = 104 occurrences)

- [x] `Projects.tsx`: project cards grid, create/edit modal, members modal. `RunHistory.tsx`: filters,
  table, the Performance Trends panel (converted in 12.4 — don't reconvert), loading skeleton.
  **Done 2026-07-08**: converted both files (`ColorPicker`, `ProjectModal`, `MembersModal`,
  `ProjectCard`, plus both page components). Notable finds:
  - `ProjectCard`'s active-border color, its color dot, and the "Active filter" badge's color/dot all
    depend on `project.color` (a genuinely per-project user-chosen hex, the exact case this phase's
    ground rules already name as an accepted exception) — kept those specific properties inline while
    converting every static property around them (layout, sizing, cursor) to classes.
  - `RunHistory.tsx`'s mini-stats array had a `soft: 'rgba(...)'` field on each entry that turned out to
    be dead — never read anywhere in the render (confirmed by grep before touching it) — dropped while
    replacing the array's CSS-var `color` strings with Tailwind `dotCls` classes (same conditional-class
    treatment as chunk 12.5/12.8's status maps).
  - Caught two self-introduced instances of exactly the bug this phase's new ground rule exists to
    prevent: two `card py-3.5 px-4` wrappers (the loading-skeleton stat row and the real mini-stat
    cards) written without the required `!`, so `.card`'s own `padding: 16px` would have silently won
    over the intended `14px`/`16px` split. Caught by the same grep sweep the ground rule now
    prescribes, before running any checks — fixed to `!py-3.5 !px-4`.
    Elsewhere in this chunk, several properties looked like conflicts but weren't after checking each
    against `.tbl`'s actual rule set: `.tbl td`'s `color: var(--text-2)` conflicts with `!text-text-3`/
    `!text-text-primary` overrides (needed `!`), but `.tbl` (the table itself) only sets `font-size`,
    which is inherited into `<td>`s rather than matched by a `.tbl td` rule — so a plain `text-[11.5px]`
    utility on a `<td>` correctly wins over the inherited size without `!`, and a nested `<span>`'s own
    color utility correctly wins over color inherited from its parent `<td>`, also without `!` — neither
    inheritance case needed the marker, only the two direct `color`-on-`<td>` conflicts did.
  - `MembersModal`'s remove-member button had `style={{ color: 'var(--text-muted)' }}` on a
    `btn-ghost`-classed element — `.btn-ghost`'s own CSS already sets that exact color, so the override
    was redundant and dropped entirely rather than converted.
  - `ProjectCard`'s delete button used `onMouseEnter`/`onMouseLeave` to toggle failure-red on hover —
    replaced with `hover:!text-failure-text` (needs `!` here specifically because `.btn-ghost:hover` is
    itself an unlayered rule setting `color: var(--text)`, same reasoning as chunk 12.7's
    `StepEditor.tsx` fix).
  Verified: `tsc --noEmit` and `eslint` clean (zero warnings, no pre-existing `watch()` noise in either
  file), `npx vitest run` — 97/97 passing, `npm run build` succeeds. Live-verified via the same dev
  stack (Playwright, headless): Projects' card grid (default + non-default project, showing the
  members-only vs. edit+delete+members icon sets), the New Project modal with its 8-swatch color
  picker, and the Members modal (existing admin member, add-user select, Add button). For
  `RunHistory.tsx`: the main list with real success/failed runs (including a `(deleted)`-tagged pipeline
  from an earlier chunk's throwaway test data), the 24h/7d/30d/All time-tab toggle, a search filter
  producing the "No runs match your filters" empty state, and the Performance Trends panel expanded
  with real chart data. Zero console/React errors throughout.

## 12.10 `pages/Pipelines.tsx` + `pages/Login.tsx` (50 + 46 = 96 occurrences)

- [x] `Pipelines.tsx`: list, filters, promote modal, import/export. `Login.tsx`: sign-in form, MFA
  step-2 input, SSO buttons (if configured), forgot-password link.
  **Done 2026-07-08**: converted both files (`Pipelines.tsx`'s `FilterChip` plus the page component;
  `Login.tsx`'s 7-step auth state machine plus `ErrorBox`). Notable finds:
  - `FilterChip`'s `style={{ gap: 4 }}` on a `btn btn-sm` button conflicted with `.btn`'s own
    `gap: 6px` (unlayered) — needed `!gap-1`. Caught by the grep sweep before running checks, not
    after — the ground rule from chunk 12.9's near-miss is already paying for itself.
    Same fix needed on `Login.tsx`'s three SSO buttons (`gap: 8` vs. `.btn`'s `gap: 6px`) and the
    "Use a backup code instead" button (`font-size: 12`/`color: text-muted` vs. `.btn`'s own
    `font-size: 12.5px`/`color: text`).
    Login's promote-pipeline "Got it" button and every full-width submit button used
    `justifyContent: 'center'` alongside `.btn`'s own already-`center` default — redundant, dropped
    rather than converted, matching the established "don't convert what's already the default"
    precedent from chunks 12.2/12.3.
  - Two more hover-color-toggle patterns (`Pipelines.tsx`'s row-name link and delete button) replaced
    with `hover:!text-accent-text`/`hover:!text-failure-text` — same reasoning as chunks 12.7/12.9's
    `.btn-ghost:hover` fix, generalized here to a plain link with no matching unlayered hover rule at
    all (so no `!` was actually required for the link's hover, only for the button's, since
    `.btn-ghost:hover` is the one unlayered rule in play).
  - `Pipelines.tsx`'s steps-count `<td className="mono" style={{ color: 'var(--text-2)' }}>` was
    redundant — `.tbl td` already sets that exact color — dropped entirely rather than kept as a
    matching-but-pointless override.
  - `Login.tsx`'s MFA code input reused the identical `!text-lg` fix already verified working on
    Settings.tsx's MFA card in chunk 12.7 (same `.input` font-size conflict, same resolution).
  Verified: `tsc --noEmit` and `eslint` clean (zero warnings), `npx vitest run` — 97/97 passing,
  `npm run build` succeeds. Live-verified via the same dev stack (Playwright, headless): the full
  credentials → forgot-password → "check your email" confirmation → back-to-sign-in → real
  successful login round-trip (reaching `/dashboard`), and separately the Pipelines list, filter
  chips, and the Promote modal (opened on the one seeded pipeline, confirming the `!p-6` padding
  fix visibly matches the intended generous modal spacing vs. `.card`'s tighter 16px default). The
  MFA-code/backup-code/reset-password steps were verified by code inspection rather than a full live
  TOTP round-trip — they reuse byte-for-byte the same input-styling classes already empirically
  confirmed correct on Settings.tsx's MFA card, and building a throwaway TOTP session for a
  styling-only chunk wasn't worth the added complexity. Zero console/React errors throughout.

## 12.11 `pages/Users.tsx` + `pages/AuditLog.tsx` + `pages/Recipients.tsx` (32 + 30 + 25 = 87 occurrences)

- [x] `Users.tsx`: list, add-user form, role changes. `AuditLog.tsx`: table + filters + loading
  skeleton (2026-07-06). `Recipients.tsx`: list, inline add/edit rows, chip input.
  **Done 2026-07-08**: converted all three files (`Users.tsx`'s `RoleBadge` plus the page; the whole of
  `AuditLog.tsx`; `Recipients.tsx`'s `ChipInput`/`GroupRow` plus the page). Notable finds:
  - `Recipients.tsx`'s `ChipInput` had the exact same dead `badge-muted` class bug flagged (but left
    for this chunk) in chunk 12.8 — fixed identically: replaced with `.chip` plus a `className="x"` on
    the remove button for the hover treatment.
  - `AuditLog.tsx`'s two filter inputs referenced `className="input-wrap"`/`"input input-sm"` —
    **also neither class is defined anywhere in `index.css`**, a second, previously-unknown instance of
    the same "dead class, unstyled at runtime" bug family as `badge-muted`. Unlike `badge-muted` there
    was no adjacent real class with matching intent to swap in, so these were rebuilt from scratch using
    the icon+bordered-box search-input pattern already established in `RunHistory.tsx`/`Pipelines.tsx`
    (chunks 12.9/12.10) for consistency, rather than inventing a fourth visual treatment for the same
    concept.
  - `Users.tsx`'s `RoleBadge` (admin/editor/viewer, a genuine fixed 3-state enum) converted to a
    Tailwind class map the same way as chunks 12.5/12.8/12.9's status maps; `editor`'s `#60A5FA` and
    `admin`'s exact-token `var(--accent-text)` were kept precise (`text-blue-400` and `text-accent-text`
    respectively) while the non-matching `rgba(...)` background tints stayed arbitrary.
  - `AuditLog.tsx` and `Recipients.tsx` both render real `<table className="tbl">` markup, unlike
    `Users.tsx`'s plain unclassed table — every `.tbl td` color override needed `!` (e.g. the group
    name/description cells), while padding-left/font-size overrides on the same cells did not, per the
    inheritance-vs-direct-match distinction nailed down in chunk 12.8. Both tables' empty-state cells
    (`text-align/padding/color` on a bare `<td>`) needed the same `!py-10 !px-0 !text-text-muted`
    treatment as `RunHistory.tsx`'s chunk-12.9 empty state.
  - `Recipients.tsx`'s `GroupRow` edit-mode name/description inputs (`style={{ height: 32 }}`) and the
    "New Group" form's intentional accent-tinted border (`borderColor: 'rgba(249,115,22,0.3)'`, a fixed
    constant rather than a per-instance value) both needed `!h-8`/`!border-[rgba(249,115,22,0.3)]`
    respectively against `.input`/`.card`'s own defaults.
  Verified: `tsc --noEmit` and `eslint` clean (zero warnings), `npx vitest run` — 97/97 passing,
  `npm run build` succeeds. Live-verified via the same dev stack (Playwright, headless): Users' table
  (admin's own row showing the `(you)` tag, ADMIN role badge, OFF MFA badge, export-only actions since
  self-actions are hidden) and the Add User modal; Audit Log's real login-event history with the two
  rebuilt filter boxes rendering identically to the established search-box pattern; Recipients' existing
  group row (compact chip pill) and a new-group form exercising the chip input live (added two real
  address chips, confirming visible pill styling instead of the previous unstyled bare text) plus the
  accent-tinted form border. Zero console/React errors throughout.

## 12.12 `pages/Emails.tsx` + `pages/BulkLoads.tsx` + `pages/Reports.tsx` (24 + 22 + 21 = 67 occurrences)

- [x] All three are simple list pages (empty state + table) — good chunk to pair with a newer
  contributor or do quickly once the pattern is well-established from earlier chunks.
  **Done 2026-07-08**: converted all three files. As expected, the fastest chunk so far — no new
  patterns, no dead classes, no surprises. `Emails.tsx` and `Reports.tsx` both use real `.tbl` tables
  (provider/subject/filename cells needed `!` for color overrides, same inheritance-vs-direct-match
  distinction as every prior `.tbl`-using chunk); `BulkLoads.tsx` delegates its rows to the already-
  converted `BulkLoadRow` (chunk 12.4) and just needed its own loading-skeleton/empty-state wrapper
  converted, including dropping one more `style={{ padding: 16 }}` that was redundant against `.card`'s
  own default (same class of finding as chunks 12.2/12.3/12.9).
  Verified: `tsc --noEmit` and `eslint` clean (zero warnings), `npx vitest run` — 97/97 passing,
  `npm run build` succeeds. Live-verified via the same dev stack (Playwright, headless): Emails' empty
  state (no configs seeded), Bulk Loads' real config row (rendered through the untouched `BulkLoadRow`
  component, confirming this page's wrapper conversion didn't disturb it), and Reports' two real
  configs with EXCEL format badges and mono filenames. Zero console/React errors throughout.

## 12.13 `pages/Dashboard.tsx` — cleanup pass (12 occurrences)

- [x] Already ~90% Tailwind (see the file for the target style) — just finish the remaining inline
  styles for full consistency. Smallest chunk; good last step to close out the phase.
  **Done 2026-07-08**: all 12 originally-listed `style={{...}}` occurrences turned out to already be
  accepted exceptions per this phase's ground rules — 11 are `Sk` skeleton placeholder dimensions and
  the 12th is the mini run-history bar's per-instance `background`/`opacity` (the exact case the ground
  rules name explicitly) — so none needed conversion. The real work in this chunk was auditing the
  ~90% that was *already* Tailwind, since Dashboard.tsx predates Phase 12 and had never been checked
  against the `!important`-for-unlayered-CSS ground rule added in chunk 12.7. That audit found and
  fixed real, currently-live bugs (verified via `getComputedStyle` before and after, not just
  theory):
  - The 4 stat cards' `card p-[16px_18px]` (both the loading skeleton and the real cards) computed to
    a flat `16px` on all sides — the intended extra 2px of horizontal breathing room was silently
    dropped. Fixed to `!p-[16px_18px]`.
  - The "Recent failures" table's `card overflow-hidden p-0` computed to `16px` padding, not `0px` —
    the table was rendering inset from the card edges instead of flush, on the live Dashboard every
    user sees first. Fixed to `!p-0`.
  - Two `<td>` cells in that same table (`Error`, `When`) had `text-[var(--text-3)]`/
    `text-[var(--text-muted)]` silently losing to `.tbl td`'s own `color: var(--text-2)`. Fixed with `!`.
  - Two `card ... p-4` instances turned out to be harmlessly redundant (`p-4` = 16px = `.card`'s own
    default) rather than bugs — removed rather than kept as a no-op, same as the dead-weight cleanups
    in chunks 12.2/12.3/12.9/12.12.
  This closes out Phase 12 — all 14 chunks (12.0–12.13) are now complete; every `pages/`/`components/`
  file has been swept for both raw inline `style={{}}` and the `!important`-for-unlayered-CSS bug this
  phase surfaced partway through.
  Verified: `tsc --noEmit` and `eslint` clean (zero warnings), `npx vitest run` — 97/97 passing,
  `npm run build` succeeds. Live-verified via the same dev stack (Playwright, headless) against a real
  seeded pipeline with a real run and a real failure from earlier in this session: the 4 stat cards
  (correct `16px 18px` padding visible), the pipeline card with its mini run-history bars, and the
  Recent Failures table now rendering fully flush against the card border with correctly-colored error/
  timestamp text. Zero console/React errors.

---

# Phase 13 — Unified Registry & Plugin Architecture (2026-07-07)

*Replaces the four separate hardcoded if/elif dispatch points (steps, connections, email providers,
storage) with one generic registry primitive, then wires the existing plugin loader and frontend
through it. Framing note: this phase builds the capability-introspection **seam** (what's registered,
what's installed) — it deliberately does not add a tier/licensing/entitlement **gate** on top of it.*

## 13.1 Generic registry primitive

- [ ] **[ARCH-3] Generic `Registry` class** — Add `flowforge/registry.py`: `.register(key, cls,
  **metadata)`, `.get(key)`, `.list()`, `.metadata(key)`. One instance per category (steps,
  connections, email_providers). Storage and reports are **not** in scope for this phase — see the note
  at the end of 13.2 for why.
- [ ] **[ARCH-4] `IntegrationSpec` dataclass** — `key`, `display_name`, `description`, `requires` (pip
  extra name, for the "declared but dependency missing" case), `config_schema` (optional, for future
  generic frontend forms), and `tier: str | None = None` (unenforced, read by nothing yet). *Revised
  2026-07-08*: originally scoped as "no tier field — deliberately absent," on the theory that omitting
  it kept the seam honest. Reconsidered — the stated purpose of this whole phase is to prepare for a
  future Free/Paid split, so a registry that can't even *represent* a tier isn't a smaller seam, it's a
  missing one. Every category migrated in 13.2 would need a second pass to add it later. The field
  costs nothing today (nothing reads it) and removes that rework.

## 13.2 Migrate connections + email providers off if/elif

- [ ] **[ARCH-5] Registry-based connections factory** — Replace `connections/factory.py`'s if/elif
  chain with `@registry.connections.register("postgresql", ...)` decorators on each `BaseConnection`
  subclass. Keep the existing lazy-import-inside-function pattern (so `oracledb` isn't imported unless
  someone actually uses Oracle) — just move the lazy import inside the decorated registration function
  instead of inside the factory's if-branch.
- [ ] **[ARCH-6] Registry-based email providers factory** — Same treatment for
  `email_providers/factory.py`.
- [ ] **[TEST-1] Contract test** — A single parametrized test that walks every registered
  connection/provider and asserts it satisfies its ABC (catches "someone added a class but forgot an
  abstract method" automatically, going forward).

*Note on scope (added 2026-07-08):* `ARCH-3` originally listed `storage` and `reports` as registry
categories, but neither gets a migration task here, and they're not equivalent gaps. `report.py:36`
(`if fmt == 'excel': elif fmt == 'pdf': ...`) has the identical shape to the connections/providers
dispatch and could get the same treatment in a follow-up phase — it just isn't scheduled yet. `storage`
is structurally different: there's no shared dispatch function to replace at all today — `s3_upload.py`,
`azure_blob_upload.py`, and `drive_upload.py` each import their own storage module directly. Registering
storage backends would mean refactoring how upload steps *choose* a backend, not just decorating
existing classes — a bigger, separate design question. Left out of this phase rather than silently
scope-creeping it.

## 13.3 Extend the plugin loader beyond steps

- [ ] **[ARCH-7] Generalize `engine/loader.py`** — It currently only scans for `BaseStep` subclasses.
  Parametrize it to scan for any registered base class, so a plugin file can define a step, a
  connection, a storage backend, or a report format in the same `FLOWFORGE_PLUGIN_DIR`.
- [ ] **[ARCH-8] `importlib.metadata` entry-point support** — Alongside directory scanning, support
  `group="flowforge.plugins"` so a pip-installed package (not just a dropped-in file) can register
  itself. This is what makes a future plugin marketplace possible without having to build a private
  packaging system later.

## 13.4 Kill remaining hardcoded lists

- [ ] **[ARCH-9] `GET /api/registry/{category}` endpoint** — Replace frontend hardcoded
  step/connection/provider-type arrays with a single endpoint backed by the new registry (already done
  for step types via `GET /api/step-types` — extend the same idea to connections and providers,
  matching the pattern from the Phase 11 `StepEditor` refactor).
- [ ] **[ARCH-10] Generic JSON-config fallback for plugin connections/providers** — `StepEditor`
  already falls back to a raw JSON textarea for unrecognized step types; give `Connections.tsx` and the
  email provider UI the same fallback so 3rd-party plugin connections/providers work in the UI with
  zero frontend changes, same as plugin steps do today.

## 13.5 Capability introspection (the seam, not the gate)

- [ ] **[ARCH-11] `GET /api/registry` aggregate endpoint** — Returns every registered key across all
  categories plus two separate booleans: `installed` (whether its `requires` extra is actually
  present) and `entitled` (hardcoded `true` for now — no entitlement system exists yet). *Revised
  2026-07-08*: originally a single `available: bool`. Split because "installed" and "entitled" are
  different questions the moment a Free/Paid split exists (a paid connector can be installed but not
  licensed, or licensed but not installed) — shipping one merged field now means an API-shape break for
  every consumer of this endpoint later. Splitting costs nothing today since `entitled` is a stub.
  Purely informational for now (powers a future "what's installed" admin page) — but it's the exact
  shape an entitlement check will read from later. Building the seam, not the gate.
- [ ] **[DOC-1] Rewrite `docs/plugins.md`** — Currently steps-only; expand to document all four
  pluggable categories and the entry-point mechanism.
