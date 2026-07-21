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

- [x] Add `@xyflow/react` (react-flow's successor) + evaluate `dagre`/`elkjs` for auto-layout; spike a static read-only render of one pipeline's steps as nodes *(~0.5 day)* — **done 2026-07-09**: chose `dagre` (lighter, standard pairing with react-flow) over `elkjs`.
- [x] Data mapping layer: steps → nodes, `step_order`/`parallel_group` → layout (same-group steps placed in a column = one "wave") *(~0.5–1 day)* — **done 2026-07-09**: `frontend/src/lib/pipelineWaves.ts` is a faithful port of `_build_execution_waves`'s exact consecutive-run grouping semantics (unit-tested against the same cases as `tests/test_runner_extended.py`); `frontend/src/components/pipeline/canvas/layout.ts` wraps dagre (rankdir LR) to turn waves into columns.
- [x] Canvas interactions: drag to reorder (writes `step_order`), drag a node into/out of a group column (writes `parallel_group`), click a node to open the existing step form in a side panel *(~1–1.5 days)* — **done 2026-07-09**: `PipelineCanvas.tsx`'s `onNodeDragStop` + `resolveDrop.ts` (pure, unit-tested coordinate math) + `pipelineReorder.ts`'s `assignParallelGroup`; click opens `StepPanel.tsx`.
- [x] Add/delete/duplicate a step from the canvas (reuse the existing `STEP_FORMS` registry for the config modal) *(~0.5–1 day)* — **done 2026-07-09**: node hover actions + side panel footer; duplicate is new logic (`pipelineReorder.ts`'s `duplicateStep`, didn't exist before) and was also added to the list view (`StepEditor.tsx`) for consistency.
- [x] Toggle between canvas view and the current list view (both read/write the same data — least risky rollout) *(~0.5 day)* — **done 2026-07-09**: `PipelineEdit.tsx`, both views share the same local `steps` state array.
- [x] Dark/light theming, responsive behavior, empty-state, matching design tokens *(~0.5 day)* — **done 2026-07-09**: `--xy-*` var overrides in `index.css` mapped to existing design tokens; empty-state reuses the list view's `.ff-empty` treatment.
- [x] Tests: component tests for node mapping, Playwright E2E for drag-to-reorder/group, visual check across a few real pipelines *(~1 day)* — **done 2026-07-09**: unit tests for `computeWaves`/`layoutWaves`/`resolveDropTarget`/`pipelineReorder` + component tests for `PipelineCanvas`/`StepEditor` (139 tests total, all green), and `e2e/pipeline-canvas.spec.ts` (toggle/add/edit-persist/duplicate/delete) run live against a real stack (Docker Postgres on 5434 + Flask + Vite) — 5/5 passed, stable across repeated runs (an initial run failed 4/5 during Docker/backend/frontend cold-start resource contention, not a real bug — same suite passed cleanly once warmed up). Full existing E2E suite also re-run for regressions: 36 passed, 4 pre-existing unrelated failures found in `connections.spec.ts`/`pipelines.spec.ts`/`run-history.spec.ts` (stale selectors predating this work, e.g. `pipelines.spec.ts:41` looks for `input[name="name"]` but the field has never had a `name` attribute — not caused by this change). Visually verified a 4-step demo pipeline (`db_query` → parallel `report`+`email` group → `drive_upload`) renders the correct wave/column layout. Actual pointer-drag-to-reorder/drag-to-group is still not automated in CI (flaky against react-flow's real layout math under headless CI) — that logic is covered by the `resolveDropTarget`/`assignParallelGroup` unit tests instead.
- [x] Docs: close out this phase in `TASKS.md`, screenshot for README, brief mention in `getting-started.md` *(~0.25 day)* — **done 2026-07-09**: this phase's checkboxes updated; `docs/screenshots/pipeline-canvas.png` captured via Playwright against the same 4-step demo pipeline and embedded in `getting-started.md`. Not added to README — no existing screenshot-embed section references `docs/screenshots/*.png` there today (verified via grep) and the demo GIF/README hero screenshot is a separate, still-open Phase 10 item.

## 14.2 Option B — Arbitrary step-level DAG (Airflow-equivalent, separate/larger initiative)

*Everything in 14.1, plus a rewrite of the execution engine's core semantics. This touches the
highest-blast-radius code in the app — every pipeline run goes through it — so it needs its own
design pass and test plan, not a quick follow-on to 14.1. Estimated ~3–4 weeks, most of it in the
backend rewrite and its test coverage, not the canvas UI itself. **Scoped into 4 milestones
2026-07-21, executed one at a time with a review checkpoint between each rather than as one big
change** — see the decisions and per-milestone breakdown below.*

### Decisions locked in (confirmed with the user 2026-07-21, apply across all milestones)

1. **`on_error: stop` with branches** (M2): halts only the failed step's transitive descendants;
   unrelated/independent branches keep running to completion. (Rejected alternative: halting the
   entire pipeline on any stop-failure — simpler but wastes the DAG's parallelism.)
2. **Context visibility** (M2): `{{ steps.X.* }}` is populated only for X's transitive upstream
   ancestors, not "anything completed so far, DAG-wide." Enforces that the graph drawn is the graph
   that actually matters. (Rejected alternative: keep today's global-visibility model — fully
   backward-compatible with existing templates, but doesn't enforce the graph is meaningful and
   visibility could vary run-to-run if the topological sort order isn't unique.)
3. **Backward compatibility** (all milestones): a pipeline with **zero** `ff_step_dependencies` rows
   keeps running through today's exact wave-based engine, byte-for-byte unchanged. The new DAG engine
   only activates once a pipeline actually has real edges. `StepDependency.exists_for_pipeline(id)`
   (built in M1) is the single signal M2's dual-path engine selection branches on. (Rejected
   alternative: auto-migrate every pipeline onto the DAG engine, treating `step_order` as an implicit
   linear chain — one code path long-term, but changes the execution engine under every existing
   production pipeline the moment it ships.)

### Current system, as verified by direct code reading (context for all 4 milestones)

- `runner.py::_build_execution_waves`: linear scan over `step_order`-sorted steps; a step joins the
  current group only if its `parallel_group` matches AND it's contiguous — a differently-grouped or
  ungrouped step in between splits the group (`test_build_waves_parallel_group_none_breaks_group`).
  Sequential steps mutate a single shared `context` dict in place via `_expose_step_outputs`; parallel
  waves run on real `ThreadPoolExecutor` threads, each given a **shallow snapshot** of context taken
  before the wave starts (siblings can't see each other's output), merged back after `wait()`.
- `on_error='stop'` halts all *later* waves but lets the current wave/parallel-siblings finish;
  `'continue'` just logs and proceeds — either way `result.success` (pipeline-level) is set `False` on
  any failure, independent of `on_error` (a `continue`-only failure still marks the run failed).
- `PipelineStep` (table `ff_pipeline_steps`): `step_order` (unique per pipeline via
  `UniqueConstraint('pipeline_id','step_order')`), `parallel_group` (nullable string). Neither is
  touched by Milestone 1.
- `PipelineDependency` (table `ff_pipeline_dependencies`) is the existing **pipeline-to-pipeline**
  (not step-level) edge table — `id, upstream_id, downstream_id, created_at`,
  `UniqueConstraint('upstream_id','downstream_id')`, `CheckConstraint('upstream_id != downstream_id')`
  (blocks direct self-loop only). Cycle detection lives in `api/routes/pipelines.py::_has_path`
  (lines ~673-686) — a stack-based traversal (its own docstring calls it "BFS" but it's actually DFS,
  `.pop()` not `.popleft()`) issuing one DB query per hop against the `PipelineDependency` ORM model
  directly. **Verified not reusable as-is** for step-level cycles — tightly bound to that
  model/columns, and one-query-per-hop would be an N+1 problem if re-run on every canvas edge-drag in
  M3. The *pattern* (visited-set + frontier stack) is reusable; the implementation isn't.
- Migration convention, verified against `0023_pipeline_deps_parallel.py` (the direct precedent — it
  added `parallel_group` + `ff_pipeline_dependencies` in one migration) and confirmed
  `0031_email_body_format` is the current Alembic head: filename `NNNN_snake_case.py`,
  `revision`/`down_revision` as the full filename stem string, `op.*` helpers only,
  `postgresql.UUID(as_uuid=False)` + `server_default=sa.text('gen_random_uuid()')` for PKs,
  `server_default=sa.text('NOW()')` for timestamps, explicit `op.create_index` calls (not inline
  `index=True`), `downgrade()` exactly reverses `upgrade()`.
- `api/routes/pipelines.py`'s dependency routes (`get_dependencies`/`add_dependency`/
  `remove_dependency`, lines ~671-756) are the direct precedent for the new step-dependency routes —
  same validation shape (not-found → 404, self-reference → 400, cycle → 409, duplicate → 409),
  `@require_role(['admin', 'editor'])` on writes, `can_access_project` guard.
- `api/routes/steps.py` (134 lines) currently imports `require_auth` only (no `require_role` yet) —
  will need that import added in M1.
- Frontend canvas (`PipelineCanvas.tsx`) derives nodes/edges 100% fresh every render from
  `step_order`/`parallel_group` via `computeWaves`/`layoutWaves`/`buildWaveEdges` (`layout.ts`) — the
  latter draws synthetic cartesian wave-to-wave edges, not real dependency data. `StepNode.tsx`
  already renders decorative `<Handle>` components (no `id` prop, so one per side) but `onConnect` is
  never wired up. Zero persisted x/y or edges exist anywhere today. All Milestone 3 territory —
  untouched by Milestone 1.
- Flagged for M2 (not solved in M1): `engine/loader.py::load_pipeline` silently skips `enabled=False`
  steps — an edge could legally reference a disabled step's id. M1's schema doesn't prevent this; M2
  needs a policy (skip-and-satisfy vs. error) when it starts walking edges.

### Milestone 1 — Schema + migration (additive, zero runner changes) — next up

- [ ] **New model `StepDependency`** (`flowforge/db/models.py`, directly after `PipelineDependency`):
  table `ff_step_dependencies` — `id, pipeline_id (FK→ff_pipelines, CASCADE, indexed),
  upstream_step_id (FK→ff_pipeline_steps, CASCADE, indexed), downstream_step_id (FK→ff_pipeline_steps,
  CASCADE, indexed), created_at`. `UniqueConstraint('upstream_step_id','downstream_step_id',
  name='uq_step_dependency')`, `CheckConstraint('upstream_step_id != downstream_step_id',
  name='ck_no_self_step_dependency')`. `pipeline_id` is deliberately denormalized onto the edge row
  (not derived via join) so `exists_for_pipeline` is a single indexed lookup and the API route can
  enforce "both steps belong to this pipeline" by direct column comparison — cross-pipeline edges are
  blocked at the route layer, not a DB constraint (Postgres can't declaratively express "these two FK
  targets share a third column's value" without a trigger). Add a classmethod
  `exists_for_pipeline(pipeline_id) -> bool` — the single signal M2's dual-path engine selection
  branches on. On `PipelineStep`, add two relationships only (`upstream_step_deps`/
  `downstream_step_deps`, `cascade='all, delete-orphan'`) — no new columns, no `__table_args__`
  changes. `step_order`/`parallel_group` stay completely untouched and unmigrated.
- [ ] **Migration `0032_step_dependencies.py`** (`down_revision = '0031_email_body_format'`) — creates
  `ff_step_dependencies` + 3 indexes (`ix_step_dep_pipeline/upstream/downstream`), following
  `0023_pipeline_deps_parallel.py`'s exact style. No changes to `ff_pipeline_steps`. `downgrade()`
  drops the 3 indexes then the table.
- [ ] **Step-level cycle detection, enforced at write-time** — new `_creates_step_cycle(pipeline_id,
  new_upstream_id, new_downstream_id)` in `api/routes/steps.py` (NOT reusing `_has_path` — bound to
  the wrong model and one-query-per-hop): one query loads the whole per-pipeline edge set into an
  in-memory adjacency dict, then a visited-set/stack traversal checks whether the proposed edge would
  close a cycle. Safe to call on every request, including a future canvas keystroke in M3. Enforced now
  (not deferred to M2/M3) so the table is acyclic by construction before anything reads it.
- [ ] **New API routes** in `api/routes/steps.py` (reuse existing `bp`, no new blueprint; add
  `require_role` import + `StepDependency` import):
  - `GET /api/pipelines/<id>/step-dependencies` → flat `[{dep_id, upstream_step_id,
    downstream_step_id}]` list, 404/403 guarded same as existing routes.
  - `POST /api/pipelines/<id>/step-dependencies` (`@require_role(['admin','editor'])`) — validates
    both fields present (400), both step ids belong to this pipeline (404/400), self-reference (400),
    `_creates_step_cycle` (409), duplicate (409), then insert (201).
  - `DELETE /api/pipelines/<id>/step-dependencies/<dep_id>` (`@require_role(['admin','editor'])`) —
    scoped by pipeline match, 404 if not found.
- [ ] **Tests**: new `tests/test_step_dependencies_model.py` (valid edge, self-reference constraint,
  duplicate constraint, cascade on step delete, cascade on pipeline delete, `exists_for_pipeline`
  true/false). New API tests appended to `tests/test_pipelines_extended_coverage.py` alongside the
  existing pipeline-dependency tests (empty list, add+list+remove round-trip, self-reference → 400,
  missing ids → 400, step not found → 404, cross-pipeline rejected, cycle → 409 mirroring
  `test_cycle_detection_blocked`, duplicate → 409, remove-not-found → 404). **Regression test proving
  zero impact on the existing engine** (added to `tests/test_runner_extended.py`/
  `tests/test_loader_unit.py`): take the existing `test_build_waves_*` fixtures, additionally insert
  `StepDependency` rows for that same pipeline (edges that, if honored, would reorder execution), then
  assert `_build_execution_waves(...)`/`loader.load_pipeline(...)` produce byte-for-byte identical
  output to before the edges existed — the concrete proof of the backward-compatibility decision above.
- [ ] **Verification**: `alembic upgrade head` clean, `downgrade -1` then `upgrade head` again
  (reversibility); full backend suite green; manual round-trip (`POST` valid → 201, repeat → 409,
  reversed pair closing a cycle → 409, `GET` lists it, `DELETE` removes it).

### Milestone 2 — Runner rewrite: topological DAG execution engine (roadmap-level, own design pass)

Scope: `runner.py`, `loader.py`, likely a new `engine/dag.py` kept separate from the untouched wave
code path.

- [ ] Dual-path gate on `StepDependency.exists_for_pipeline` — `False` keeps the exact existing wave
  path; `True` builds the graph and runs the new scheduler.
- [ ] New scheduler: in-degree/ready-set model — dispatch any step whose upstream deps have all
  completed, as soon as they complete, rather than wave-synchronized `ThreadPoolExecutor` batches.
- [ ] Branch-scoped `on_error='stop'` — compute each step's transitive descendant set (same adjacency
  structure as cycle detection) so a stop-failure only short-circuits its descendants.
- [ ] Ancestors-only context — each step's context snapshot built from only its transitive-ancestor
  outputs, computed from the graph (a new construction helper, not a tweak of `_expose_step_outputs`).
- [ ] Retries unaffected in shape, just invoked per-node instead of per-wave.
- [ ] Stretch (not required to close M2): decide whether to leave Jinja's default `Undefined`
  (silently blank for an undeclared step reference) or add a DAG-build-time lint for it.
- [ ] Resolve the disabled-step-referenced-by-an-edge policy flagged above.

### Milestone 3 — Canvas: real edge-drawing wired to the M1 API (roadmap-level)

Scope: `PipelineCanvas.tsx`, `StepNode.tsx`, `layout.ts`, new API client functions.

- [ ] Wire `onConnect` on `<ReactFlow>` (absent today) → calls the M1 `POST step-dependencies`
  endpoint; 409 (cycle) surfaces as inline UX feedback, not a silent failure.
- [ ] Handle `id`s on `StepNode`'s `<Handle>` components if multiple distinct connection points per
  step are needed (explicit M3 scope call — single handle per side may be an acceptable v1).
- [ ] Fetch real edges from the M1 API; if any exist for the pipeline, use them exclusively and skip
  the synthetic `buildWaveEdges` cartesian edges — mirrors the backend's dual-path gate on the
  frontend.
- [ ] Decide what `onNodeDragStop`'s existing reorder logic (`resolveDropTarget`/`assignParallelGroup`)
  means once a pipeline is in DAG mode.
- [ ] Add drag/connect coverage to `PipelineCanvas.test.tsx` and `e2e/pipeline-canvas.spec.ts` — both
  currently have zero.

### Milestone 4 — Test matrix and regression preservation (roadmap-level)

- [ ] New: partial-branch failures (stop halts only descendants, sibling branch completes), concurrent
  execution of independent branches (real overlap, not just same-`parallel_group`), `{{ steps.* }}`
  resolution across non-linear branches (only ancestors visible, not siblings).
- [ ] Preserve unmodified: all `test_build_waves_*` and existing `on_error`/context tests — if any fail
  after M2 lands, that's a signal the dual-path gate leaked into the old path.
- [ ] Adapt via new tests (not edits): DAG-mode counterparts of the "stop halts everything" tests,
  asserting the new branch-scoped semantics instead.

---

---

# Phase 13 — Unified Registry & Plugin Architecture (2026-07-07)

*Replaces the four separate hardcoded if/elif dispatch points (steps, connections, email providers,
storage) with one generic registry primitive, then wires the existing plugin loader and frontend
through it. Framing note: this phase builds the capability-introspection **seam** (what's registered,
what's installed) — it deliberately does not add a tier/licensing/entitlement **gate** on top of it.*

## 13.1 Generic registry primitive

- [x] **[ARCH-3] Generic `Registry` class** — Add `flowforge/registry.py`: `.register(key, cls,
  **metadata)`, `.get(key)`, `.list()`, `.metadata(key)`. One instance per category (steps,
  connections, email_providers). Storage and reports are **not** in scope for this phase — see the note
  at the end of 13.2 for why. — **done 2026-07-21**: primitive only (`Registry` class, usable as a
  direct call or decorator, raises on duplicate key registration), unit-tested in
  `tests/test_registry.py` (14 tests). Deliberately not wired into `connections/factory.py`,
  `email_providers/factory.py`, or `engine/loader.py` yet — that's ARCH-5/6/7 below.
- [x] **[ARCH-4] `IntegrationSpec` dataclass** — `key`, `display_name`, `description`, `requires` (pip
  extra name, for the "declared but dependency missing" case), `config_schema` (optional, for future
  generic frontend forms), and `tier: str | None = None` (unenforced, read by nothing yet). *Revised
  2026-07-08*: originally scoped as "no tier field — deliberately absent," on the theory that omitting
  it kept the seam honest. Reconsidered — the stated purpose of this whole phase is to prepare for a
  future Free/Paid split, so a registry that can't even *represent* a tier isn't a smaller seam, it's a
  missing one. Every category migrated in 13.2 would need a second pass to add it later. The field
  costs nothing today (nothing reads it) and removes that rework. — **done 2026-07-21**: frozen
  dataclass added to `flowforge/registry.py` alongside `Registry`, plus a `Registry.register_spec()` /
  `.spec()` pair (mirrors `.register()`/`.metadata()` but takes/returns a structured `IntegrationSpec`
  instead of loose kwargs) so migrating categories in 13.2 have a typed path from day one. Unit-tested
  in `tests/test_registry.py` (8 new tests, 22 total).

## 13.2 Migrate connections + email providers off if/elif

- [x] **[ARCH-5] Registry-based connections factory** — Replace `connections/factory.py`'s if/elif
  chain with `@registry.connections.register("postgresql", ...)` decorators on each `BaseConnection`
  subclass. Keep the existing lazy-import-inside-function pattern (so `oracledb` isn't imported unless
  someone actually uses Oracle) — just move the lazy import inside the decorated registration function
  instead of inside the factory's if-branch. — **done 2026-07-21**: implemented as
  `connections_registry.register_spec(IntegrationSpec(...), (dotted_class_path, kwargs_fn))` per
  `db_type` rather than decorating already-imported classes directly — existing tests patch
  `sys.modules['flowforge.connections.mssql']` and `flowforge.connections.odbc.ODBCConnection`
  expecting the class to be resolved fresh on every `get_connection()` call (not bound at decoration
  time), so the dotted-path-string approach already used by `engine/loader.py`'s `_STEP_CLASSES` was
  the compatible option. `Registry`'s `_classes` value type widened from `type` to `Any` to reflect
  that a category can register anything, not just a class. All 8 db_types covered; all existing
  connection/factory tests pass unchanged (312 in the affected files, 2005 full suite).
- [x] **[ARCH-6] Registry-based email providers factory** — Same treatment for
  `email_providers/factory.py`. — **done 2026-07-21**: identical pattern, `providers_registry` with all
  6 provider types (gmail, microsoft365, smtp, sendgrid, ses, mailgun); `get_provider()`/
  `get_email_provider()` signatures unchanged.
- [x] **[TEST-1] Contract test** — A single parametrized test that walks every registered
  connection/provider and asserts it satisfies its ABC (catches "someone added a class but forgot an
  abstract method" automatically, going forward). — **done 2026-07-21**:
  `tests/test_registry_contract.py` — parametrized over both registries, asserts
  `issubclass(cls, Base...)` and `not cls.__abstractmethods__` for each of the 8 connection types and
  6 provider types (16 tests total, no live credentials needed since it only imports the class, never
  instantiates it).

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

- [x] **[ARCH-7] Generalize `engine/loader.py`** — It currently only scans for `BaseStep` subclasses.
  Parametrize it to scan for any registered base class, so a plugin file can define a step, a
  connection, a storage backend, or a report format in the same `FLOWFORGE_PLUGIN_DIR`. — **done
  2026-07-21**: added a `_PluginCategory` dataclass (`label`, `base_class`, `key_attr`, `contains`,
  `register`) and `_register_plugin_class()` that checks one class against every known category; wired
  up for the three categories that currently have a registration point — steps (`_STEP_CLASSES`,
  unchanged storage), connections (`connections_registry`), email providers (`providers_registry`).
  Storage/report formats aren't wired in since neither has a registry yet (see the 13.2 scope note).
  Plugin-registered connections/email providers store the class directly (not a dotted-path tuple like
  built-ins) and must define a `from_config(cls, cfg: dict)` classmethod — checked at construction time
  via `hasattr`, not enforced by the ABC, so a typo'd plugin still loads and registers but fails with a
  clear `ValueError` only when actually used. `_reset_plugin_state_for_tests()` extended to also drop
  plugin-added connections/providers (via new `BUILTIN_DB_TYPES`/`BUILTIN_PROVIDER_TYPES` frozensets
  and `Registry.unregister()`) without touching the 8/6 built-ins. `docs/plugins.md` updated to cover
  the new categories and the `from_config` contract (full four-category rewrite is still DOC-1).
  Existing plugin-step tests all pass unchanged; 14 new tests in
  `tests/test_plugin_loader_multi_category.py` cover plugin connections, plugin email providers, one
  file registering both a step and a connection, and reset behavior.
- [x] **[ARCH-8] `importlib.metadata` entry-point support** — Alongside directory scanning, support
  `group="flowforge.plugins"` so a pip-installed package (not just a dropped-in file) can register
  itself. This is what makes a future plugin marketplace possible without having to build a private
  packaging system later. — **done 2026-07-21**: `_load_entry_point_plugins()` enumerates
  `importlib.metadata.entry_points(group='flowforge.plugins')`, loads each entry point, and runs it
  through the same `_register_plugin_class()` used for directory scanning (so it can be a step,
  connection, or email provider too). Enumeration failure, a single entry point failing to load, and an
  entry point resolving to a non-class are all logged and skipped rather than raising. Both loading
  paths run from the same `_load_plugins()` call, guarded by the existing once-per-process flag. 6 new
  tests cover success, load failure, non-class result, enumeration failure, and directory+entry-point
  plugins coexisting.

## 13.4 Kill remaining hardcoded lists

- [x] **[ARCH-9] `GET /api/registry/{category}` endpoint** — Replace frontend hardcoded
  step/connection/provider-type arrays with a single endpoint backed by the new registry (already done
  for step types via `GET /api/step-types` — extend the same idea to connections and providers,
  matching the pattern from the Phase 11 `StepEditor` refactor). — **done 2026-07-21**: new
  `flowforge/api/routes/registry.py` blueprint, `GET /api/registry/<category>` for `steps`/
  `connections`/`email_providers` (steps included for symmetry/reuse by ARCH-11, though
  `GET /api/step-types` remains the endpoint the UI actually uses for steps). Each entry:
  `key, display_name, description, requires, tier, plugin, installed`. Found and fixed a real gap while
  building `installed`: `sendgrid`/`mailgun` providers only need `requests` at runtime but had no
  matching pip extra in `pyproject.toml` (their `requires='sendgrid'`/`'mailgun'` values referenced
  extras that didn't exist) — added both extras (`requests>=2.31` each) so the metadata is now accurate
  and `pip install flowforge[sendgrid]` actually works. 11 tests in `tests/test_registry_api.py`.
- [x] **[ARCH-10] Generic JSON-config fallback for plugin connections/providers** — `StepEditor`
  already falls back to a raw JSON textarea for unrecognized step types; give `Connections.tsx` and the
  email provider UI the same fallback so 3rd-party plugin connections/providers work in the UI with
  zero frontend changes, same as plugin steps do today. — **done 2026-07-21**:
  `components/connections/types.ts`'s `DbForm.db_type`/`MailForm.provider_type` widened from literal
  unions to `string` (plus a new `raw_config` field); `KNOWN_DB_TYPES`/`KNOWN_PROVIDER_TYPES` derived
  from the existing label maps mark which types keep their curated dedicated form. `Connections.tsx`
  fetches `/api/registry/connections` and `/api/registry/email_providers` (via new
  `getRegistryCategory()` in `lib/api.ts`) and appends any type not in the known set as an extra
  dropdown option; selecting one swaps the dedicated Fields component for a raw JSON textarea (mirrors
  `StepConfigForm`'s fallback). Chose to keep the curated built-in `<option>` labels hardcoded rather
  than drive them from the backend `display_name` too — some built-in frontend labels intentionally
  carry UX-only phrasing (e.g. "SMTP (Generic)", "AWS SES") that doesn't belong in a general API
  contract; only the previously-nonexistent plugin-type path needed fixing. Invalid JSON in the
  fallback textarea surfaces a form error at submit time rather than silently saving `{}`. 3 new tests
  in `Connections.test.tsx` (8 total, all passing) plus full frontend suite green (154 tests) and a
  clean `tsc --noEmit`.

## 13.5 Capability introspection (the seam, not the gate)

- [x] **[ARCH-11] `GET /api/registry` aggregate endpoint** — Returns every registered key across all
  categories plus two separate booleans: `installed` (whether its `requires` extra is actually
  present) and `entitled` (hardcoded `true` for now — no entitlement system exists yet). *Revised
  2026-07-08*: originally a single `available: bool`. Split because "installed" and "entitled" are
  different questions the moment a Free/Paid split exists (a paid connector can be installed but not
  licensed, or licensed but not installed) — shipping one merged field now means an API-shape break for
  every consumer of this endpoint later. Splitting costs nothing today since `entitled` is a stub.
  Purely informational for now (powers a future "what's installed" admin page) — but it's the exact
  shape an entitlement check will read from later. Building the seam, not the gate. — **done
  2026-07-21**: `GET /api/registry` in the same `registry.py` blueprint as ARCH-9, flattening all three
  categories into one list with a `category` field added per entry plus `entitled: true` unconditionally
  on every row. `installed` is computed by mapping each `requires` pip-extra name to the module actually
  probed via `importlib.util.find_spec` (extra name and importable module aren't always the same
  string, e.g. extra `oracle` → module `oracledb`) — verified against this dev venv's actual installed
  set (`oracledb`/`requests` present, `pymysql`/`pyodbc`/`snowflake.connector`/`boto3`/
  `google.cloud.bigquery` absent) to make sure the check reflects reality, not just mocked values. Steps
  report `installed: true` unconditionally since no per-step `requires` metadata exists yet (noted in
  code rather than fabricated). Covered by the same `tests/test_registry_api.py`.
- [x] **[DOC-1] Rewrite `docs/plugins.md`** — Currently steps-only; expand to document all four
  pluggable categories and the entry-point mechanism. *Partially addressed 2026-07-21 during ARCH-7/8*:
  the doc now covers all three categories that actually have plugin support (steps, connections, email
  providers) and the entry-point mechanism, but hasn't had the full structural rewrite/polish pass this
  item originally scoped (storage/report-format categories still don't exist to document, per the 13.2
  scope note). — **done 2026-07-21**: full restructure — "How it works" now leads with a
  category/base-class/key-attribute table instead of steps-only prose, each of the three categories
  (steps, connections, email providers) gets its own top-level section with contract + example, a new
  "Registry introspection" section documents `GET /api/registry`/`GET /api/registry/<category>`
  (ARCH-9/11), "Frontend" now describes the plugin fallback for all three categories (was steps-only —
  this line was actually wrong as of ARCH-10, since Connections.tsx now has the same fallback), and a
  "What's not pluggable yet" section replaces the old passing mention of storage/reports. Also fixed two
  now-stale cross-references: `docs/INDEX.md`'s one-line description (said "plugin step type" only) and
  two mentions in `README.md`. Added a manual-test checklist item (32d) in
  `docs/manual-testing-guide.md` for plugin connections/providers, matching the existing 32a-c coverage
  for plugin steps — that capability had shipped with zero manual-test-checklist coverage until now.
  "All four pluggable categories" in this item's own title is aspirational, not literal — storage/report
  formats still don't exist as pluggable categories (documented as such, not silently ignored).
