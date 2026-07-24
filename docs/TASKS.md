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
ordered by priority. Completed work — score tables, dates, full
implementation detail — has been moved to
[TASKS_ARCHIVE.md](TASKS_ARCHIVE.md) rather than kept under the original
Phase headings, so this file now only contains open items plus the
reference material (Phase 5, Known Risks) still needed to act on them.
Phase 13 and Phase 14 were fully completed and archived on 2026-07-22 —
see TASKS_ARCHIVE.md's "Session — 2026-07-21" and "Session — 2026-07-22"
entries.*

## High priority

*Release-blocking (Release Definition lists "GTM done" under v1.0), quick wins, or ongoing practice that protects a score already earned.*

- [ ] Going forward: never push directly to `master`; always open a PR. Self-approval is blocked by GitHub for PRs you author, so get approval from a collaborator/second account for those, or prefer bot-authored PRs (e.g. Dependabot) *(Scorecard — Code-Review)* — **partially addressed 2026-07-06**: `enforce_admins` disabled on `master`'s branch protection so admin-override merges (`gh pr merge --admin`) are possible without a collaborator (PRs #94, #95 merged this way). This unblocks the solo-maintainer workflow but does **not** raise the Scorecard Code-Review score — admin-override merges still count as unreviewed, so the score stays near 0 until a real second reviewer is in the loop. See Phase 11's Code-Review deadlock item below.
- [ ] Re-run scorecard to confirm Pinned-Dependencies improved after the hash-pinning already done *(Scorecard — Pinned-Dependencies)*
- [ ] Record a 60–90s demo GIF/MP4 (dashboard → create pipeline with report+email step → run it → Run History) and add to the README — blocks every other GTM item below *(Go-To-Market 5.1)*
- [ ] Capture a high-quality Dashboard screenshot for the README hero / LinkedIn Featured section *(Go-To-Market 5.1)*

## Security — SonarCloud residual finding needs manual resolution *(found 2026-07-06)*

- [ ] **Manually resolve the residual SonarCloud finding** (`pythonsecurity:S5496`, issue key `AZ82Oyzt-6VzRaR01a4L`, `flowforge/engine/context.py`) as Won't Fix / False Positive in the SonarCloud UI — the rule flags the `render()` call-site pattern itself (Jinja2 template from user-controlled input) regardless of the mitigations already shipped (see archive), and will keep failing `master`'s Quality Gate until either manually resolved or it ages out of the New Code period on its own. Justification: `_jinja` is already a `SandboxedEnvironment` (blocks RCE-class gadgets), the blocklist/pattern now covers known and future credential names, and rendered values are no longer reflected — this is the same `{{ current_date }}`-style templating used intentionally everywhere else in the app, not a coding mistake in this one spot. Requires SonarCloud login (not available to Claude).
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
- [ ] Reddit: post in r/selfhosted, r/Python, r/opensource, and cross-post to r/dataengineering *(Go-To-Market 5.3)* — **partially done 2026-07-08**: posted to r/Python and r/selfhosted; r/opensource and the r/dataengineering cross-post still pending.
- [ ] Submit PRs to awesome-selfhosted ("Automation") and awesome-python ("Task Queues"/"Data Pipeline") *(Go-To-Market 5.4)*
- [ ] LinkedIn: write the launch post, add FlowForge to your Featured section, tag `#OpenSource #Python #LocalAI #DataEngineering #Productivity` *(Go-To-Market 5.5)* — **launch post already published 2026-07-08**; unconfirmed whether it's pinned to the Featured section or carries the suggested hashtags.

## Low priority

*Passive/automatic, deferred until a precondition exists, or explicitly optional.*

- [ ] Ensure at least 1 commit/week until the repo passes 90 days old (~2026-07) — Maintained check auto-resolves either way, no other fix exists *(Scorecard — Maintained)*
- [ ] Update screenshots showing old (pre-multi-user) UI *(deferred — no screenshots exist in docs yet, so nothing to do until some are added)*
- [ ] Code Climate maintainability badge — set up, add to README badge row if grade is A or B *(explicitly optional)*
- [ ] Decide whether to leave Jinja's default `Undefined` (silently blank for an undeclared `{{ steps.X.* }}` reference in DAG-mode pipelines) or add a DAG-build-time lint for it *(Phase 14.2 Milestone 2 stretch item, left open when M2 shipped — genuinely optional, not required by anything else)*

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

---

## Known Risks & Mitigations

