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
reference material (Phase 5, Phase 13, Phase 14, Known Risks) still needed
to act on them.*

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

*From a brutal, evidence-based architect/VC-style audit of the codebase as it actually is today (verified via code reading, not self-reported scores). Findings below survived direct verification against `flowforge/` source, not just prior review docs. The Critical subsection and most of High Priority / Nice-to-Have have since shipped — see [TASKS_ARCHIVE.md](TASKS_ARCHIVE.md) ("Session — 2026-07-02" and surrounding entries) for the full fix detail. Only the items below remain open.*

## High Priority (refactoring & scalability)

- [ ] Resolve the OpenSSF Scorecard Code-Review deadlock (0/10, structurally stuck for a solo maintainer since GitHub blocks self-approval) — recruit a co-maintainer/approver or explicitly drop the ≥8.0 target instead of leaving it perpetually "in progress." **Not resolved by disabling `enforce_admins` (2026-07-06)** — that change only unblocks the solo-maintainer merge workflow (see Phase 10 note above); admin-override merges still don't count as reviewed, so the score is unaffected.
- [ ] Get at least one real external user or design partner before adding more enterprise-checkbox features (SSO/SAML/MFA/GDPR tooling currently serves zero non-author users).

## Nice-to-Have (polish & optimization)

- [ ] Add a one-click deploy option (Railway/Render/Fly.io) to lower adoption friction beyond `docker compose up`.

---

---

# Phase 14 — Visual Pipeline Canvas *(scoped 2026-07-08)*

*Promised in `ROADMAP.md` v3.0 goals, silently absent from the actual v3.0 backlog delivered (see
`TASKS_ARCHIVE.md`'s "V3.0 Backlog complete" session — everything else in that list shipped, this
didn't), and flagged in this project's own market-comparison doc as the #1 competitive gap vs.
Airflow/n8n/Dagster.*

**Current state**: `PipelineEdit.tsx` is a linear list of step cards (drag-to-reorder within the
list, one type-specific form per step). Non-linear structure already exists in the data model but
has no graphical representation: `parallel_group` (string field on `ff_pipeline_steps`, migration
0023) groups steps that run concurrently, and `ff_pipeline_dependencies` (upstream_id/downstream_id,
with BFS cycle detection) links whole *pipelines* together — there is no step-to-step dependency
edge within a single pipeline today. Both existing mechanisms are set via a text input /
dropdown-and-pill-list UI, not by drawing a graph. No node/graph canvas library is in
`frontend/package.json` today (no `react-flow`/`@xyflow/react`/`dagre`/`elkjs`).

**Scope decision needed before starting**: does "visual DAG canvas" mean visualizing/editing the
*existing* sequential + parallel-wave execution model (Option A — frontend-only), or does it mean
adding *true* arbitrary step-to-step dependency edges like Airflow/Dagster (Option B — requires
rewriting the pipeline execution engine)? These are very different projects; Option A is recommended
as the v1 deliverable since it closes the visible competitive gap without touching the
highest-blast-radius code in the app (the runner used by every pipeline execution). Option B should
only be scoped as its own follow-up phase if arbitrary per-step branching is actually required.

## 14.1 Option A — Visualize + edit the existing model (recommended v1)

*No backend/schema changes — steps stay sequential + wave-grouped, just represented and edited as a
graph instead of a list. Estimated ~5–7 focused days at this project's demonstrated pace (for
comparison, the 14-chunk Tailwind migration took ~3 days, but that was mechanical conversion —
interaction-design work like drag-and-drop has more iteration and edge-case testing per line of
code).*

- [ ] Add `@xyflow/react` (react-flow's successor) + evaluate `dagre`/`elkjs` for auto-layout; spike a static read-only render of one pipeline's steps as nodes *(~0.5 day)*
- [ ] Data mapping layer: steps → nodes, `step_order`/`parallel_group` → layout (same-group steps placed in a column = one "wave") *(~0.5–1 day)*
- [ ] Canvas interactions: drag to reorder (writes `step_order`), drag a node into/out of a group column (writes `parallel_group`), click a node to open the existing step form in a side panel *(~1–1.5 days)*
- [ ] Add/delete/duplicate a step from the canvas (reuse the existing `STEP_FORMS` registry for the config modal) *(~0.5–1 day)*
- [ ] Toggle between canvas view and the current list view (both read/write the same data — least risky rollout) *(~0.5 day)*
- [ ] Dark/light theming, responsive behavior, empty-state, matching design tokens *(~0.5 day)*
- [ ] Tests: component tests for node mapping, Playwright E2E for drag-to-reorder/group, visual check across a few real pipelines *(~1 day)*
- [ ] Docs: close out this phase in `TASKS.md`, screenshot for README, brief mention in `getting-started.md` *(~0.25 day)*

## 14.2 Option B — Arbitrary step-level DAG (Airflow-equivalent, separate/larger initiative)

*Everything in 14.1, plus a rewrite of the execution engine's core semantics. This touches the
highest-blast-radius code in the app — every pipeline run goes through it — so it needs its own
design pass and test plan, not a quick follow-on to 14.1. Estimated ~3–4 weeks, most of it in the
backend rewrite and its test coverage, not the canvas UI itself.*

- [ ] New table/columns for step-to-step dependency edges + Alembic migration
- [ ] Rewrite `runner.py`'s execution model from linear-waves to topological-sort-based DAG execution — redefine what `on_error: stop` means when there are multiple branches, handle fan-in/fan-out and diamond dependencies
- [ ] Cycle detection at the step level (today's BFS cycle check only covers pipeline-to-pipeline dependencies, not steps within one pipeline)
- [ ] Canvas: real edge-drawing (drag from one node's output handle to another's input) that persists actual dependency data, with inline cycle-rejection UX
- [ ] Test matrix: partial-branch failures, concurrent branch execution, `{{ steps.* }}` variable resolution across non-linear branches

---

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
