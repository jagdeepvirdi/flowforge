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

- [x] **`SECRET_KEY`/`JWT_SECRET` have no startup validation and can silently be empty** *(2026-07-24)* —
  `flowforge/api/app.py:46-60` reads both via `os.environ.get(..., '')`; `JWT_SECRET` falls back to
  `SECRET_KEY`, and if both are unset the app boots fine and signs HS256 JWTs with an empty key,
  making every session token forgeable by anyone who knows the algorithm (same file). Fixed:
  `create_app()` now calls `_validate_secret()` on both (raises `RuntimeError`, not just a log) if
  either is unset or under 32 characters — the length floor alone rejects every realistic
  human-typed placeholder (`changeme`, `secret`, `password` are all under 32 chars) without an
  entropy heuristic, which would've flagged the test suite's own intentionally-simple dummy keys
  (`'a' * 64`). Also made `flowforge/crypto.py`'s existing 32-byte format check run eagerly at boot
  (`crypto._key()` called directly in `create_app()`) instead of only on first
  `encrypt()`/`decrypt()`. 4 new tests in `tests/test_app_coverage.py`; full suite (2099 tests) still
  green.
- [x] **Docker image runs as root** *(2026-07-24)* — `Dockerfile` now creates a non-root
  `flowforge` user/group (uid/gid 1000) and switches to it via `USER flowforge` after `output/` and
  `logs/` are created and `chown -R`'d. Verified: image builds, `whoami`/`id` report the non-root
  user, `output/` is writable, gunicorn boots cleanly with all 4 workers and `/api/health` responds
  `{"status":"ok"}` under the new user.
- [x] **Weak defaults in `docker-compose.yml` that a lazy deployer will never change** *(2026-07-24)* —
  `POSTGRES_PASSWORD` and `FLOWER_BASIC_AUTH` now use compose's `${VAR:?message}` required-variable
  syntax instead of `${VAR:-weak-default}`, so `docker compose up` refuses to start with a clear
  error if either is unset, rather than silently defaulting to `flowforge` / `admin:changeme`.
  Verified via `docker compose config` both failing (unset) and succeeding (set). `.env.example`
  comments updated to say REQUIRED. This repo's own local `.env` didn't have either set — confirms
  the gap was real, not hypothetical.
- [x] **`/dashboard/summary` runs an unbounded query, polled every 3-5s per open tab** *(2026-07-24)* —
  `flowforge/api/routes/runs.py`'s `dashboard_summary()` now ranks runs per-pipeline in SQL with a
  `ROW_NUMBER() OVER (PARTITION BY pipeline_id ORDER BY started_at DESC)` window function
  (`sqlalchemy.orm.aliased` on the ranked subquery) and filters `rn <= 14` in the database, instead
  of fetching every `PipelineRun` row for every accessible pipeline and truncating to 14/pipeline in
  Python. New test creates 20 runs for one pipeline and confirms exactly the 14 most recent come
  back, most-recent-first.
- [x] **`/pipelines` list endpoint has no pagination** *(2026-07-24)* — added the same `limit`
  (capped at 500, matching `/runs`) / `offset` pattern used elsewhere; still returns a bare JSON
  array (no response-shape change) so the frontend's existing `getPipelines()` call needed no
  changes. 3 new tests cover the cap, an explicit small limit, and offset skipping.
- [x] **Plugin loader has no runtime trust enforcement** *(2026-07-24)* — added
  `_world_or_group_writable()` (POSIX-only; Windows' `os.stat()` doesn't model real per-owner
  permissions so the check always returns `False` there rather than false-positiving on every file).
  `_load_directory_plugins()` now logs a loud `SECURITY:` warning if `FLOWFORGE_PLUGIN_DIR` itself is
  group/world-writable, and **refuses to load** (logs an error, skips) any individual `.py` file
  that is group/world-writable, rather than only documenting the admin-only trust boundary in a
  docstring. 7 new tests, including a Windows-specific regression test (an obviously-writable mode
  bit is still ignored on `os.name == 'nt'`) since the naive version of this check broke every
  plugin-loader test on this dev machine before being scoped to POSIX.