| Risk | Mitigation |
|---|---|
| ~~cx_Oracle requires Oracle Instant Client~~ | ✅ Migrated to `python-oracledb` (thin mode, pure Python) |
| M365 requires Azure AD app registration | Step-by-step guide in `docs/microsoft365-oauth2-setup.md`; `flowforge setup microsoft365` wizard |
| Gmail OAuth2 token expiry | Refresh token handling; re-auth wizard in Settings |
| Drive folder ID opaque to users | Folder picker in frontend fetches Drive tree via API |
| Smart attachment: Drive upload fails after report generated | Fallback: attach directly if Drive upload fails, log warning |
| Large report query times out in Preview | Preview uses `LIMIT 20` wrapper around user query |
| Oracle LOB columns break row serialization | OracleConnection reads LOB values explicitly before cursor close |
| SonarCloud flags security hotspots | Review each hotspot; most will be acknowledged false positives with justification comments |

---

---

# Phase 11 — External Review Hit-List (2026-07-01)

*From a brutal, evidence-based architect/VC-style audit of the codebase as it actually is today (verified via code reading, not self-reported scores). Findings below survived direct verification against `flowforge/` source, not just prior review docs. The Critical subsection and most of High Priority / Nice-to-Have have since shipped — see [TASKS_ARCHIVE.md](TASKS_ARCHIVE.md) ("Session — 2026-07-02" and surrounding entries) for the full fix detail. Only the items below remain open.*

## High Priority (refactoring & scalability)

- [ ] Resolve the OpenSSF Scorecard Code-Review deadlock (0/10, structurally stuck for a solo maintainer since GitHub blocks self-approval) — recruit a co-maintainer/approver or explicitly drop the ≥8.0 target instead of leaving it perpetually "in progress." **Not resolved by disabling `enforce_admins` (2026-07-06)** — that change only unblocks the solo-maintainer merge workflow (see Phase 10 note above); admin-override merges still don't count as reviewed, so the score is unaffected.
- [ ] Get at least one real external user or design partner before adding more enterprise-checkbox features (SSO/SAML/MFA/GDPR tooling currently serves zero non-author users).

## Nice-to-Have (polish & optimization)

- [ ] Add a one-click deploy option (Railway/Render/Fly.io) to lower adoption friction beyond `docker compose up`.

---

---

# Phase 12 — Known Product Limitations (2026-07-24)

*Surfaced while auditing `docs/USE_CASE.md`'s "Limitations to Be Honest About" table for staleness.
Most of these are deliberate design decisions, not bugs — listed here for visibility and to keep
`docs/USE_CASE.md` and this file honest about the same set of constraints, not as a commitment to
build any of them out.*

## Genuinely open (candidate future work)

- [ ] No conditional/branching step execution — can't gate a step on a prior step's output (e.g.
  "only send email if row count > 0") beyond DAG failure propagation (`on_error: stop`/`continue`).
  Current workaround: always run the step, filter in the query. Unlike the items below, this one
  isn't an intentional non-goal — just not built yet.

## Accepted design tradeoffs (not planned)

- No true multi-tenant isolation beyond project-level workspace scoping (`ff_project_members`) —
  by design; see [`docs/threat-model.md`](threat-model.md#out-of-scope)
- Self-hosted only, no managed/cloud SaaS offering — explicit non-goal, see `CLAUDE.md` Non-Goals
- No Airflow DAG import — explicit non-goal, see `CLAUDE.md` Non-Goals
- FlowForge does not terminate TLS itself — deploy behind Nginx/ALB by design, see
  [`docs/deployment.md`](deployment.md)
- PDF reports require the optional `weasyprint` extra (`pip install flowforge[pdf]`) rather than
  shipping in the default install — keeps the base install light for the Excel/CSV/JSON-only case

## Already tracked elsewhere (not duplicated here)

- Supply-chain security posture (OpenSSF Scorecard 6.5/10 target 8.0, no OSS-Fuzz registration, no
  cosign-signed releases) — see "Medium priority" above and `ROADMAP.md`'s "In progress" / "Not yet
  built" sections

---

---

# Phase 13 — Architect/VC Audit Hit-List (2026-07-24)

*From a brutal, evidence-based architecture/security/performance/market-readiness audit run against
the actual code (not docs) across four independent passes. Every item below cites the file/behavior
that was actually verified — this is not a generic checklist. Scores from the same audit: Architecture
6/10, Code Quality 7/10, Security 3/10, Test Coverage 6/10, Scalability 5/10, DevOps/CI 8/10, Moat 3/10,
Documentation 8/10 — overall 6/10. The one showstopper is the JWT/secret-key item below; everything
else is real but not on fire.*

## Critical (fix immediately / showstoppers)

- [ ] **`SECRET_KEY`/`JWT_SECRET` have no startup validation and can silently be empty** —
  `flowforge/api/app.py:46-60` reads both via `os.environ.get(..., '')`; `JWT_SECRET` falls back to
  `SECRET_KEY`, and if both are unset the app boots fine and signs HS256 JWTs with an empty key,
  making every session token forgeable by anyone who knows the algorithm (same file). Fix: make
  `create_app()` refuse to start (raise, not just log) if either secret is unset, empty, below a
  minimum length (32 bytes), or matches an obvious placeholder (`changeme`, `secret`, `password`,
  etc.). `flowforge/crypto.py:14-25` already has the length check for the encryption key — it just
  needs to run eagerly at boot instead of lazily on first `encrypt()`/`decrypt()` call.
- [ ] **Docker image runs as root** — `Dockerfile` has no `USER` directive. Add a non-root user and
  `USER` line; verify file permissions on `output/`, `logs/`, etc. still work under it.
- [ ] **Weak defaults in `docker-compose.yml` that a lazy deployer will never change** —
  `POSTGRES_PASSWORD` defaults to `flowforge` if unset (line ~10); `FLOWER_BASIC_AUTH` defaults to
  `admin:changeme` (line ~99) on a port exposed to the host. Fail loudly (compose `${VAR:?error}`
  syntax) instead of silently defaulting for both.
- [ ] **`/dashboard/summary` runs an unbounded query, polled every 3-5s per open tab** —
  `flowforge/api/routes/runs.py:64-99` queries *every* `PipelineRun` row for every accessible
  pipeline with no `LIMIT`, then truncates to 14/pipeline in Python. On any deployment with real run
  history (no retention configured, or just months of use) this becomes a full-table scan pulled
  into memory every few seconds per open dashboard tab. Push the per-pipeline-14-rows truncation
  into the SQL query (window function or per-pipeline subquery + `LIMIT`), not Python.
- [ ] **`/pipelines` list endpoint has no pagination** — `flowforge/api/routes/pipelines.py:161-170`
  returns every pipeline in a project unbounded, unlike `/runs` and `/audit-logs` which both
  paginate correctly. Add the same `limit`/`offset` pattern.
- [ ] **Plugin loader has no runtime trust enforcement** — `flowforge/engine/loader.py:126-160`
  `exec_module`s any `.py` file in `FLOWFORGE_PLUGIN_DIR` with full process privileges; the
  admin-only trust boundary is documented only in a docstring, not enforced in code. At minimum,
  check the directory isn't world/group-writable before loading from it, and log loudly if it is.

## High Priority (refactoring & scalability)

- [ ] Split `flowforge/db/models.py` (468 lines, 23 unrelated models — auth, pipelines, audit,
  bulk-load, SSH all in one file) into domain modules (`models/auth.py`, `models/pipelines.py`,
  `models/audit.py`, etc.) re-exported from a package `__init__.py` so imports elsewhere don't churn.
- [ ] Introduce a service/repository layer between `flowforge/api/routes/*.py` and SQLAlchemy —
  there is currently no `services/` directory anywhere; routes build queries inline and mix HTTP
  concerns with business logic (`pipelines.py` at 774 lines is the worst offender: routing,
  `_validate_cron`, `_pipeline_dict` serialization, and `_has_path` cycle detection all in one file).
- [ ] Resolve the live circular dependency between `flowforge/engine/dag.py` and
  `flowforge/engine/runner.py` at the module level instead of papering over it with lazy
  function-body imports (66 counted across the package via `grep -rn "^    from flowforge"`,
  concentrated exactly where you'd expect a layering problem: `runner.py:240,270,284`,
  `loader.py`, `bulk_load.py`, `scheduler.py`).
- [ ] Fix the concurrency semaphore's multi-worker blind spot — `flowforge/engine/concurrency.py`
  falls back to a per-process `threading.Semaphore(5)` without Redis, meaning N Gunicorn workers
  give you N×5 effective concurrent runs, not 5. The shipped `docker-compose.yml` sets
  `FLOWFORGE_REDIS_URL` by default so this only bites bare-metal/no-Redis deployments — but it
  should at least log a loud startup warning when running multi-worker without Redis configured.
  Separately, reconsider `_try_acquire_redis`'s fail-open behavior on Redis errors
  (`concurrency.py:129-148`) — failing open removes the concurrency cap entirely during exactly the
  kind of infra hiccup that also stresses the DB.
- [ ] Add leader-election or a distributed lock to `flowforge/engine/scheduler.py`'s
  `BlockingScheduler` — scaling the `scheduler` service past 1 replica (or running multiple app
  instances behind a load balancer without isolating the scheduler) causes every replica to
  independently fire and execute the same cron job, with no guard beyond the concurrency ceiling.
- [ ] Stream/chunk large data instead of full in-memory loads: `postgres.py`/`oracle.py`'s
  `execute_query` methods use `cur.fetchall()` with no server-side cursor despite `arraysize=1000`
  being set (arraysize only tunes internal batching, not streaming to the caller);
  `reports/excel_report.py` and `csv_report.py` fully materialize `rows: list[tuple]` before
  writing; `bulk_load.py`/`data_load.py` load entire source files into memory (`list(csv.reader())`,
  `readlines()`) before any chunking — only the INSERT side is chunked. A multi-million-row query or
  multi-GB CSV will OOM a worker well before any user-count concern.
- [ ] Add connect timeouts to the connection-pool creation paths in `flowforge/connections/postgres.py`
  and `oracle.py` — testing or opening a connection against a dead/blackholed host currently hangs
  for the OS-level TCP timeout (minutes), not the 5s timeout that the ad-hoc `test-raw` path already
  sets correctly. Oracle's `test-raw` branch (`connections.py:148-152`) is missing a timeout param
  entirely.
- [ ] Extend rate limiting beyond the 3 current `@limiter.limit` sites (login, `trigger_run`,
  webhook trigger). `flowforge/api/routes/ai.py`'s four endpoints (`data_profile`, `chart_config`,
  `ai_query`, `anomaly_narrative`) are `@require_auth`-only and fall back to paid
  Claude/Gemini calls when Ollama is unreachable — a cost-DoS vector for any authenticated viewer.
  `reports.py`'s `preview_report` (runs arbitrary stored SQL, string-concatenated `LIMIT 20`, no
  query timeout) is equally unlimited.