## High Priority (refactoring & scalability)

- [x] **Split `flowforge/db/models.py` into domain modules** *(2026-07-24)* — was 468 lines, 22
  unrelated models in one file. Now a package: `_shared.py` (the single `db = SQLAlchemy()`
  instance, `_uuid`/`_utcnow`, cross-domain constants), `audit.py`, `auth.py` (User, ProjectMember,
  TokenBlocklist, PasswordResetToken), `projects.py`, `connections.py` (DbConnection, SSHConnection),
  `email.py` (EmailProvider, EmailConfig, RecipientGroup), `reports.py`, `bulk_load.py`,
  `pipelines.py` (Pipeline, PipelineStep, PipelineVariable, PipelineDependency, StepDependency,
  PipelineRun, StepRun, WebhookToken), `settings.py`, all re-exported from `__init__.py` — every one
  of the 69 existing `from flowforge.db.models import X` call sites across the codebase needed zero
  changes. Safe because every `relationship(...)`/`ForeignKey(...)` in this codebase was already
  string-based (SQLAlchemy resolves those against its own mapper registry, not Python import order),
  so domain modules don't import each other and there's no new circular-import risk between them —
  they just all need to be imported once, which `__init__.py` does. Verified three ways: (1)
  `sqlalchemy.orm.configure_mappers()` resolves every relationship with no errors, (2) `alembic
  revision --autogenerate` against the migrated test DB shows zero *new* drift beyond pre-existing
  index-naming mismatches confirmed identical against the original single-file version via `git
  show`, (3) full test suite (2120 tests, including the migration-heavy `apply_migrations` fixture)
  passes unchanged.
- [x] **Introduce a service/repository layer between `flowforge/api/routes/*.py` and SQLAlchemy**
  *(2026-07-24, scoped to `pipelines.py` — the file this item named as the worst offender)* —
  added `flowforge/api/pipeline_service.py` (cron validation, create/update/clone/promote/import
  business logic, dependency-cycle detection, webhook token creation — all the multi-step
  DB-mutating logic that was previously inlined in route bodies) following the same flat-module
  convention already established by `project_access.py`/`validators.py` (no new package needed for
  one domain). Moved `_pipeline_dict`/`_webhook_token_dict` into `serializers.py` alongside the
  existing `run_dict`/`step_run_dict` — that file is specifically the home for pure model→dict
  serialization, and a new `pipeline_export_dict()` was added there too for the YAML export
  endpoint's doc-building, which was previously inlined in the route. `routes/pipelines.py` now
  only does Blueprint wiring, request parsing, `can_access_project` authz checks, and
  `jsonify(...)` responses — trivial single-statement `db.session.get()`/`delete()`/`commit()`
  calls that exist purely to produce a 404/403 before any business logic runs were left in routes
  deliberately, not moved. File went from 781 → 412 lines; no behavior change (same status codes,
  JSON shapes, validation order). Full test suite (2120 tests) passes unchanged; no other module
  imported the moved private helpers by path, so this was safe to do without touching call sites
  elsewhere. Remaining route files (`runs.py`, `reports.py`, etc.) are unaffected — out of scope
  for this pass, per the item's own framing.
- [x] **Resolve the live circular dependency between `flowforge/engine/dag.py` and
  `flowforge/engine/runner.py`** *(2026-07-24)* — `dag.py` imported `PipelineResult`,
  `_CONTEXT_META_KEYS`, `_get_retry_config`, `_run_step_with_retry`, `_write_step_run` from
  `runner.py` at module level, while `runner.py` could only import `dag.run_dag` lazily inside a
  function body to avoid the resulting cycle. Fixed by extracting those 5 symbols — the actual
  shared single-step-execution primitives both the wave engine and DAG engine build on — into a new
  `flowforge/engine/step_exec.py`, which neither `dag.py` nor `runner.py` needs to import from each
  other for anymore. Verified both `dag`-first and `runner`-first import order work identically
  (previously order-sensitive), both modules' `PipelineResult` are now the literal same class
  (`is` identity check), and every existing `patch('flowforge.engine.runner._write_step_run', ...)`
  -style test mock still works via the re-export in `__init__`. Full suite (2120 tests) unchanged.
  Note: the remaining ~65 lazy function-body imports in the package (`loader.py`, `bulk_load.py`,
  `scheduler.py`, etc.) are mostly legitimate — deferring the Flask/DB layer until actually needed
  for testability, not papering over other live cycles — this item was specifically about the one
  confirmed real circular dependency, not a sweep of every lazy import in the codebase.