- [ ] Break up `flowforge/engine/runner.py` (586 lines: orchestration, retry logic, variable
  exposure, wave-building, webhook firing, and the `_notify_devbrain` external integration all in
  one module) into focused modules.
- [ ] Add a `frontend/src/hooks/` layer (currently doesn't exist) and break up the monolithic page
  components — `Settings.tsx` (737 lines, 25 `useState`/`useEffect`/`useQuery`/`fetch` call sites)
  and `ReportEdit.tsx` (675 lines, 21) mix data-fetching, form state, and rendering inline.
- [ ] Close the release-cadence gap — only 2 tags exist (`v1.0.0`, `v1.1.0`), `pyproject.toml` is
  still pinned at `1.1.0` while `CHANGELOG.md`'s `[Unreleased]` section already documents the entire
  shipped DAG engine (dated 2026-07-22) plus ~7 weeks of other work, and there's a dangling
  `[1.2.0]: ...compare/v1.1.0...v1.2.0` changelog link with no corresponding tag. Cut a real
  `v1.2.0` release; the `release.yml`/`publish.yml` tooling is already correctly built (SLSA
  provenance, PyPI OIDC) — it's just not being used.
- [ ] Make `.github/workflows/secrets-scan.yml` a blocking gate — it currently runs with
  `continue-on-error: true`, so a real secret leak wouldn't actually stop a merge; right now it's
  advisory, not a gate.

## Nice-to-Have (polish & optimization)

- [ ] Add true unit tests with mocking for core business logic (`engine/runner.py`, `engine/dag.py`,
  `engine/context.py`) alongside the existing suite — every test file checked (`test_pipelines.py`,
  `test_runs.py`, `test_runs_api.py`, etc.) is 100% integration-style against a real Postgres with
  zero `@patch`/`MagicMock` usage; safe for refactors but slow to iterate on and can't isolate
  business-logic correctness from the DB/HTTP layer.
- [ ] Add production error-tracking (Sentry or equivalent) — logging itself is legitimate (113
  `logging`/`getLogger` call sites, not print-statement soup), but there's zero error-tracking SDK
  anywhere, so production debugging is log-files-only.
- [ ] Add a dependency/license audit tool to CI (e.g. `pip-licenses`) plus a `NOTICE` file — the
  current MIT-compatibility check (no GPL-family packages found) was a manual one-time grep, not an
  enforced, repeatable gate. Do this before any commercial relicensing conversation.
- [ ] Build genuine Airflow/cron migration tooling — zero evidence this exists today beyond
  FlowForge's own YAML export/import; this is the most plausible real differentiator given the
  existing "Oracle advantage" / migration-bridge positioning in `docs/USE_CASE.md`, rather than more
  enterprise-checkbox features.
- [ ] Evaluate a managed/hosted tier reusing the existing `docker-compose.yml` service topology —
  low engineering lift given the multi-service (db/redis/app/scheduler/worker) shape already exists;
  this is the more realistic commercial moat than the core engine itself, which is honestly
  replicable in a few weeks by a competent team (topological DAG + Jinja2 templating + integration
  adapters — no proprietary technology).
- [ ] Add a plugin marketplace/discovery layer on top of the existing plugin system (`docs/plugins.md`)
  — the load mechanism exists, there's no registry/discovery UX around it.
- [ ] Close the gap between "no YAML required" marketing and actual first-run friction — a bare
  dashboard is genuinely one `docker compose up` away, but a real first pipeline with email requires
  5+ manual steps across Google Cloud Console or Azure AD (OAuth app registration, consent screens,
  client secrets) before the "no-code" promise is actually true end-to-end.