- [x] **Fix the concurrency semaphore's multi-worker blind spot** *(2026-07-24)* —
  `flowforge/engine/concurrency.py` falls back to a per-process `threading.Semaphore(5)` without
  Redis, meaning N Gunicorn workers give you N×5 effective concurrent runs, not 5. Fixed: `create_app()`
  now logs a `CAPACITY:` warning at startup when `GUNICORN_WORKERS > 1` and `FLOWFORGE_REDIS_URL` is
  unset (3 new tests cover warn/no-warn cases). Separately, `_try_acquire_redis`'s fail-open behavior
  on Redis errors is deliberate and load-tested (`tests/test_concurrency_failure_injection.py`), so
  rather than flipping the default, added an opt-in `FLOWFORGE_CONCURRENCY_FAIL_CLOSED=true` env var
  for operators who'd rather deny new runs than risk extra DB load during a Redis outage (2 new tests).
- [x] **Add leader-election or a distributed lock to `flowforge/engine/scheduler.py`'s
  `BlockingScheduler`** *(2026-07-24)* — added `flowforge/engine/leader.py`: with
  `FLOWFORGE_REDIS_URL` set, `start_scheduler()` now routes `_scheduler.start()` through
  `leader.run_with_leadership()`, which blocks until this replica wins a Redis lock
  (`SET NX PX`, 30s TTL) and only then calls into the scheduler; a background thread renews the
  lock every 10s via a Lua script that checks token ownership before extending it. If renewal
  ever fails (Redis unreachable, or another replica's clock/timing won the lock instead), the
  process calls `os._exit(1)` immediately rather than risk two schedulers firing the same cron
  job — the process manager (Docker/systemd/k8s) is expected to restart it, at which point it
  re-enters the election. Without `FLOWFORGE_REDIS_URL`, election is skipped entirely (same
  convention as `concurrency.py`'s fallback) and a startup `WARNING` says not to run more than
  one replica — HA isn't possible without a shared coordination point. 14 new tests in
  `tests/test_leader_election.py` plus 2 in `tests/test_scheduler.py` covering the wiring; full
  suite (2134 tests) passes unchanged.
- [x] **Stream/chunk large data instead of full in-memory loads** *(2026-07-24, partial — scoped down,
  see below)* — added `BaseConnection.execute_query_with_columns_chunked()` (concrete default:
  falls back to the eager path, so every connection type keeps working) with real streaming
  overrides in `postgres.py` (named/server-side cursor — a regular cursor pulls the whole result to
  the client on `execute()` regardless of `fetchall()`, so only a named cursor actually avoids
  holding a multi-million-row result in memory) and `oracle.py` (iterating the cursor directly
  batches via `arraysize` without needing a special cursor type). `csv_report.py`'s `generate()` now
  accepts any iterable and writes row-by-row instead of requiring a materialized list; `report.py`'s
  CSV branch wires DB → CSV end-to-end through the new streaming path, keeping the connection open
  for the duration of the write instead of closing it right after an eager fetch. Found and fixed a
  real bug along the way: psycopg2 named cursors report `.description` as `None` until the *first
  fetch* — reading columns immediately after `execute()` (as the naive version of this fix did)
  silently returned an empty column list, caught by `tests/test_report_e2e.py`'s real-Postgres tests
  (a pure-mock test suite would not have caught this). 16 new tests across
  `test_postgres_unit.py`/`test_oracle.py`/`test_connection_base.py`/`test_report_generators.py`.
  **Explicitly out of scope for this pass** (each needs its own dedicated, carefully-tested effort,
  not a rushed inclusion here): Excel/PDF/JSON report formats still materialize `rows` fully —
  Excel in particular would need `openpyxl`'s `write_only=True` mode, which has real interaction
  with the already-shipped column-formatting feature (`docs/manual-testing-guide.md` §36) that needs
  careful verification, not a blind conversion. `bulk_load.py`/`data_load.py` still read entire
  source files into memory before chunking on the insert side — footer-row stripping in particular
  needs a bounded sliding-window buffer (not a naive one-pass stream) to preserve exact
  header/footer-trim behavior across 3 load paths (Python fallback, Postgres COPY, SQL*Loader) in
  an already-867-line file with heavy existing test coverage worth not destabilizing casually.
- [x] **Add connect timeouts to the connection-pool creation paths** *(2026-07-24)* — added
  `connect_timeout=5` to `postgres.py`'s `ThreadedConnectionPool` and `tcp_connect_timeout=5` to
  `oracle.py`'s `create_pool` and to the `test-raw` endpoint's `oracledb.connect()` call (the one
  branch that had no timeout at all, unlike every other `db_type` in that function). 3 new tests
  assert the kwarg is actually passed through.
- [x] **Extend rate limiting beyond the 3 current `@limiter.limit` sites** *(2026-07-24)* — added
  `@limiter.limit('20 per minute')` to all 4 `flowforge/api/routes/ai.py` endpoints (`data_profile`,
  `chart_config`, `ai_query`, `anomaly_narrative` — the cost-DoS vector via paid Claude/Gemini
  fallback) and to `reports.py`'s `preview_report` (arbitrary stored SQL execution). Matches the
  existing `pipelines.py` pattern exactly (`from flowforge.api.app import limiter`).
- [x] **Break up `flowforge/engine/runner.py`** *(2026-07-24)* — retry logic already lived in
  `step_exec.py` from the earlier dag.py/runner.py circular-dependency fix; this pass split the
  rest. New modules: `waves.py` (wave-building + wave execution — `_build_execution_waves`,
  `_run_sequential_step` [newly extracted from `run_pipeline`'s inline sequential-step branch,
  for symmetry with the already-factored-out `_run_parallel_wave`], `_run_parallel_wave`,
  `_expose_step_outputs`, `_build_vars_log`, `_handle_failed_step`), `run_records.py`
  (`_create_run_record`, `_finish_run_record`, `_get_last_success_ts`), `notifications.py`
  (`_fire_failure_webhook`, `_notify_devbrain`), `dependency_trigger.py`
  (`_trigger_downstream_pipelines`). `runner.py` now only holds `run_pipeline()` (158 lines) and
  imports everything else. No behavior change — pure mechanical extraction, same call order, same
  return values. `_write_step_run`/`_expose_step_outputs`/`_handle_failed_step` are re-exported
  (unused, `# noqa: F401`) from `runner.py` even though their call sites moved into `waves.py`,
  because existing tests patch/import them as `flowforge.engine.runner.<name>` — same convention
  already used for `step_exec.py`'s re-exports. `ruff check` clean; full suite (2134 tests) passes
  unchanged.
- [x] **Add a `frontend/src/hooks/` layer and break up the monolithic page components**
  *(2026-07-24)* — new `frontend/src/hooks/`: `useMfa`, `useRetentionSettings`,
  `useChangePassword` (state/query/mutation logic pulled out of `Settings.tsx`'s inline card
  components), `useReportConfigForm`, `useReportPreviewTools` (form + data-fetching vs.
  AI-tooling state pulled out of `ReportEdit.tsx`, split along the same seam the two hooks
  already had — a single shared `error`/`setError` passed from the form hook into the preview
  hook, matching the original single error banner). Every card that used to be a function
  declared inline in `Settings.tsx` now lives in its own file under
  `frontend/src/components/settings/` (`ChangePasswordCard`, `MfaCard`, `GoogleOAuthCard`,
  `Microsoft365Card`, `AiOllamaCard`, `RetentionCard`, `YamlCard`, `DocsCard`, plus
  `common.tsx` for the shared `StatusBadge`/`CodeBlock`/`InlineCode`); `ColumnFormattingCard`
  moved out of `ReportEdit.tsx` into `frontend/src/components/report/`. `Settings.tsx` went
  737 → 90 lines (now just the tab shell), `ReportEdit.tsx` went 675 → 370 (page layout +
  wiring, no state logic). No behavior change — pure mechanical extraction. Verified via `tsc
  --noEmit` (clean), `eslint` (0 errors, same pre-existing `watch()` warning pattern already
  present in `EmailEdit.tsx`), the full Vitest suite (172 tests, unchanged), a production
  `vite build`, and a manual Playwright pass against the real dev stack (login → all 5 Settings
  tabs → MFA card → admin Retention save → create/save a real report end-to-end → delete it) —
  zero console errors.
- [x] **Close the release-cadence gap** *(2026-07-24)* — `pyproject.toml` bumped `1.1.0` → `1.3.0`
  (also fixed `flowforge/__init__.py`'s `__version__`, separately stale at `0.1.0` — unused
  elsewhere in the app, but worth being accurate now that it's touched). **Not** tagged `v1.2.0`:
  `CHANGELOG.md` already has an unrelated, unused `## [1.2.0]` section (pre-launch "multi-user
  roles" content, folded into the `v1.0.0` tag, whose own `compare/v1.1.0...v1.2.0` link is the
  dangling one this item originally flagged) — reusing that label for today's real release would
  put two different `## [1.2.0]` sections in the file. Decided with the user: skip straight to
  `v1.3.0` rather than rewrite historical changelog content; the old `[1.2.0]` section and its
  dangling link are left as-is (a known, now-documented quirk, not a live gap). `CHANGELOG.md`'s
  `[Unreleased]` section converted to `## [1.3.0] — 2026-07-24`, with today's four refactors
  (service layer, leader election, runner.py split, frontend hooks layer) added under it alongside
  the already-documented DAG engine work. `release.yml`/`publish.yml` (SLSA provenance, PyPI OIDC)
  fired on push — user confirmed, tag pushed, both workflows green, package live on PyPI. This was
  also the first time these ~12 already-committed-but-never-pushed local commits actually ran
  through GitHub's CI (they'd only ever been tested on this dev machine, Windows) — that surfaced
  one real, pre-existing bug: `tests/test_plugin_loader.py`'s
  `test_world_or_group_writable_always_false_on_windows` built `Path('x')` *after* monkeypatching
  `os.name` to `'nt'`, which is silently a no-op on Windows (already `'nt'` natively) but on Linux
  CI made `pathlib.Path()` itself try to instantiate a real `WindowsPath` and raise
  `NotImplementedError` — which then also crashed pytest's own failure-reporting code (also calls
  `Path()`), aborting the whole session with a cascading `INTERNALERROR` instead of a normal test
  failure. Root-caused by reproducing the exact crash in a Linux Docker container mirroring CI's
  postgres/env setup (not guessable from the Windows-only local runs that had passed every time);
  fixed by building the `Path` before the monkeypatch. Two follow-up commits after the tag push
  (a `ruff` import-sort miss in the same file, then this real fix) before `master`'s CI went fully
  green (CI, CodeQL, Secrets Scan, OpenSSF Scorecard all passing on `7968521`, confirmed still
  green on `615b2d7` — the last commit of this session).
- [x] **Make `.github/workflows/secrets-scan.yml` a blocking gate** *(2026-07-24)* — removed
  `continue-on-error: true` from the TruffleHog step. Note: this is a one-line change I could verify
  parses as valid YAML but couldn't execute (no local GitHub Actions runner) — worth watching the
  next PR's checks to confirm nothing in this repo's history trips `--only-verified` now that it's
  blocking.

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

