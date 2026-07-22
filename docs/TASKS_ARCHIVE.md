# TASKS_ARCHIVE.md — FlowForge
*Completed tasks moved here from TASKS.md. Ordered newest-first.*

---

## Session — 2026-07-22 (Phase 14 — Visual Pipeline Canvas complete: Option A canvas + Option B step-level DAG rewrite) 🟢 *(COMPLETE)*

### Phase 14 — Visual Pipeline Canvas *(scoped 2026-07-08)* — Option A + Option B complete

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

#### 14.1 Option A — Visualize + edit the existing model (recommended v1)

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

#### 14.2 Option B — Arbitrary step-level DAG (Airflow-equivalent, separate/larger initiative)

*Everything in 14.1, plus a rewrite of the execution engine's core semantics. This touches the
highest-blast-radius code in the app — every pipeline run goes through it — so it needs its own
design pass and test plan, not a quick follow-on to 14.1. Estimated ~3–4 weeks, most of it in the
backend rewrite and its test coverage, not the canvas UI itself. **Scoped into 4 milestones
2026-07-21, executed one at a time with a review checkpoint between each rather than as one big
change** — see the decisions and per-milestone breakdown below.*

##### Decisions locked in (confirmed with the user 2026-07-21, apply across all milestones)

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

##### Current system, as verified by direct code reading (context for all 4 milestones)

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

##### Milestone 1 — Schema + migration (additive, zero runner changes) — done 2026-07-22

- [x] **New model `StepDependency`** (`flowforge/db/models.py`, directly after `PipelineDependency`):
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
  changes. `step_order`/`parallel_group` stay completely untouched and unmigrated. — **done
  2026-07-22**: implemented exactly as scoped in `flowforge/db/models.py`.
- [x] **Migration `0032_step_dependencies.py`** (`down_revision = '0031_email_body_format'`) — creates
  `ff_step_dependencies` + 3 indexes (`ix_step_dep_pipeline/upstream/downstream`), following
  `0023_pipeline_deps_parallel.py`'s exact style. No changes to `ff_pipeline_steps`. `downgrade()`
  drops the 3 indexes then the table. — **done 2026-07-22**.
- [x] **Step-level cycle detection, enforced at write-time** — new `_creates_step_cycle(pipeline_id,
  new_upstream_id, new_downstream_id)` in `api/routes/steps.py` (NOT reusing `_has_path` — bound to
  the wrong model and one-query-per-hop): one query loads the whole per-pipeline edge set into an
  in-memory adjacency dict, then a visited-set/stack traversal checks whether the proposed edge would
  close a cycle. Safe to call on every request, including a future canvas keystroke in M3. Enforced now
  (not deferred to M2/M3) so the table is acyclic by construction before anything reads it. — **done
  2026-07-22**.
- [x] **New API routes** in `api/routes/steps.py` (reuse existing `bp`, no new blueprint; add
  `require_role` import + `StepDependency` import): — **done 2026-07-22**.
  - `GET /api/pipelines/<id>/step-dependencies` → flat `[{dep_id, upstream_step_id,
    downstream_step_id}]` list, 404/403 guarded same as existing routes.
  - `POST /api/pipelines/<id>/step-dependencies` (`@require_role(['admin','editor'])`) — validates
    both fields present (400), both step ids belong to this pipeline (404/400), self-reference (400),
    `_creates_step_cycle` (409), duplicate (409), then insert (201).
  - `DELETE /api/pipelines/<id>/step-dependencies/<dep_id>` (`@require_role(['admin','editor'])`) —
    scoped by pipeline match, 404 if not found.
- [x] **Tests**: new `tests/test_step_dependencies_model.py` (valid edge, self-reference constraint,
  duplicate constraint, cascade on step delete, cascade on pipeline delete, `exists_for_pipeline`
  true/false). New API tests appended to `tests/test_pipelines_extended_coverage.py` alongside the
  existing pipeline-dependency tests (empty list, add+list+remove round-trip, self-reference → 400,
  missing ids → 400, step not found → 404, cross-pipeline rejected, cycle → 409 mirroring
  `test_cycle_detection_blocked`, duplicate → 409, remove-not-found → 404). **Regression test proving
  zero impact on the existing engine** — **done 2026-07-22**, with one deviation from the original
  plan: rather than extending `test_runner_extended.py`/`test_loader_unit.py` (both of which operate
  on hand-built `BaseStep`/`MagicMock` fixtures with no real DB or pipeline_id, so there was nowhere
  to hang a real `StepDependency` row), the regression test
  (`test_step_dependencies_do_not_affect_loader_order`) lives in the new
  `test_step_dependencies_model.py` alongside the other real-DB model tests: builds a real
  pipeline/steps via the ORM, calls `loader.load_pipeline(...)` before and after inserting a
  `StepDependency` edge that (if honored) would reverse execution order, and asserts the returned
  step order is byte-for-byte identical both times — the concrete proof of the backward-compatibility
  decision above.
- [x] **Verification**: `alembic upgrade head` clean, `downgrade -1` then `upgrade head` again
  (reversibility); full backend suite green; manual round-trip (`POST` valid → 201, repeat → 409,
  reversed pair closing a cycle → 409, `GET` lists it, `DELETE` removes it). — **done 2026-07-22**:
  reversibility verified directly via `alembic` `command.current/downgrade/upgrade`; full backend
  suite green (2067 passed); round-trip verified via the new pytest API-client tests rather than a
  separately booted live app instance (Flask test client exercises the same routes end-to-end
  against the same real Postgres test DB, so this is equivalent coverage, not a shortcut).

##### Milestone 2 — Runner rewrite: topological DAG execution engine — done 2026-07-22

Scope: `runner.py`, `loader.py`, new `engine/dag.py` kept separate from the untouched wave
code path.

- [x] Dual-path gate on `StepDependency.exists_for_pipeline` — `False` keeps the exact existing wave
  path; `True` builds the graph and runs the new scheduler. — **done**: gated in
  `runner.run_pipeline` on `pipeline_id` + `StepDependency.exists_for_pipeline`; wave path
  (`_build_execution_waves` and the whole `for wave in waves` loop) is untouched — verified by the
  full 2081-test suite staying green, including every pre-existing `test_runner*.py` test (all of
  which call `run_pipeline` without a `pipeline_id`, so the gate is a no-op for them).
- [x] New scheduler: in-degree/ready-set model — dispatch any step whose upstream deps have all
  completed, as soon as they complete, rather than wave-synchronized `ThreadPoolExecutor` batches.
  — **done**: `flowforge/engine/dag.py::run_dag` — a single `ThreadPoolExecutor` alive for the
  whole run, `concurrent.futures.wait(..., FIRST_COMPLETED)` driving a ready-queue/in-degree loop
  (`tests/test_dag_engine.py::test_linear_chain_all_succeed`,
  `test_independent_branches_run_concurrently`).
- [x] Branch-scoped `on_error='stop'` — compute each step's transitive descendant set (same adjacency
  structure as cycle detection) so a stop-failure only short-circuits its descendants. — **done**:
  on a `stop` failure, the node's full transitive descendant set (precomputed once per node at
  graph-build time, not recomputed per failure) is marked skipped and finalized immediately,
  without going through the normal in-degree/ready path — proven safe because a descendant set is
  closed under `adjacency` by construction, so nothing outside it needs touching. Independent
  branches are provably unaffected (`test_stop_failure_skips_only_descendants`), multi-level chains
  fully skip (`test_stop_failure_skips_transitive_descendants_multi_level`), and a merge point fed
  by both a failed branch and an independent one is skipped regardless of the independent upstream's
  state (`test_merge_point_downstream_of_stop_failure_is_skipped_even_with_independent_upstream`) —
  an explicit design call not spelled out in the original decision: this engine skips eagerly the
  instant the failure is known, rather than waiting for every upstream of a merge node to reach a
  terminal state first (Airflow's default trigger-rule behavior). Proven safe here because a
  descendant can only be reachable this way if the failed node is genuinely one of its ancestors, so
  it could never have already been dispatched — but it does mean a "diamond" merge node is skipped
  without waiting on its still-running independent branch to finish (that branch keeps running to
  completion on its own; its output/step_run is simply never consumed). Skipped steps get a real
  `step_runs` row with `status='skipped'` (schema already supported this status since the
  `0001_baseline` migration; nothing previously wrote it) via a new `skipped` kwarg on
  `_write_step_run` (default `False`, so the wave path's calls are unaffected).
- [x] Ancestors-only context — each step's context snapshot built from only its transitive-ancestor
  outputs, computed from the graph (a new construction helper, not a tweak of `_expose_step_outputs`).
  — **done**: `dag.py`'s `_step_output_entry`/`_step_output_vars` are deliberate duplicates of
  `runner._expose_step_outputs`'s logic (returning values instead of mutating a shared dict) so the
  wave path's function is never touched; `_build_node_context` merges only a node's precomputed
  ancestor set's outputs. Scope call beyond the original wording: "ancestors-only" was applied to
  **both** `{{ steps.X.* }}` *and* flattened `output_variables` (e.g. a custom var set via
  `output_variables`) — the latter wasn't explicitly named in the original decision, but it's the
  same category of "step output" and leaving it globally visible would have quietly broken the
  stated principle ("the graph drawn is the graph that actually matters"). Proven by
  `test_context_only_exposes_transitive_ancestors` (an independent sibling's output is invisible)
  and `test_context_step_output_entry_visible_to_descendant`.
- [x] Retries unaffected in shape, just invoked per-node instead of per-wave. — **done**: `_run_node`
  calls the exact same `_get_retry_config`/`_run_step_with_retry` pair as both wave-mode code paths,
  imported unchanged from `runner.py`.
- [ ] Stretch (not required to close M2, left open): decide whether to leave Jinja's default
  `Undefined` (silently blank for an undeclared step reference) or add a DAG-build-time lint for it.
  Not addressed — genuinely optional per the original scoping.
- [x] Resolve the disabled-step-referenced-by-an-edge policy flagged in Milestone 1. — **done**:
  "skip-and-satisfy" — `run_dag` drops any edge where either endpoint isn't among the loaded
  (enabled) steps, logging a warning with the count. A downstream step that only depended on a
  disabled upstream is therefore never blocked waiting for it. Covered by
  `test_edge_referencing_missing_step_is_dropped_not_fatal`.

**Tests**: `tests/test_dag_engine.py` (14 unit tests against `run_dag` directly — no DB, `_write_step_run`
mocked) plus `tests/test_runner_dag_gate.py` (2 real-DB integration tests proving the gate itself:
a pipeline with `StepDependency` rows routes to `run_dag` with the right edges; one with none stays
on the wave path, `run_dag` never called). Full backend suite: 2081 passed, 0 regressions. Ruff clean.

##### Milestone 3 — Canvas: real edge-drawing wired to the M1 API — done 2026-07-22

Scope: `PipelineCanvas.tsx`, `StepNode.tsx`, `layout.ts`, new API client functions.

- [x] Wire `onConnect` on `<ReactFlow>` (absent today) → calls the M1 `POST step-dependencies`
  endpoint; 409 (cycle) surfaces as inline UX feedback, not a silent failure. — **done**: new
  `stepDeps.ts`'s `canConnectSteps` guards client-side (unsaved pipeline/step, self-connection)
  before the round-trip; `PipelineCanvas.tsx`'s `handleConnect` calls `addStepDep` and shows any
  API error (cycle, duplicate, etc.) in a dismissible inline banner
  (`data-testid="canvas-connect-error"`) — never a silent failure. Deliberately diverges from how
  pipeline-to-pipeline dependencies work elsewhere in this codebase (`DependenciesCard`/
  `TriggersCard`: local-state-only, batched into the parent's Save-time sync loop): step edges
  persist immediately on connect instead, because live cycle feedback at draw-time is the whole
  point of a canvas connect gesture — deferring it to Save would let a doomed edge appear to draw
  successfully and only fail later, disconnected from the gesture that created it.
- [x] Handle `id`s on `StepNode`'s `<Handle>` components if multiple distinct connection points per
  step are needed (explicit M3 scope call — single handle per side may be an acceptable v1). —
  **taken as-is**: `StepNode.tsx` unchanged, single unnamed target/source handle per side (left/right).
- [x] Fetch real edges from the M1 API; if any exist for the pipeline, use them exclusively and skip
  the synthetic `buildWaveEdges` cartesian edges — mirrors the backend's dual-path gate on the
  frontend. — **done**: `PipelineEdit.tsx` fetches `stepDeps` via `useQuery(['step-deps', id])`
  (`enabled: !isNew`) and passes them + `pipelineId` down; `PipelineCanvas.tsx`'s `hasRealEdges =
  stepDeps.length > 0` gate switches both the rendered edges (`toRealFlowEdges` vs
  `buildWaveEdges`) and the layout (`layoutRealEdges` vs `layoutWaves`, the former new in
  `layout.ts`, both sharing a `layoutFromEdges` helper). Real edges render in the accent color,
  visually distinct from the neutral synthetic ones — verified live in a browser (screenshots),
  not just unit tests.
- [x] Decide what `onNodeDragStop`'s existing reorder logic (`resolveDropTarget`/`assignParallelGroup`)
  means once a pipeline is in DAG mode. — **decided**: it's a no-op once `hasRealEdges` is true —
  `step_order`/`parallel_group` no longer drive execution order in DAG mode (M2), so reassigning
  them on drag would be meaningless. The node still visually follows the cursor during the drag
  (react-flow's default behavior) but snaps back to its dagre-computed position on the next render
  since positions are never persisted — verified live: dragging a node in DAG mode leaves
  `step_order`/`parallel_group` unchanged server-side and the node visually returns to place.
- [x] Add drag/connect coverage to `PipelineCanvas.test.tsx` and `e2e/pipeline-canvas.spec.ts` — both
  currently have zero. — **done, with a scope note**: a real handle-to-handle pointer drag is the
  same class of gesture already documented in `pipeline-canvas.spec.ts`'s header comment as too
  flaky to automate reliably (worse than node-repositioning drag — it must land on a 6px handle).
  Followed that same established precedent rather than fighting it: `PipelineCanvas.test.tsx` mocks
  `ReactFlow` itself (not the handlers under test) to expose `onConnect`/`onEdgesDelete` as plain
  buttons while still mounting real `StepNode`/`StepPanel` components via the real `nodeTypes`, so
  every pre-existing test in the file keeps exercising real DOM — 7 new tests cover synthetic-vs-
  real edge selection, successful connect, unsaved-pipeline/self-connect rejection, 409 surfacing,
  and edge deletion, all against the *actual* `handleConnect`/`handleEdgesDelete` code, not a
  reimplementation. `e2e/pipeline-canvas.spec.ts` adds one real end-to-end test: create a step
  dependency via a direct API call (mirroring what a successful drag would do), then assert the
  canvas fetches and renders it as a real edge and that it survives a reload — run live against
  the full stack (6/6 passed). Also added: unit tests for the new pure `stepDeps.ts` helpers
  (`toRealFlowEdges`, `canConnectSteps`) and `layout.ts`'s new `layoutRealEdges`. Full frontend
  suite: 172 passed (was 154), `tsc --noEmit` clean, `npm run build` clean, eslint clean.

##### Milestone 4 — Test matrix and regression preservation — done 2026-07-22

- [x] New: partial-branch failures (stop halts only descendants, sibling branch completes), concurrent
  execution of independent branches (real overlap, not just same-`parallel_group`), `{{ steps.* }}`
  resolution across non-linear branches (only ancestors visible, not siblings). — **done**: new
  `tests/test_dag_integration.py` (4 tests), deliberately complementing rather than duplicating M2's
  existing coverage — `test_dag_engine.py`'s 12 unit tests exercise `run_dag()` directly with
  `_write_step_run` mocked (no DB), and `test_runner_dag_gate.py`'s 2 tests prove only the
  engine-selection gate itself. This file instead drives the real `runner.run_pipeline` entry point
  against a real Postgres test DB with real `StepDependency` rows, and asserts against the actual
  persisted `StepRun`/`PipelineRun` rows rather than in-memory return values:
  `test_partial_branch_failure_writes_correct_step_run_statuses` and
  `test_partial_branch_failure_skips_multi_level_descendants_only` (branch-scoped stop, single- and
  multi-level descendant sets, verified via real `status='skipped'`/`'failed'`/`'success'` `StepRun`
  rows); `test_independent_branches_real_overlap_recorded_in_db` (two independent roots' real
  `started_at`/`finished_at` timestamps, read back from the DB, must overlap — stronger proof than
  M2's wall-clock-elapsed unit test, since it confirms concurrency survives all the way to what gets
  persisted); `test_context_ancestors_only_resolves_correctly_through_jinja` (a sibling's
  `output_variables` render as empty string through the real `engine.context.render()` Jinja path,
  not just raw dict access, while an ancestor's `{{ steps.X.* }}` entry and flattened var both
  resolve correctly). One real bug caught and fixed in the test itself while writing the concurrency
  test: `StepDependency.exists_for_pipeline` gates on whether the *pipeline* has any edge at all, not
  whether the specific pair under test does — an initial version with zero edges between the two
  "independent" steps silently fell back to the wave engine (sequential) instead of exercising the
  DAG engine at all; fixed by adding an unrelated `x -> y` edge elsewhere in the same pipeline so the
  gate activates while `a`/`b` remain genuine independent DAG roots.
- [x] Preserve unmodified: all `test_build_waves_*` and existing `on_error`/context tests — if any fail
  after M2 lands, that's a signal the dual-path gate leaked into the old path. — **done**: none of
  `test_runner.py`, `test_runner_extended.py`, `test_loader_unit.py` touched. Full backend suite:
  2085 passed (2081 baseline + 4 new), 0 regressions, ruff clean.
- [x] Adapt via new tests (not edits): DAG-mode counterparts of the "stop halts everything" tests,
  asserting the new branch-scoped semantics instead. — **done**:
  `test_partial_branch_failure_writes_correct_step_run_statuses` is the explicit DAG-mode counterpart
  of `test_runner.py::test_on_error_stop_halts_pipeline` (wave mode: a stop-failure halts every
  remaining step, so the independent step is never even attempted) — same shape, opposite assertion:
  the independent step completes and gets a real `'success'` `StepRun` row.

---

## Session — 2026-07-21 (Phase 13 — Unified Registry & Plugin Architecture complete) 🟢 *(COMPLETE)*

### Phase 13 — Unified Registry & Plugin Architecture (2026-07-07) — all sub-phases complete

*Replaces the four separate hardcoded if/elif dispatch points (steps, connections, email providers,
storage) with one generic registry primitive, then wires the existing plugin loader and frontend
through it. Framing note: this phase builds the capability-introspection **seam** (what's registered,
what's installed) — it deliberately does not add a tier/licensing/entitlement **gate** on top of it.*

#### 13.1 Generic registry primitive

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

#### 13.2 Migrate connections + email providers off if/elif

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

#### 13.3 Extend the plugin loader beyond steps

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

#### 13.4 Kill remaining hardcoded lists

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

#### 13.5 Capability introspection (the seam, not the gate)

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

---

## Session — 2026-07-08 (Phase 12 Tailwind Migration complete + frontend bundle code-splitting) 🟢 *(COMPLETE)*

### Nice-to-Have — code-splitting and Phase 12 close-out fixes

- [x] Root-cause the Phase 12 `!important` workaround + remove dead CSS *(2026-07-08, post-Phase-12 follow-up)* — wrapped every custom class in `index.css` (`.card`, `.btn`, `.input`, `.chip`, `.tbl`, `.field`, `.pill`, `.tbadge`, `.ff-*`, base reset, responsive grids, etc.) in `@layer components`, so Tailwind's `@layer utilities` naturally wins on any property conflict — no `!` needed. Mechanically stripped all ~217 now-unnecessary `!`-prefixed classes across 29 files (chunks 12.2–12.13 plus two pre-existing spots in `PipelineVariablesCard.tsx`/`WebhookCard.tsx`) via a targeted regex script (`!` immediately followed by a hyphenated utility token — safe because JS identifiers can't contain hyphens, so there was no risk of clobbering a JS `!condition` negation), then re-verified via `getComputedStyle` and a full `tsc`/`eslint`/`vitest`/`build` + live-verification pass (`Dashboard`, `ReportEdit`, `Settings`, `Connections`, Pipeline Builder) — zero visual diff, CSS bundle shrank to 44.92 kB (from 48.78 kB pre-Phase-12). Also deleted 7 confirmed-dead CSS rules found via a systematic sweep of every custom class against every `className` usage in `pages/`/`components/`: `.panel-scroll`, `.ff-div`, `.ff-brand`, `.ff-nav-count`, `.badge-success`, `.badge-danger`, `.badge-running` (the last three explicitly marked "backward compat" and superseded by `.pill-*`, confirmed zero references before deleting).
- [x] Code-split the frontend bundle *(found 2026-07-08, fixed 2026-07-08)* — `frontend/dist/assets/index-*.js` was ~1.1MB, well over Vite's default 500KB `chunkSizeWarningLimit`, because all 17 pages were statically imported in `App.tsx`. Converted every page import in `App.tsx` to `React.lazy(() => import(...))`; added a `<Suspense fallback={<RouteFallback/>}>` boundary around `<Routes>` (for the top-level `/login` route) and a second one inside `Layout.tsx` around `<Outlet/>` (nested under `RouteErrorBoundary`, so sidebar/topbar stay mounted and lazy-load failures are still caught) — new shared `components/shared/RouteFallback.tsx` centers the existing `Spinner`. Result: main entry chunk dropped to 254 kB, with heavy dependencies (Recharts `LineChart` at 381 kB, CodeMirror bundled into `ReportEdit`/`PipelineEdit`, `types.ts` at 92 kB) now split into their own on-demand chunks — no chunk-size warning on build. Verified: `tsc --noEmit` clean, `vitest run` 97/97 passing, production build produces 30+ per-route/per-dependency chunks, and a headless Playwright smoke test against `vite preview` confirmed loading `/login` only fetches 4 small chunks (`index`, `rolldown-runtime`, `api`, `Login`) with zero console errors — none of the other pages' code (or Recharts/CodeMirror) loads until their route is visited.

### Phase 12 — Tailwind Migration (2026-07-06) — all 14 chunks complete

*Styling cleanup only — no behavior changes. `tailwindcss@4` + `@tailwindcss/postcss` are already
installed and configured (`tailwind.config.ts`, content globs cover `src/**/*.{ts,tsx}`); adoption is
just inconsistent. 54 of 62 `.tsx` files under `pages/`/`components/` still use inline
`style={{...}}` as their primary styling mechanism — **1,125 occurrences total** — while only
`Dashboard.tsx` mostly uses real Tailwind utility classes (`className="flex items-center gap-3"` etc.).
This phase converts the remaining 53 files, broken into 14 independently-completable chunks so no
single session has to touch the whole frontend at once.*

#### Ground rules (applied to every chunk below)

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
  `.tbadge`/`.pill`/`.tbl`/`.field`/`.label` on any property those classes already set.** ~~*(found
  2026-07-08, during 12.7)*~~ **Superseded 2026-07-08 (post-Phase-12 follow-up):** root-caused instead
  of worked around — `index.css`'s custom classes are now wrapped in `@layer components`, which Tailwind
  places *before* `@layer utilities` in its layer order, so utility classes win naturally without any
  `!`. All ~217 `!`-prefixed workarounds added across chunks 12.2–12.13 (plus two pre-existing ones in
  `PipelineVariablesCard.tsx`/`WebhookCard.tsx` predating Phase 12) were mechanically stripped and
  re-verified via `getComputedStyle` (e.g. `card p-0` → `padding: 0px` with **no** `!` needed) plus a
  full `tsc`/`eslint`/`vitest`/`build` pass and a live-verification sweep of `Dashboard`, `ReportEdit`,
  `Settings`, `Connections`, and the Pipeline Builder — zero visual diff, CSS bundle shrank further
  (44.92 kB, down from 47.65 kB) since Tailwind no longer emits `!important` variants. The `!`-prefix
  rule below is kept for historical context (why chunks 12.7–12.13 look the way they do in git
  history) but **does not apply to new code** — don't add `!` prefixes going forward; if a utility
  doesn't override a `.card`/`.input`/etc. property, something regressed in the `@layer` setup, not a
  case for reaching for `!`.
  Original finding *(2026-07-08, during 12.7)*: these custom classes live in `index.css` as plain (unlayered) CSS, while
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

#### 12.0 Foundation — sync Tailwind theme with the full design-token set

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

#### 12.1 Shared layout/chrome components — highest leverage, rendered on every page

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

#### 12.2 Pipeline step-form components + StepEditor

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

#### 12.3 Connections sub-components

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

#### 12.4 Misc remaining components

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

#### 12.5 `pages/RunDetail.tsx` — standalone (111 occurrences, most complex page)

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

#### 12.6 `pages/ReportEdit.tsx` — standalone (104 occurrences)

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

#### 12.7 `pages/Settings.tsx` + `pages/BulkLoadEdit.tsx` (75 + 73 = 148 occurrences)

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

#### 12.8 `pages/Connections.tsx` + `pages/EmailEdit.tsx` (55 + 53 = 108 occurrences)

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

#### 12.9 `pages/Projects.tsx` + `pages/RunHistory.tsx` (53 + 51 = 104 occurrences)

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

#### 12.10 `pages/Pipelines.tsx` + `pages/Login.tsx` (50 + 46 = 96 occurrences)

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

#### 12.11 `pages/Users.tsx` + `pages/AuditLog.tsx` + `pages/Recipients.tsx` (32 + 30 + 25 = 87 occurrences)

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

#### 12.12 `pages/Emails.tsx` + `pages/BulkLoads.tsx` + `pages/Reports.tsx` (24 + 22 + 21 = 67 occurrences)

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

#### 12.13 `pages/Dashboard.tsx` — cleanup pass (12 occurrences)

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

## Session — 2026-07-05 / 2026-07-06 (Nice-to-have polish + observability) 🟢 *(COMPLETE)*

- [x] Consolidate migration ID scheme *(2026-07-06)* — the 4 autogenerated hash-named files (`6158f44dafca`, `b7a76582c1ea`, `9c08f36f9ef8`, `c4e8f2a1b9d3`) sat between `0019` and `0020` in the actual `revision`/`down_revision` chain but sorted out of order alphabetically. Renamed to `0019a`/`0019b`/`0019c`/`0019d_*.py` (via `git mv`, preserving history) so directory order now matches execution order. Filenames only — the `revision =` ID strings inside are untouched, since those are what's recorded in any already-deployed database's `alembic_version` table; changing them would require a bridging migration and wasn't worth the risk for a cosmetic fix. Verified: `ScriptDirectory.walk_revisions()` still resolves to a single head (`0028_project_members`) with the same full chain, and the full test suite (which runs `alembic upgrade head` per session) passes unchanged (1896 tests).
- [x] Add loading skeletons for data-fetching views *(2026-07-06)* — 9 pages previously showed a bare `<Spinner/>` on an otherwise blank screen while loading: `AuditLog`, `BulkLoadEdit`, `Emails`, `Pipelines`, `Projects`, `Recipients`, `Reports`, `RunDetail` got full content-shaped skeleton layouts (title/table/card placeholders via the existing `Sk`/`Skeleton` component, matching the pattern already used on `Dashboard`/`BulkLoads`/`RunHistory`/etc.); `Settings` didn't block on a blank page (each card already rendered immediately with the page shell), so its 4 small per-card status-badge spinners were swapped for skeleton pills instead, for visual consistency. Added a `ResizeObserver` stub to `src/__tests__/setup.ts` (unrelated prerequisite hit while re-running the suite). Verified live: started the Flask backend + Vite dev server, logged in via Playwright, and screenshotted all 9 pages with real dev data (including triggering a real pipeline run for `RunDetail` and opening a real bulk-load config for `BulkLoadEdit`) — zero console/runtime errors on any page.
- [x] Pin Docker base images to digest *(2026-07-06)* — the app `Dockerfile` was already digest-pinned on both stages; the gap was service images referenced by mutable tag only: `postgres:16-alpine` and `redis:7-alpine` in `docker-compose.yml`, `gvenzl/oracle-free:23-slim` in `docker-compose.oracle.yml`, `postgres:16-alpine` in `docker-compose.sample-db.yml`, and the `postgres`/`redis` CI service containers in `.github/workflows/test.yml`. All resolved via `docker buildx imagetools inspect` and pinned `tag@sha256:digest` (keeps the tag readable alongside the immutable digest, matching the Dockerfile's existing style). Verified with `docker compose config` against the merged stacks. Added a `docker` ecosystem entry to `.github/dependabot.yml` (directory `/`, monthly) to track the Dockerfile + all 3 `docker-compose*.yml` files going forward — **known gap**: Dependabot's `docker` ecosystem doesn't scan `image:` strings inside GitHub Actions workflow YAML, so the two CI service-container pins in `test.yml` won't auto-update and need re-pinning by hand if they drift.
- [x] **Audit Log — link `run_id` for cross-referencing** *(scoped 2026-07-05, shipped 2026-07-06)* — `PIPELINE_STARTED`/`PIPELINE_SUCCESS`/`PIPELINE_FAILED` audit entries already carried `run_id` (`runner.py:260,316`), but `log_email_sent()` and `log_report_exported()` (`flowforge/audit.py`) only stored `pipeline_name`/`step_name` — no `run_id`. Added a `run_id: str = ''` parameter (appended, default `''`, so existing positional call sites/tests are unaffected) to both functions — included in the log line (`run_id=<id>` or `run_id=unknown`) and in the `details` JSONB written to `ff_audit_log`. Threaded through from `email_step.py`/`report.py` via `context.get('run_id', '')` (already set by the runner on every pipeline context). No frontend change needed — the Audit Log page's Details column already `JSON.stringify`s the full `details` dict, so `run_id` shows up automatically and can be cross-referenced against Run History without fuzzy-matching on name + timestamp.
- [x] **Step performance trends over time** *(scoped 2026-07-05, shipped 2026-07-06)* — `step_runs` already recorded `duration_ms`, `rows_affected`, and `status` for every step type (bulk load, SFTP, db_procedure, report, email, etc.) — `_write_step_run()` in `runner.py:425` is called generically regardless of step type, so the raw data already existed; this only adds a view over it, no new collection. New `GET /api/step-runs/trends` endpoint (`flowforge/api/routes/runs.py`, same blueprint as the existing anomalies/diff endpoints) accepts `step_type`, `pipeline_id`, `project_id` (access-scoped like `list_runs`), and `days` (default 30, clamped to [1, 180]); buckets matching `step_runs` rows by day and returns per-bucket `run_count`/`success_count`/`failure_count`/`avg_duration_ms`/`p95_duration_ms`/`avg_rows_affected`, plus `available_step_types` for populating a picker. Aggregated in Python (`statistics.mean` + a nearest-rank `_percentile()` helper) rather than DB-side percentile functions, matching this file's existing `_check_anomaly` convention instead of introducing a Postgres-only SQL construct. Frontend: new collapsible `StepTrendsPanel` component (lazy-loaded on expand, mirroring `DiffPanel`'s pattern) rendered on the Run History page, with a step-type dropdown, a 7d/30d/90d window picker, and a Recharts line chart (avg + p95 duration) styled to match `ChartPreview.tsx`'s existing palette/tooltip/axis conventions.
- [x] Bulk load dry-run V2 *(scoped 2026-07-04, V1 shipped same day; error-grouping requirement added 2026-07-05; V2 shipped 2026-07-06)* — V1 (`preview_bulk_load()` in `flowforge/steps/bulk_load.py`, "Test File" button in `BulkLoadEdit`/`BulkLoads`) checks file discovery, header parsing, and target-column existence, but CSV values are untyped text — it can't catch type-coercion or constraint errors (NOT NULL, unique/PK, length overflow) that only surface once a real insert runs. V2 adds an opt-in "Attempt insert (rolled back)" checkbox in `BulkLoadEdit` that passes `dry_run=true` through `POST /bulk-load-configs/{id}/validate` and `.../validate-raw` to `preview_bulk_load(cfg, dry_run=True)`: it builds the exact same parameterized `INSERT` statement `_load_python_fallback` uses (reusing the real code path, not a heuristic type-check) and attempts each sampled row individually against the real target table inside a `SAVEPOINT`, rolling the whole transaction back at the end — nothing is ever committed. Per-row execution (rather than reusing the batch COPY/executemany calls verbatim) was a deliberate deviation from the original literal wording, since a batched statement aborts at the first bad row and can't surface a second, unrelated failure — savepoint-per-row was the only way to satisfy the error-grouping requirement below while still hitting the real DB engine's real constraint/type checking. Scoped to PostgreSQL + the Python-fallback path only; skipped for the Oracle `sqlldr` path (manages its own commits) with a warning surfaced both dynamically (`preview_bulk_load` warnings) and statically in the "Use SQL\*Loader" checkbox's UI copy in `BulkLoadEdit.tsx`.
  - **Error reporting groups by error signature, not per-row.** `_classify_insert_error()` maps driver exceptions to `(error_type, column)` — psycopg2's `.diag.sqlstate`/`.diag.column_name` when available, else ORA-code / substring matching. `_group_insert_errors()` groups all rows hitting the same `(column, error_type)` into one entry `{row_indices, column, error_type, message, count}`, sorted by count descending. `_insert_error_summary()` produces the lead line (e.g. "3 error types across 14 of 20 sampled rows"). `BulkLoadEdit.tsx` renders the summary + grouped detail above the sample-rows table, caps the row numbers shown per group to first 3 + "and N more" (`formatRowNumbers()`), and highlights every affected row/cell in the table (not just the capped ones) by cross-referencing `row_indices`/`column` against the rendered grid.
- [x] Env-var exfiltration via bulk-load preview endpoint — the new `/bulk-load-configs/validate-raw` endpoint (merged in #94) let any authenticated user, regardless of role, exfiltrate any env var not in the (then 7-entry) `_SafeEnv` blocklist by crafting a `source_directory`/`target_table` like `{{ env.FLOWFORGE_DB_URL }}`; the rendered value was echoed verbatim into the returned error/warning message. Fixed in #95: expanded `_ENV_BLOCKLIST` (added `FLOWFORGE_DB_URL`/`REDIS_URL`, AWS/Azure/SSO/SAML secrets, `DB_PASSWORD`) plus a name-pattern check (`_looks_like_credential_name`) so future credential-shaped env vars are blocked by default; `preview_bulk_load()` no longer reflects rendered template values in messages, only the original template string. 23 new/updated tests.
- [x] Branch-Protection: grant the Scorecard GitHub App `administration:read` (Settings → Integrations → GitHub Apps), or add a fine-grained PAT as the `SCORECARD_TOKEN` secret — quick fix for a currently-erroring (-1) check *(Scorecard — Branch-Protection)* — **done 2026-07-06**: `SCORECARD_TOKEN` (fine-grained PAT, `administration:read`) wired into `.github/workflows/scorecard.yml` (PR #94).

---

## Session — 2026-07-02 (Phase 11 critical security fixes + refactoring) 🟢 *(COMPLETE)*

### Critical (fix immediately / showstoppers)

- [x] **SQL injection in `data_load.py`** *(2026-07-02)* — added `validate_identifier()` guard for `target_table` (post-render) and every column name (post-`column_map`) before they're interpolated into `CREATE TABLE`/`TRUNCATE`/`INSERT`, matching `db_query.py`/`bulk_load.py`. Query-source rendering also switched from `render()` to `render_sql()`.
- [x] **Secrets leak via shared step context** *(2026-07-02)* — `render_sql()` now hard-blocks (raises `SecretLeakError`) instead of warning when a secret pipeline variable is referenced. Added `render_guarded()` in `engine/context.py` and applied it to every sink where a secret could be persisted/transmitted outside the pipeline: `email_step.py` (subject/body/drive-share message), `notification.py` (message/title), `ai_analyze.py` (query/prompt), and `data_load.py`'s query source. Legitimate secret sinks (`db_procedure` params — true bind variables, SFTP/S3/Azure credentials) are untouched.
- [x] **SSRF in notification webhooks** *(2026-07-02)* — new `flowforge/net_guard.py` (`assert_public_url()`) rejects link-local/RFC1918/loopback/multicast/unspecified resolved IPs; wired into `notification.py`'s Slack and Teams webhook senders before any outbound request. Telegram's API host is fixed (not editor-configurable), so no guard needed there.
- [x] **Audit log miscategorization for user management** *(2026-07-02)* — added `audit.log_user_change()` (writes `USER_CREATED`/`USER_UPDATED`/`USER_DELETED`); `api/routes/users.py` now calls it instead of `log_pipeline_change()`.
- [x] **Reconcile `ROADMAP.md` / `TASKS.md` / `CLAUDE.md`** *(2026-07-02)* — `docs/TASKS.md` designated as the authoritative, evidence-based tracker. `ROADMAP.md` rewritten to match actual shipped state (verified against code) and now explicitly defers to TASKS.md; also calls out the one confirmed real gap (visual DAG canvas never built). `CLAUDE.md`'s stale "Non-Goals (v1)" and "Authentication (v1)" sections (still describing multi-user auth/Slack-Teams/S3-Azure as unbuilt) corrected and pointed at ROADMAP.md/TASKS.md.

### High Priority (refactoring & scalability)

- [x] **Break up frontend god-components** *(2026-07-02)* — `StepEditor.tsx` 782→168 lines: each step-type form moved to `components/pipeline/stepForms/*.tsx` (10 forms + shared `Field`/`types` + a `STEP_FORMS` registry StepEditor dispatches through). `PipelineEdit.tsx` 775→352 lines: `PipelineVariablesCard`, `DependenciesCard`, `WebhookCard`, `CronBuilder` extracted to `components/pipeline/*.tsx`. `Connections.tsx` 861→484 lines: per-DB-type (`DbFieldsGeneric/Odbc/Snowflake/BigQuery`) and per-provider-type (`MailFieldsSmtp/OAuth/Sendgrid/Ses/Mailgun`) field components plus `DbConnectionRow`/`EmailProviderRow` extracted to `components/connections/*.tsx`. All three verified live in-browser (every step type / DB type / provider type rendered and interacted with, zero console errors) in addition to `tsc`/`eslint`/production build passing.
- [x] **Enforce a real coverage threshold** *(2026-07-02)* — this finding was stale: `--cov-fail-under=72` had already existed in `test.yml` since an earlier commit, but a later commit (`8236da5`) pushed actual coverage to 88%+ without raising the floor, leaving a ~19-point regression window. Verified all pending work was purely additive, measured actual coverage locally (90.6%–91%), and raised `--cov-fail-under` 72→88 in `test.yml` plus `codecov.yml`'s `project.default.target` 70%→88% and `patch.default.target` 60%→75% (threshold widened 5%→10% to tolerate normal per-PR variance) so both gates now track reality instead of a stale historical floor.
- [x] **Load-test the scheduler and Redis fail-open concurrency path** *(2026-07-02)* — used a real Docker Redis container (`docker pause`/`unpause`) plus a real hanging TCP server and real Postgres jobstore for genuine failure injection, not mocks:
  - **Found and fixed a real bug**: `_redis_client()` set `socket_connect_timeout` but not `socket_timeout`, so a Redis that accepted the TCP connection but then hung (frozen/overloaded/blackholed mid-command — reproduced via `docker pause`) caused `try_acquire()` to block **indefinitely**, silently defeating the documented fail-open guarantee. Fixed by adding `socket_timeout=3`; verified the same `docker pause` scenario now fails open in ~3s. Permanent regression test added (`tests/test_concurrency_failure_injection.py`) using a real hanging TCP socket server, so this is caught in CI without a Docker dependency.
  - Verified with real concurrent load against a real Redis (50 threads, 50 concurrent `try_acquire()` calls, limit=10): the Lua acquire script grants **exactly** 10 slots with zero duplicates — atomicity holds under genuine concurrency, not just sequential mocks. Added a `redis:7-alpine` service to `test.yml` so this runs in CI too (`FLOWFORGE_TEST_REDIS_URL`), not just locally.
  - Verified the scheduler's "jobs survive scheduler restarts" claim against a real Postgres-backed `SQLAlchemyJobStore`, with a genuinely hard-killed scheduler process (no graceful `shutdown()` — matching what an actual crash looks like, not just a clean restart): jobs and their latest schedule updates both survive. Claim holds. Test added in `tests/test_scheduler_jobstore_persistence.py`.

---

## Session — 2026-07-01 (V3.0 Backlog complete: connectors, storage, plugin system, pipeline features) 🟢 *(COMPLETE)*

*No fixed date originally targeted — community-driven backlog. All items below shipped 2026-07-01 unless individually dated otherwise.*

### New Connectors & Providers
- [x] Snowflake / BigQuery / Redshift connectors *(2026-07-01)* — `connections/{snowflake,bigquery,redshift}.py`; Redshift is a thin `PostgreSQLConnection` subclass (wire-compatible, no new dependency); Snowflake via `snowflake-connector-python`; BigQuery via `google-cloud-bigquery` (named `@pN` query parameters instead of positional `%s`, since BigQuery has no DBAPI-style placeholders); `db_type` CHECK constraint relaxed via migration `0027`; Connections page has dedicated Snowflake/BigQuery config forms (service account JSON masked in API responses)
- [x] AWS S3 / Azure Blob upload step *(2026-07-01)* — `steps/{s3_upload,azure_blob_upload}.py` + `storage/{s3,azure_blob}.py`; credentials via env vars (`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`/`AWS_DEFAULT_REGION`, `AZURE_STORAGE_CONNECTION_STRING` or `AZURE_STORAGE_ACCOUNT_URL`+`KEY`), matching the existing Drive/OneDrive convention; presigned/SAS shareable URLs by default; documented in `docs/step-types.md`
- [x] MSSQL / SQL Server connection support — `connections/mssql.py` via `pyodbc`; `flowforge-io[mssql]` optional extra *(2026-05-30)*
- [x] Generic ODBC connection support — `connections/odbc.py` via `pyodbc`; DSN or connection string config *(2026-05-30)*
- [x] SendGrid API email provider — `email_providers/sendgrid.py`; Web API v3; base64 attachments; `pip install flowforge-io[all]` *(2026-05-30)*
- [x] AWS SES email provider — `email_providers/ses.py`; boto3 SES client; raw MIME for attachments; `pip install flowforge-io[ses]` *(2026-05-30)*
- [x] Mailgun email provider — `email_providers/mailgun.py`; Messages API v3; US/EU region; multipart attachments *(2026-05-30)*
- [x] Telegram / Slack / Teams notification step — `steps/notification.py`; step_type `notification`; platform selector in StepEditor; Slack/Teams via incoming webhook; Telegram via Bot API *(2026-05-30)*

### Pipeline Features
- [x] Pipeline dependencies — `ff_pipeline_dependencies` table; cycle detection; `_trigger_downstream_pipelines()` in runner fires eligible downstreams after success; CRUD at `GET/POST/DELETE /api/pipelines/{id}/dependencies`; Dependencies card in PipelineEdit *(2026-05-30)*
- [x] Parallel step execution — `parallel_group VARCHAR(100)` on `ff_pipeline_steps`; runner groups steps into waves; same-group steps run in `ThreadPoolExecutor`; context snapshots per thread, outputs merged after wave; visual group badge + indigo border in StepEditor *(2026-05-30)*
- [x] Pipeline run diff view — `GET /api/runs/{id}/diff` compares step rows/duration/file-size vs prev successful run; collapsible DiffPanel with colour-coded delta badges in RunDetail *(2026-05-30)*
- [x] Report column formatting rules — `column_formatting JSONB` on `ff_report_configs`; Excel generator applies `number_format`, `width`, conditional `PatternFill`/`Font` per rule; ColumnFormattingCard UI in ReportEdit (presets + colour pickers) *(2026-05-30)*
- [x] Environment promotion workflow — `POST /api/pipelines/{id}/promote` clones to target project (disabled); warns on secret vars + unresolved references; Promote (↗) button on Pipelines page with project picker modal *(2026-05-30)*

### Platform
- [x] Plugin system — community step types loaded from a directory *(2026-07-01)* — `flowforge/engine/loader.py` scans `FLOWFORGE_PLUGIN_DIR` (default `./plugins`) for `*.py` files defining `BaseStep` subclasses; consolidated the 4 previously-drifted step-type lists (DB CHECK constraint, API validation, 2 frontend arrays — this also fixed a pre-existing bug where `notification` steps couldn't be added via the API) into one registry exposed via `GET /api/step-types`; `ck_step_type` relaxed from an enum CHECK to a format check (migration `0026`) since plugin type names aren't known in advance; StepEditor falls back to a generic JSON config editor for types with no dedicated form; example plugin + authoring guide in `examples/plugins/http_webhook_step.py` / `docs/plugins.md`
- [x] `ff_project_members` join table — team-scoped project access (deferred from v2) *(2026-07-01)* — enforced (not just informational): non-admin users only see/edit pipelines, reports, emails, and recipient groups in projects they're a member of; admins bypass everywhere, matching the existing `require_role` convention. Shared `flowforge/api/project_access.py` helper (`can_access_project`/`scope_query`) applied across pipelines/steps/runs/reports/emails/recipients/projects routes. Fixed a pre-existing gap where `POST/PATCH/DELETE /projects` only required login (any role, including viewer) with no role check. New `GET/POST/DELETE /api/projects/{id}/members` endpoints (admin-only mutations); Projects page has a Members modal. Migration `0028` backfills every existing user into the Default project so nobody already using FlowForge loses access; new users and project creators are auto-added going forward
- [x] Password reset flow via email — `ff_password_reset_tokens` table; `POST /auth/password-reset/request|confirm`, `GET /auth/password-reset/validate/<token>`; user `email` column; "Forgot password?" on Login; Users page shows/sets email *(2026-05-30)*
- [x] Distributed Redis-backed concurrency lock (replaces per-process semaphore for horizontal scale) *(2026-07-01)* — turned out the semaphore had silently regressed to nothing in a prior refactor (no concurrency limiting existed at all). `flowforge/engine/concurrency.py`: in-process `threading.Semaphore` fallback when `FLOWFORGE_REDIS_URL` is unset, or a Redis sorted-set distributed counter (fail-open on Redis outages) when it's set — holds the `FLOWFORGE_MAX_CONCURRENT_RUNS` limit correctly across multiple Gunicorn/Celery workers. Wired into the single `launch_run()` entry point shared by all 4 trigger paths (HTTP, webhook, scheduler, downstream dependency fan-out); returns HTTP 429 when exhausted

---

## Session — 2026-06 (SonarCloud/Scorecard remaining fixes, docs polish, production hardening) 🟢 *(COMPLETE)*

### Phase 2 — Code Quality Badges (remaining items)

#### 2.1 SonarCloud
- [x] Take a screenshot of the SonarCloud dashboard for LinkedIn post

##### 2.1f Major Code Smells (one remaining)
- [x] Add explicit `{' '}` between inline JSX elements — `Layout.tsx:103,148`, `Projects.tsx:232`, `PipelineEdit.tsx:313`, `BulkLoadEdit.tsx:186`

##### 2.1g Minor Code Smells (remaining)
- [x] Remove unnecessary type assertions (`as SomeType`) — `StepEditor.tsx:37,224,268` (config already typed); `Pipelines.tsx:92` (removed with FileReader refactor); `ReportEdit.tsx:196` (api.ts return type tightened); `ProjectSwitcher.tsx:39`, `FieldTooltip.tsx:18` (replaced with instanceof)
- [x] Fix unexpected negated conditions — `Layout.tsx:195`, `RunDetail.tsx:186`, `BulkLoads.tsx:78`
- [x] Replace `FileReader.readAsText(blob)` with `await blob.text()` — `Pipelines.tsx:88`
- [x] Replace `dict()` / `list()` constructor calls with literals `{}` / `[]` — `sftp_transfer.py:60`

#### 2.2 OpenSSF Scorecard
**Score snapshot: 6.5 / 10** (2026-06-13, commit dfd329a) — target ≥ 8.0
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
| Branch-Protection | -1 | Auth error — needs fine-grained PAT (fixed 2026-07-06, see prior session) |
| Contributors | 0 | Solo project, expected |

*Remaining open items from this snapshot (Fuzzing/Signed-Releases/CII Silver/re-running Scorecard) are tracked in `TASKS.md` Phase 10 — Medium priority, since they were still open as of this archiving pass.*

##### Critical — Code-Review (0/10)
- [x] Enable **branch protection** on `master` *(2026-06-09)*
- [x] Self-review all existing un-reviewed merged PRs *(2026-07-01)* — approved 25/41 merged PRs retroactively (all Dependabot-authored). GitHub hard-blocks self-approval via API/UI for the 16 PRs where `jagdeepvirdi` is the actual author (#22,23,25-35,38,50,51) — no workaround with a single account.

##### Medium — Pinned-Dependencies (6/10)
- [x] Hash-pinned `requirements.txt` and Dockerfile
- [x] Pin the 2 unpinned actions in `secrets-scan.yml` — `actions/checkout@v6` → hash `df4cb1c`, `trufflesecurity/trufflehog@main` → hash `84a2b33` *(2026-06-13)*
- [x] Replace bare `pip install` calls in workflows with hash-pinned requirements files *(2026-06-13)*: `requirements-build.txt` used in `publish.yml` + `release.yml`; `requirements-dev.txt` (superset: runtime + dev tools) used in `test.yml` test and sast jobs; `pip install --no-deps -e .` for editable package install

##### Medium — SAST (9/10)
- [x] CodeQL configured on all branches

##### Medium — Fuzzing (0/10)
- [x] Hypothesis property-based tests added to `tests_fuzz/` — but Scorecard only recognizes OSS-Fuzz or atheris integration (registration itself remains open — see TASKS.md)

##### Low — Signed-Releases (0/10)
- [x] `release.yml` uses `actions/attest-build-provenance` — Scorecard not picking it up (expects cosign or SLSA provenance attached as a release asset; cosign step remains open — see TASKS.md)

### Phase 3 — Documentation Polish (remaining)

#### 3.4 Getting-Started Quick Check
- [x] Run through `docs/getting-started.md` end-to-end — verify all commands and screenshots are current

### Phase 6 — Production Hardening (P1)

#### 6.1 Gunicorn Deployment Guide
- [x] Document `gunicorn --workers 4 --worker-class gevent` in RUNBOOK.md (§4a)
- [x] Explain why Celery is required when running multiple Gunicorn workers
- [x] Add Nginx reverse-proxy config example
- [x] Add systemd units for web, scheduler, and Celery worker (RUNBOOK.md §4a)

#### 6.2 SQLAlchemy Pool Tuning
- [x] Document `SQLALCHEMY_POOL_SIZE`, `SQLALCHEMY_MAX_OVERFLOW`, `SQLALCHEMY_POOL_TIMEOUT`, `SQLALCHEMY_POOL_RECYCLE` in `.env.example`
- [x] Add pool settings to `create_app()` from env vars
- [x] Add PgBouncer note in RUNBOOK.md §9

#### 6.3 Prometheus Metrics Endpoint
- [x] `GET /api/metrics` — plain-text Prometheus format (no extra dependency)
- [x] Metrics: `flowforge_runs_total{status}`, `flowforge_runs_active`, `flowforge_queue_depth`
- [x] Requires Bearer token auth; documented scrape config + Grafana PromQL in RUNBOOK.md §10

#### 6.4 Flower Dashboard (Celery Monitoring)
- [x] `flower` service added to `docker-compose.yml` with `--profile monitoring` (opt-in)
- [x] `FLOWER_BASIC_AUTH` and `FLOWER_PORT` env vars in `.env.example`
- [x] Documented in RUNBOOK.md §11 (Docker Compose + bare-metal + monitoring guide)

#### 6.5 Dependency Audit in CI
- [x] `pip-audit` already runs in GitHub Actions `test.yml` — fails on any CVE
- [x] `npm audit --audit-level=high` already runs in `frontend` job
- [x] All `requirements.txt` deps pinned to exact versions ✅

#### 6.6 Reliability & Hardening (from Codebase Review)
- [x] **[ARCH-2] Persistent Scheduler Jobstore** — APScheduler already uses `SQLAlchemyJobStore` when `FLOWFORGE_DB_URL` is set; falls back to memory with a warning. Tests confirm both paths.
- [x] **[CODE-3] Drive API Failure Visibility** — `_handle_attachments` now wraps each upload in try/except; failures fall back to direct attachment and are surfaced in Run History step logs via `warnings_out`.
- [x] **[DB-1] Prevent Invisible History** — `PipelineRun.pipeline_id` already uses `ondelete=SET NULL` (nullable); deleting a pipeline preserves all run rows with their denormalized `pipeline_name`.
- [x] **[SEC-3] SQL Sandbox Protection** — `render_sql()` added to `context.py`; warns when secret pipeline variables appear in SQL templates. `_secret_var_keys` stored in context by runner. Used in `db_query` and `report` steps for query rendering.

### Phase 7 — Observability & Admin UI

- [x] **Audit Log — link `run_id` for cross-referencing** — see the 2026-07-05/06 session above for the shipped detail; the checkbox itself lived in `TASKS.md` Phase 10 pending this archive pass.
- [x] **Step performance trends over time** — see the 2026-07-05/06 session above for the shipped detail; same note as above.

---

## Session — 2026-05-30 (Phase 8 Compliance Track + Phase 9 SSH Automation) 🟢 *(COMPLETE)*

### Phase 8 — Compliance Track (P2 — Regulated Environments)

*Required before FlowForge can be deployed in finance, healthcare, or SOC2-reviewed environments.*

#### 8.1 Data Protection
- [x] **Report file encryption at rest** — AES-256-GCM via `FLOWFORGE_ENCRYPT_OUTPUT=true`; `crypto.py` gains `encrypt_file()` / `decrypt_file_to_stream()`; `report.py` + `script_report.py` encrypt after generation; download endpoint decrypts `.enc` files transparently
- [x] **Secrets scanning in CI** — `.github/workflows/secrets-scan.yml` using TruffleHog OSS (`--only-verified --fail`) on every push and PR
- [x] **GDPR data export** — `GET /api/admin/users/{id}/export` — user profile, audit log entries, pipeline run history as JSON; Download button in Users UI
- [x] **GDPR data deletion** — `DELETE /api/admin/users/{id}?purge=true` — anonymises audit log (username → `[deleted:...]`, ip_address removed), then deletes user record; GDPR purge button in Users UI

#### 8.2 Identity Hardening
- [x] **MFA (TOTP)** — `pyotp` added to deps; DB migration `0020_mfa_sso.py` adds `mfa_secret`, `mfa_enabled`, `mfa_backup_codes` (all AES-256 encrypted); `POST /auth/mfa/enroll|confirm|disable|verify|use-backup`; Login page shows step-2 TOTP input; Settings page shows MFA enrollment card with QR code + 10 backup codes
- [x] **SSO / OAuth2 login** — `GET /api/auth/sso/google|microsoft` + callbacks; `GOOGLE_SSO_CLIENT_ID/SECRET` + `MICROSOFT_SSO_TENANT_ID/CLIENT_ID/SECRET`; `FLOWFORGE_SSO_AUTO_CREATE`; Login page shows SSO buttons when configured; token delivered via `/#sso_token=<jwt>` hash fragment
- [x] **IP allowlisting** — `FLOWFORGE_ALLOWED_IPS=10.0.0.0/8,192.168.1.0/24`; `_register_ip_allowlist()` in `app.py` registers `before_request` handler using stdlib `ipaddress`; invalid CIDRs logged as warnings and skipped

#### 8.3 Compliance Documentation
- [x] **Data flow diagram** — `docs/data-flow.md` — full inventory: data types, storage locations, transmission targets, encryption, data retention, GDPR rights, authentication security, audit events, network ports
- [x] **SAML support** *(2026-07-01)* — `python3-saml` (`sso` extra); `GET /auth/sso/saml/login`, `POST /auth/sso/saml/acs`, `GET /auth/sso/saml/metadata` in `flowforge/api/routes/sso.py`; reuses existing provider-agnostic `_find_or_create_user`, no DB migration needed (`sso_provider` already free-text); configured via `SAML_SP_ENTITY_ID`/`SAML_IDP_ENTITY_ID`/`SAML_IDP_SSO_URL`/`SAML_IDP_X509_CERT` env vars; "Sign in with SSO" button in Login page when configured

### Phase 9 — Automation Scenarios (SSH & Remote Execution)

#### 9.1 Infrastructure Support
- [x] **Implement `SSHConnection`** — new connection type to store host, port, credentials (password/key_path)
- [x] **Implement `SshCommandStep`** — execute remote commands/scripts via paramiko; capture stdout/stderr
- [x] **Implement `DbHealthCheckStep`** — industry-standard metrics (Lag, Locks, Bloat, Sessions)
- [x] **Smart Alerting Logic** — add `send_only_on_failure` toggle to pipelines to suppress routine emails
- [x] **Alembic migration** — update `ck_step_type` to include `ssh_command`, `db_health_check`, and `data_report`
- [x] **Implement `ScriptReportStep`** — generate Excel/CSV/PDF from pipeline context variables (e.g. Shell script outputs)

#### 9.2 Scenario 1: Industry-Standard Health Monitoring
- [x] **Configure Daily Health Pipeline** — importable YAML templates in `examples/` (daily digest + alerting variant)
- [x] **Standard SSH Metrics**: Load Average, Memory Usage (`free -m`), Disk I/O, and `df -h` — documented in `docs/scenarios/health-monitoring.md`
- [x] **Standard DB Metrics**: PostgreSQL (`pg_stat_activity`, cache hit ratio, replication lag) and Oracle (`v$session`, `v$sysstat`, tablespace usage) — implemented in `DbHealthCheckStep`
- [x] **Conditional Execution**: Threshold-check SSH step exits 1 on breach; `send_only_on_failure: true` suppresses routine emails — documented with example in alerting YAML template

#### 9.3 Scenario 2: Remote Script & Log Processing
- [x] **Configure Log Extraction Pipeline** — importable YAML in `examples/log-extraction-pipeline.yaml` (SSH → Report → Email, 3 steps)
- [x] **Log Handling**: `ssh_command` gains `save_output: true` — writes stdout/stderr to a `.log` file and sets `output_path`; attach alongside Excel via `{{ steps.<name>.output_path }}`

---

## Session — 2026-05-28 (GEMINI: SonarCloud 2.1a–g partial, 2.3–2.5, 3.1–3.3, 6.6, 7.1, 7.2) 🟢 *(COMPLETE)*

### Phase 1 — Celery E2E ✅ (previously archived content removed from TASKS.md)

- [x] Start Redis + `flowforge worker`, trigger a pipeline via the API/UI *(verified by `verify_celery.py`)*
- [x] Confirm worker picks up the task and writes to `ff_pipeline_runs` + `ff_step_runs`
- [x] Confirm fallback (no `FLOWFORGE_REDIS_URL`) still runs pipeline in thread mode
- [x] Confirm scheduler-triggered runs also flow through Celery correctly

### Phase 2.1 — SonarCloud (completed sub-sections)

#### 2.1a Bugs
- [x] Fix Python: `StepRun` not imported in `runs.py` — added to `from flowforge.db.models import` *(2026-05-27)*
- [x] Fix Python: Unused import `from pymysql import connections` in `connections/mysql.py` — removed *(2026-05-27)*
- [x] Fix Python: Unused exception variable `as e` in 13 `except` clauses — removed `as e` binding where unreferenced *(2026-05-27)*
- [x] Fix React hooks called conditionally — `Users.tsx` (S6440) — all 4 hooks already above the early `return` *(2026-05-27)*
- [x] Fix conditional always produces same value — `Dashboard.tsx` (S3923) — removed redundant guard *(2026-05-27)*
- [x] Fix click handlers with no keyboard listener — `Layout.tsx`, `HelpDrawer.tsx`, `PageIntro.tsx`, `EmailEdit.tsx`, `Projects.tsx` — all have `role="button"`, `tabIndex={0}`, `onKeyDown` *(2026-05-27)*

#### 2.1b Security ✅ — Security rating: A
- [x] Fix NOSONAR comment syntax — `app.py:37` resolved *(2026-05-27)*
- [x] Accept `SECRET_KEY` false positive in SonarCloud UI *(2026-05-27)*
- [x] CSRF hotspot — marked Safe (JWT Bearer auth, no cookies) *(2026-05-27)*
- [x] Hardcoded DB password — `# NOSONAR` added + marked False Positive *(2026-05-27)*
- [x] **Security rating: E → A** *(2026-05-27)*

#### 2.1c Critical Code Smells — Cognitive Complexity (Python) ✅
- [x] Reduce complexity in `steps/bulk_load.py:26` (34 → ≤15) — extracted `_validate_bulk_cfg`, `_extract_data_rows`, `_derive_csv_columns`, `_derive_line_columns` *(2026-05-27)*
- [x] Reduce complexity in `steps/bulk_load.py:369` (30 → ≤15) — same helpers *(2026-05-27)*
- [x] Verify `engine/runner.py:53` — COMPLETED (code already heavily refactored)
- [x] Verify `steps/data_load.py:19` — COMPLETED
- [x] Verify `steps/ai_analyze.py:166` — COMPLETED
- [x] Verify `steps/db_query.py:47` — COMPLETED
- [x] Verify `api/routes/pipelines.py:177,328` — COMPLETED

#### 2.1d Critical Code Smells — Cognitive Complexity (Frontend) ✅
- [x] Reduce complexity in `RunDetail.tsx:71` (32 → ≤15) — extracted `DiagnosisPanel`, `AnomalyPanel` *(2026-05-28)*
- [x] Reduce complexity in `Connections.tsx:74` (26 → ≤15) — extracted `DbConnectionCard`, `EmailProviderCard` *(2026-05-28)*
- [x] Reduce complexity in `Settings.tsx:108` (17 → ≤15) — extracted `GoogleOAuthCard`, `Microsoft365Card`, `AiOllamaCard`, `YamlCard`, `DocsCard` *(2026-05-28)*
- [x] Fix deeply nested functions in `PipelineEdit.tsx:299,306,312,318` — extracted `PipelineVariablesCard` *(2026-05-28)*

#### 2.1e Duplicated String Literals ✅
- [x] `_NOT_FOUND` constants in all relevant route files — all defined
- [x] `_CASCADE` / `_SET_NULL` / `_FF_PROJECTS_ID` / `_FF_PIPELINES_ID` constants in `db/models.py` — all defined at lines 14–17

#### 2.1f Major Code Smells (completed items)
- [x] Replace `logger.error("...: %s", e)` with `logger.exception("...")` in all `except` blocks — COMPLETED across all modules *(2026-05-28)*
- [x] Fix Flask catch-all routes to declare HTTP method — COMPLETED (using `@app.get`) *(2026-05-28)*
- [x] Fix array index used as React key — COMPLETED for most critical lists *(2026-05-28)*
- [x] Associate form labels with inputs (`htmlFor`/`id` pairs) — COMPLETED for Settings, Users, Projects, BulkLoadEdit, core StepEditor fields *(2026-05-28)*
- [x] Fix non-native interactive elements — `Layout.tsx`, `HelpDrawer.tsx`, `PageIntro.tsx`, `TopBar.tsx`, `EmailEdit.tsx`, `Projects.tsx` all updated *(2026-05-28)*
- [x] Fix nested ternary operations — COMPLETED for Connections, Dashboard, RunDetail, ReportEdit, PipelineEdit, Settings, Projects, Users *(2026-05-28)*
- [x] Fix CSS contrast ratio below WCAG AA (4.5:1) — `frontend/src/index.css:305,306` fixed *(2026-05-28)*
- [x] Replace `<div role="dialog">` with native `<dialog>` element — `HelpDrawer.tsx` updated *(2026-05-28)*

#### 2.1g Minor Code Smells (completed items)
- [x] Mark React props as `Readonly<Props>` — 18 components updated *(2026-05-28)*
- [x] Replace `window.*` with `globalThis.*` — `api.ts`, `TopBar.tsx`, `HelpDrawer.tsx`, `PipelineEdit.tsx`, `BulkLoads.tsx`, `Projects.tsx`, `RouteErrorBoundary.tsx`, `Users.tsx` *(2026-05-28)*
- [x] Replace `parseInt(x, 10)` → `Number.parseInt(x, 10)` — `StepEditor.tsx`, `BulkLoadEdit.tsx`, `Pipelines.tsx`, `PipelineEdit.tsx` *(2026-05-28)*
- [x] Use `[[` instead of `[` in shell — `tests/run_tests.sh` *(2026-05-28)*
- [x] Add default `*)` case to switch in `tests/run_tests.sh` *(2026-05-28)*

### Phase 2.3 — OpenSSF Best Practices Badge ✅
- [x] Complete the self-certification questionnaire at bestpractices.dev
- [x] Achieved **Passing** tier — project #13002 *(2026-05-27)*
- [x] **OpenSSF Best Practices** badge added to README *(PR #29)*

### Phase 2.4 — Codecov ✅
- [x] `pytest --cov=flowforge --cov-report=xml` + `codecov/codecov-action@v4` added to `test.yml`
- [x] **Coverage** badge added to README
- [x] Added `--cov-branch` for branch coverage measurement *(PR #30)*
- [x] Added `codecov.yml` with 70% project target, 60% patch target *(PR #30)*
- [x] Local coverage: **78% branch / 80% line** across 842 passing tests *(2026-05-27)*
- [x] Add `CODECOV_TOKEN` secret to GitHub repo settings

### Phase 2.5 — README Badge Row ✅
- [x] Tests + Codecov + Scorecard badges in README
- [x] SonarCloud Quality Gate badge in README
- [x] OpenSSF Best Practices badge added *(PR #29, 2026-05-27)*

### Phase 3.1 — CONTRIBUTING.md ✅
- [x] "Quick Dev Setup" section added (5-command block, login hint)
- [x] "Running Tests" one-liners for pytest and vitest

### Phase 3.2 — docs/security.md ✅
- [x] Created — covers: AES-256-GCM encryption, key rotation, JWT + revocation, RBAC roles, audit log, template sandbox, input validation, transport security

### Phase 3.3 — SECURITY.md ✅
- [x] Created at repo root — supported versions table, GitHub private advisory + email disclosure, response SLA

### Phase 4.1 — GitHub Release ✅ (previously archived content removed from TASKS.md)
- [x] CI green (842 tests passing)
- [x] Tag pushed: `v1.0.0`
- [x] GitHub Release published: https://github.com/jagdeepvirdi/flowforge/releases/tag/v1.0.0

### Phase 4.2 — Good First Issues ✅ (previously archived content removed from TASKS.md)
- [x] 5 issues created (#1–#5), labeled `good first issue` / `help wanted`

### Phase 6.6 — Audit Log `user_id` Attribution ✅
- [x] `_current_user_id()` helper added to `audit.py`; reads `g.current_user_id` (set by `require_auth`) *(2026-05-28)*
- [x] `_write_db_audit()` writes `user_id` alongside `username` to `ff_audit_log` DB table *(2026-05-28)*

### Phase 7.1 — Audit Log UI Page ✅
- [x] New `ff_audit_log` DB table + Alembic migration `6158f44dafca` *(2026-05-28)*
- [x] `AuditLog` SQLAlchemy model in `db/models.py` *(2026-05-28)*
- [x] `audit.py` updated: writes to both rotating file AND DB via `_write_db_audit()` *(2026-05-28)*
- [x] New Blueprint `flowforge/api/routes/audit.py` — `GET /api/audit-logs` (paginated + filtered) + `GET /api/audit-logs/export` (CSV stream); admin-only *(2026-05-28)*
- [x] Registered `audit_bp` in `app.py` *(2026-05-28)*
- [x] New `frontend/src/pages/AuditLog.tsx` — admin-only page at `/settings/audit`; action + user filters; pagination; CSV export *(2026-05-28)*
- [x] `App.tsx` route wired; `Layout.tsx` nav item added (admin-only) *(2026-05-28)*
- [x] `frontend/src/lib/api.ts` — `getAuditLogs()`, `exportAuditLogs()`, `AuditLogEntry` / `AuditLogResponse` types *(2026-05-28)*

### Phase 7.2 — Run Retention Policies ✅
- [x] `FLOWFORGE_RUN_RETENTION_DAYS` env var (default 90); `FLOWFORGE_AUDIT_RETENTION_DAYS` (defaults to run retention) *(2026-05-28)*
- [x] `_prune_old_runs()` + `_prune_old_audit_logs()` added to daily cleanup job in `scheduler.py` *(2026-05-28)*
- [x] `/setup/status` returns `retention.run_days` + `retention.audit_days` + `ai.model` *(2026-05-28)*
- [x] `RetentionCard` sub-component in `Settings.tsx` shows current retention values *(2026-05-28)*

### New Tests — 2026-05-28 (GEMINI)
- [x] `test_connections.py` — Oracle mock success/missing-module, MySQL mock success/missing-module, unsupported type (5 tests)
- [x] `test_pipelines.py` — clone, clone nonexistent, export, import YAML, import invalid format, import missing name (7 tests)
- [x] `conftest.py` — `ff_audit_log` added to teardown; hardcoded `testadmin` username

### New Files — 2026-05-28 (GEMINI)
- [x] `flowforge/api/routes/audit.py`
- [x] `flowforge/db/migrations/versions/6158f44dafca_add_auditlog_model.py`
- [x] `frontend/src/pages/AuditLog.tsx`
- [x] `docs/testing.md` — full 5-layer test runbook (unit / integration / frontend unit / E2E / manual)

---

## Session — 2026-05-25 (v1.0.0 GitHub Release) 🟢 *(COMPLETE)*

### Phase 4.1 — GitHub Release

- [x] CI green — fixed `test_unreadable_file_counts_as_error` (Linux: `Path.is_file()` calls `stat()` internally; moved guard inside `try` block, commit `66a8aef`)
- [x] Tag `v1.0.0` pushed to origin
- [x] GitHub Release published as Latest: https://github.com/jagdeepvirdi/flowforge/releases/tag/v1.0.0
- [x] CHANGELOG v1.0.0 entry added; footer diff links updated

### Phase 4.2 — Good First Issues

- [x] #1 "Add a dark mode toggle to the Settings page" — `good first issue`
- [x] #2 "Add SendGrid as an email provider" — `good first issue`, `help wanted`
- [x] #3 "Add Telegram notification step type" — `good first issue`, `help wanted`
- [x] #4 "Add a total run count stat card to the Dashboard" — `good first issue`
- [x] #5 "Export Run History to CSV from the Run History page" — `good first issue`, `help wanted`

---

## Session — 2026-05-25 (P0 Release Blockers — Docker + CHANGELOG + Celery E2E) 🟢 *(COMPLETE)*

### 1.2 Docker Compose Smoke Test — All Complete (commit `8a20243`)

- [x] Run `docker compose up` on a clean environment — all 5 services started cleanly
- [x] Verify API, frontend (Nginx), PostgreSQL, scheduler, Redis, and Celery worker all start cleanly — `All 5 services healthy` confirmed
- [x] Verify `flowforge db upgrade && flowforge db seed` works inside the container — 18 migrations applied, admin user seeded
- [x] Open `http://localhost:5000`, log in, create a pipeline, run it — `PipelineRun.status = "success"` confirmed via `/api/runs/<id>`

*Five fixes required for clean Docker build: Dockerfile copy of `pyproject.toml`/`README.md`/`LICENSE`/`wsgi.py`; `.dockerignore` unblocked `README.md`; `alembic` added to `requirements.txt`; `cli.py db seed` sets `role="admin"`; `Skeleton.tsx` `className` prop added for TypeScript build.*

### 1.3 CHANGELOG.md — All Complete (commit `81440d1`)

- [x] Add v1.1.0 entry — MySQL, OneDrive, SFTP, AI features, step retry, failure webhook, webhook trigger, JWT revocation, SAST
- [x] Add v1.2.0 entry — multi-user roles, user management UI, Celery wiring, responsive layout, audit attribution
- [x] Confirm CHANGELOG format matches existing v0.x / v1.0.0 entries — footer diff links updated for all versions v0.1.0 → HEAD

### 1.1 Celery E2E Verification — All 4 Items Complete (commit `23dac3f` + Test 3, script `verify_celery.py`)

- [x] Start Redis + `flowforge worker`, trigger a pipeline via the API/UI — dispatched via `run_pipeline_task.delay()`
- [x] Confirm worker picks up the task and writes to `ff_pipeline_runs` + `ff_step_runs` — polled to `status = success`, StepRun checked
- [x] Confirm fallback (no `FLOWFORGE_REDIS_URL`) still runs pipeline in thread mode — `_use_celery()` returns `False`, thread executor confirmed
- [x] Confirm scheduler-triggered runs flow through Celery — Test 3: `_run_pipeline_job()` called directly (exact APScheduler entry point) with `scheduler._app` set; `PipelineRun.triggered_by='scheduler'`, `status='success'`, 1 StepRun written

---

## Session — 2026-05-25 (Celery Wiring + Multi-User Sprint Close-out) 🟢 *(COMPLETE)*

### Celery Task Queue — Wiring Complete

- [x] **`celery_app.py` rewrite** — Single module-level `celery` instance with `FlaskTask` base class that auto-pushes Flask app context on every task. Lazy `_get_app()` creates the Flask app once in worker processes; `init_celery(app)` binds the web-server app. No double `create_app()` call.
- [x] **`tasks.py` fix** — Removed `create_app()` inside the task function; Flask context now provided by `FlaskTask.__call__`.
- [x] **`launcher.py` → Celery dispatch** — `_use_celery()` returns `True` when `FLOWFORGE_REDIS_URL` is set; dispatches via `run_pipeline_task.delay(pipeline_id, triggered_by, run_id)`; thread-based fallback retained for zero-Redis deployments. `_semaphore` not present in launcher (concurrency handled by Celery worker `--concurrency`).
- [x] **`create_app()` wired** — Calls `init_celery(app)` when `FLOWFORGE_REDIS_URL` is configured; stores celery instance on `app.extensions['celery']`.
- [x] **`flowforge worker` CLI command** — `celery.worker_main()` with `--concurrency` and `--loglevel` options; validates Redis URL before starting.
- [x] **`.env.example`** — `FLOWFORGE_REDIS_URL` section added (blank by default; threading fallback when unset).

### Multi-User Sprint — MU-1 through MU-7 (all complete)

- [x] **MU-1 · JWT carries `user_id` + `/api/auth/me`** — `uid: user.id` in JWT payload; `require_auth` sets `g.current_user_id`; `GET /api/auth/me` returns `{ id, username, role }`; rejects legacy tokens without `uid`; 3 tests.
- [x] **MU-2 · User management API** — `POST /api/users`, `GET /api/users`, `PATCH /api/users/{id}`, `DELETE /api/users/{id}` (admin only); `POST /api/auth/change-password` (any user, min 8 chars); self-protection guards (cannot demote or delete self); 22 tests.
- [x] **MU-3 · `@require_role` guards on all write routes** — pipelines (create/update/delete/run/clone/import/webhook-tokens), reports, emails, recipients, runs (`cancel`), providers, connections all guarded; 21 RBAC spot-check tests; all 742 suite tests passing.
- [x] **MU-4 · Audit log username attribution** — `_current_user()` in `audit.py` reads `g.user_token['sub']` and appends `by=<username>` to every log entry. *(Optional UUID follow-up remains in Near-Term Pending.)*
- [x] **MU-5 · Frontend role context** — `Role` type + `CurrentUser` interface in `types.ts`; `getMe()` in `api.ts`; `useAuth` store extended with `user: CurrentUser | null` + `setUser` / `clearToken` also clears user; `useCurrentUser()` hook; `AppBootstrap` rehydrates role on every page load/refresh; Login calls `getMe()` immediately after token.
- [x] **MU-6 · User management UI** — `/settings/users` page (admin-only, redirects non-admins); users table with "(you)" badge, inline role select, delete button; "Add User" modal; "Change Password" card in Settings; admin-only nav item via `useCurrentUser()`; 24 frontend tests passing.
- [x] **MU-7 · Frontend role-based visibility** — Connections, Providers, Pipelines, Dashboard, Reports, Emails, Recipients all gate write UI (create/edit/delete/run) behind `role !== 'viewer'` / `role === 'admin'`; uses `useCurrentUser().role` — no extra API calls; 24 frontend tests passing.

### Critical Action Items — All Resolved

- [x] **P0 · Mobile/Responsive layout** — `@media` breakpoints at 640px, 1024px, 1200px; responsive sidebar + card layout.
- [x] **P1 · Frontend inline style refactor** — `style={{}}` replaced with Tailwind across `Dashboard.tsx`, `PipelineEdit.tsx`, `Layout.tsx`.
- [x] **P1 · Task Queue (Celery)** — Scaffolded + fully wired. `launcher.py` dispatches via Celery when Redis configured.
- [x] **P1 · RBAC** — All write routes guarded via `require_role`; frontend visibility gated per role (MU-3 + MU-7).
- [x] **Audit log user attribution** — `by=<username>` on every entry.

---

## Session — 2026-05-25 (Gemini Work Verified + Committed) 🟢 *(COMPLETE)*

*Gemini-authored changes verified against code, committed, and closed out.*

- [x] **P0 · Mobile/Responsive layout** — `@media` breakpoints at 640px, 1024px, 1200px in `frontend/src/index.css`; responsive sidebar collapse and card reflow. Committed `9ff50ec`.
- [x] **P1 · Frontend inline style refactor** — `Dashboard.tsx`: 12 dynamic-only `style={{}}` remain (bar colors, skeleton widths); `PipelineEdit.tsx`: 0 remaining; `Layout.tsx`: 5 remaining (dynamic). Committed `9ff50ec`.
- [x] **v2 · Celery/Redis scaffolding** — `flowforge/celery_app.py`, `flowforge/tasks.py` (`run_pipeline_task`), Redis service + worker service in `docker-compose.yml`, `celery[redis]==5.4.0` in `requirements.txt`. Committed `d6272d1`. ⚠️ `launcher.py` wiring to Celery is the one remaining step.

*Not done despite Gemini review claiming completion:*
- **Audit log `user_id` (MU-4)** — `audit.py` does NOT read `g.current_user_id`; no audit UI page exists. Still open in MU-4.

---

## Session — 2026-05-25 (TASKS.md Audit — Recovered Completed Items) 🟢 *(COMPLETE)*

*Items found already done in code but still listed as pending in TASKS.md.*

- [x] **Email Preview (P0)** — `GET /api/email-configs/{id}/preview` endpoint in `emails.py`; preview modal in `EmailEdit.tsx`. Verified in code 2026-05-25.
- [x] **Engine Decoupling (P1)** — `flowforge/engine/launcher.py` extracted; `pipelines.py` now calls `launcher.launch_run`. Done via commit `0e7a29c`.
- [x] **MySQL / MariaDB support** — `flowforge/connections/mysql.py`; migration `0017` adds `mysql` to DB type constraint; frontend Connections page supports MySQL. (FEAT-1)
- [x] **Step retry with configurable backoff** — `retry_count` (0–10) and `retry_delay_seconds` (0–3600) in `engine/runner.py:93-114`; per-step config in `StepEditor.tsx`. (FEAT-5)
- [x] **Pipeline YAML import/export from UI** — Import (file picker) and Export (download) buttons in `Pipelines.tsx`; `POST /api/pipelines/import` + `GET /api/pipelines/{id}/export` endpoints. (FEAT-4)
- [x] **APScheduler PostgreSQL jobstore** — `SQLAlchemyJobStore` wired in `scheduler.py`; jobs survive scheduler restarts; logged at startup. Commit `9f423ba`.
- [x] **Graceful shutdown** — `flowforge/engine/shutdown.py`: active-run registry, `_drain(timeout)`, `SIGTERM` handler, `atexit` hook; `TimeoutStopSec=90` in systemd units. (SCORE-7)
- [x] **Audit log rotation** — `RotatingFileHandler(10 MB, 5 backups)` in `audit.py`; `LOG_LEVEL` env var controls verbosity. (SCORE-4)
- [x] **Structured audit log (stdout)** — `_JsonStdoutHandler` in `audit.py`; active when `FLOWFORGE_AUDIT_STDOUT=true`; emits ISO-8601 JSON lines. (FEAT-7)
- [x] **SAST + dependency audit in CI** — `bandit -r flowforge/` (Python SAST) + `npm audit --audit-level=high` (frontend) in `.github/workflows/test.yml`. Commit `8fd9507`.

---

## Session — 2026-05-25 (Frontend Test Coverage) 🟢 *(COMPLETE)*

- [x] **FEAT-9 · Frontend test coverage** — 24 unit tests (Vitest + React Testing Library) across 5 files; 5 E2E spec files (Playwright) covering login, dashboard, pipelines CRUD, run history, and connections. Global setup/teardown with auth state reuse. Fixed 2 pre-existing broken test mocks (Dashboard, Pipelines). Completed 2026-05-25.

---

## Session — 2026-05-25 (Code Review Bug Track + AI Features + SFTP + OneDrive) 🟢 *(COMPLETE)*

### Code Review 2026-05-25 — Phase 2 (FEAT-1 through FEAT-8)

- [x] **FEAT-1 · MySQL / MariaDB support** — `connections/mysql.py`: full `BaseConnection` implementation using PyMySQL. `connections/factory.py` dispatches `'mysql'` type. Migration `0017` adds `'mysql'` to `ck_db_connection_type`. `connections.py` test-raw endpoint supports MySQL. `Connections.tsx` adds MySQL option with auto-port (3306). `pyproject.toml` adds `[mysql]` extra.
- [x] **FEAT-2 · Docker Compose one-command setup** — Existing `docker-compose.yml` refactored: renamed to `flowforge`, Oracle service extracted to `docker-compose.oracle.yml` override (users run `docker compose -f docker-compose.yml -f docker-compose.oracle.yml up`). Base stack is now frictionless: `docker compose up`.
- [x] **FEAT-3 · Pipeline clone** — `POST /api/pipelines/<id>/clone` in `pipelines.py`: copies pipeline + steps + variables with `(Copy)` name suffix, clears schedule, sets `enabled=False`. `Pipelines.tsx` adds Clone button (Copy icon) in the row action bar.
- [x] **FEAT-4 · Pipeline YAML import/export** — `GET /api/pipelines/<id>/export` returns YAML; `POST /api/pipelines/import` accepts YAML via JSON body or multipart file upload. Masked secrets (`***`) are skipped on import. Frontend: Import (file picker) and Export (download) buttons in `Pipelines.tsx`.
- [x] **FEAT-5 · Step retry with configurable backoff** — `engine/runner.py`: reads `retry_count` (0–10) and `retry_delay_seconds` (0–3600) from step config JSONB. Logs attempt N/total on each retry. `StepEditor.tsx`: Retries + delay inputs added to the step header controls bar.
- [x] **FEAT-6 · Failure webhook notification** — `db/models.py`: `on_failure_webhook_url VARCHAR(500)` on `Pipeline`. Migration `0016`. `engine/runner.py`: `_fire_failure_webhook()` POSTs JSON `{pipeline_name, run_id, error_step, error_message, triggered_by}` on failure; 10s timeout, errors logged not raised. `PipelineEdit.tsx`: Failure webhook URL input added.
- [x] **FEAT-7 · Structured audit stdout** — `audit.py`: added `_JsonStdoutHandler` that emits ISO-8601 JSON lines. Active when `FLOWFORGE_AUDIT_STDOUT=true`. File handler suppressible with `FLOWFORGE_AUDIT_FILE=false`.
- [x] **FEAT-8 · Input length validation** — `api/validators.py`: `validate_pipeline`, `validate_report`, `validate_email_config`, `validate_recipient_group`, `validate_connection` helpers. Wired into create + update handlers in `pipelines.py`, `reports.py`, `emails.py`, `recipients.py`, `connections.py`.

### Code Review 2026-05-25 — Phase 1 (CR-6 through CR-14)

- [x] **CR-6 · Oracle pool re-created on every step** — `connections/oracle.py`: added module-level `_pools` registry identical to `postgres.py`. Key is `(host, port, service_name, user, password_hash)`. Password hashed with SHA-256 (first 16 hex chars). Logs "Created Oracle pool" on first use.
- [x] **CR-7 · `_run_dict` defined in two places** — Extracted canonical `run_dict()` and `step_run_dict()` to new `flowforge/api/serializers.py`. Both `runs.py` and `pipelines.py` now import from there. The `pipelines.py` copy (which was missing `error_step`/`error_message`) is deleted.
- [x] **CR-8 · N+1 queries on Dashboard** — Added `GET /api/dashboard/summary` in `runs.py`: fetches all pipeline IDs then last 14 runs per pipeline in a single ordered query, grouped in Python. Frontend `PipelineCard` now accepts `runs` as a prop; `Dashboard` uses one `getDashboardSummary` query with per-run polling when any run is active.
- [x] **CR-9 · No rate limiting on manual trigger** — Added `@limiter.limit('10 per minute')` to `trigger_run()` in `pipelines.py`.
- [x] **CR-10 · Self-import in `email_step.py`** — Removed `from flowforge.steps.email_step import _build_inline_provider`; calls `_build_inline_provider(inline)` directly.
- [x] **CR-11 · Inconsistent `DateTime(timezone=True)`** — Fixed `RecipientGroup.created_at`, `DbConnection.created_at`, `EmailConfig.created_at/updated_at` in `db/models.py`. Migration `0015_datetime_timezone.py` alters the four columns to `TIMESTAMPTZ`.
- [x] **CR-12 · Oracle cursor not closed** — `api/routes/connections.py:149` now uses `with conn.cursor() as cur: cur.execute(...)`.
- [x] **CR-13 · Silent exception in `_get_last_success_ts`** — `engine/runner.py`: bare `except Exception` changed to `except Exception as e: logger.warning(...)`.
- [x] **CR-14 · New Anthropic client per AI call** — `steps/ai_analyze.py`: module-level `_anthropic_client` singleton initialised on first use; re-created only if `ANTHROPIC_API_KEY` changes. `_call_claude()` now calls `_get_anthropic_client()`.

### Code Review 2026-05-25 — Phase 0 (CR-1 through CR-5)

- [x] **CR-3 · `_SafeEnv` blocklist is inherently incomplete** — `engine/context.py`: replaced single-mode blocklist with dual-mode `_SafeEnv`. When `FLOWFORGE_TEMPLATE_ENV_VARS=VAR1,VAR2` is set only those vars are accessible (allowlist mode). Without it, falls back to blocklist with `FLOWFORGE_JWT_SECRET` added. Documents the new env var in the module docstring.
- [x] **CR-4 · Oracle `service_name` field inconsistency in bulk_load** — `steps/bulk_load.py`: both `_open_raw_connection()` and `_load_sqlloader()` now use `conn_cfg.get('service_name') or conn_cfg.get('database', '')`, matching `connections/factory.py`.
- [x] **CR-5 · PostgreSQL pool key excludes password** — `connections/postgres.py`: pool registry key extended to `(host, port, database, user, password_hash)` using first 16 hex chars of SHA-256. Two rows with the same host/db/user but different passwords now get separate pools.

- [x] **CR-1 · SQL injection via procedure name** — `steps/db_procedure.py` and `connections/oracle.py` both f-string interpolated the procedure name without validation. Added `validate_identifier` import to `db_procedure.py` and call it before any SQL is built; a bad name now fails immediately with a `StepResult` error before touching the DB.
- [x] **CR-2 · SFTP AutoAddPolicy — silent MITM risk** — implemented `FLOWFORGE_SFTP_STRICT_HOSTKEYS=true` flag in `steps/sftp_transfer.py`. When set, uses `paramiko.RejectPolicy()`; rejects unknown hosts with a clear error including the exact `ssh-keyscan` command needed to add the key. Default remains `AutoAddPolicy` (TOFU) for backward compatibility. Added `strict_hostkeys=` to the debug log line.

### Bug Fix Track — Code Review 2026-05-24 (BUG-1 through BUG-14)

- [x] **BUG-1: `bulk_load.py:201` — `_resolve_connection` crashes at runtime** — replaced broken `.items()` dict-comprehension with `decrypt_config(row.config)`.
- [x] **BUG-2: `bulk_load.py:281,343` — SQL injection via CSV column headers** — added `validate_identifier()` call on every mapped column name in both `_load_python_fallback` and `_load_postgres_copy`.
- [x] **BUG-3: `bulk_load.py:418` — Oracle password exposed in process list** — credentials written to a `load.par` tempfile (chmod 600); `sqlldr parfile=…` used instead of inline `user/pass@dsn` arg; tempdir cleaned up in finally block.
- [x] **BUG-4: DB constraint / step type mismatch** — migration 0011 adds `data_load` and `bulk_load` to `ck_step_type`; removes `ai_analyze` (no implementation yet). Model updated to match.
- [x] **BUG-5: `context.py:47` — Jinja2 is not sandboxed + full `os.environ` in context** — switched to `SandboxedEnvironment`; `ctx['env']` now uses `_SafeEnv` proxy that blocks credential vars (`FLOWFORGE_SECRET_KEY`, `FLOWFORGE_PASSWORD`, `*_CLIENT_SECRET`, etc.).
- [x] **BUG-6: `audit.py:20` — Audit log silenced when `LOG_LEVEL=WARNING`** — removed `_LEVEL` variable; `_get_logger()` now hardcodes `logging.INFO` so audit events are always written regardless of `LOG_LEVEL`.
- [x] **BUG-7: `runs.py:93` — No path containment check on file download** — `abs_path` and `output_root` are both `.resolve()`d; a 403 is returned if `abs_path` does not start with `output_root + os.sep`.
- [x] **BUG-8: `context.py:115` — Pipeline variables silently overwrite built-ins** — added `_BUILT_IN_VAR_KEYS` frozenset; `build()` logs a `WARNING` listing any collision before applying `ctx.update(pipeline_vars)`.
- [x] **BUG-9: `app.py` — No `MAX_CONTENT_LENGTH`** — `app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024` added in `create_app()`.
- [x] **BUG-10: `scheduler.py:97` — Dead function `_load_pipeline_jobs`** — function removed; `check_scheduler.py` section 7 updated to query the DB directly.
- [x] **BUG-11: `models.py:273` — `TokenBlocklist` grows unbounded** — added `_prune_token_blocklist()` to `scheduler.py`; called from the existing daily `_cleanup_job`. Deletes all rows where `expires_at < NOW()` inside an app context.
- [x] **BUG-12: `steps.py:88` — Step reorder magic number can violate unique constraint** — replaced `999999` with `-old_order` (guaranteed negative, never collides with a positive step order); added `.with_for_update()` to the occupant query to prevent concurrent swap races.
- [x] **BUG-13: `bulk_load.py:343` — Delimiter injected into COPY SQL string literal** — `delimiter` is validated in `BulkLoadStep.run()` before any SQL is constructed: must be exactly one printable character and not a quote or backslash.
- [x] **BUG-14: `report.py:38` — Excel template path unrestricted** — added `_resolve_template_path()` helper: joins `raw` against `FLOWFORGE_TEMPLATE_DIR` (default `./templates`), resolves both, and raises `ValueError` if the result escapes the root.

### AI Features — AI-1 through AI-6 (all shipped)

- [x] **[AI-1] AI Chart Generator** — "Visualize" button on the Report Preview panel. Sends column names + up to 50 rows to Ollama; Ollama returns a JSON chart config `{ type, x, y, title }`. FlowForge renders it immediately using Recharts. Supported types: bar, line, area, pie, scatter. New Flask endpoint `POST /api/ai/chart-config`; new `ChartPreview` React component.
- [x] **[AI-2] SQL Explainer** — "Explain" button in the Report Designer SQL editor header. Sends SQL text only to Ollama via `POST /api/ai/query` (`task: explain`); returns structured plain-text summary (tables/joins, filters, aggregations, potential issues). Dismissible panel below SQL editor.
- [x] **[AI-3] SQL Optimizer** — "Optimize" button alongside AI-2. Ollama rewrites the query (JSON mode for reliable SQL extraction). Side-by-side diff panel: original (red tint) vs suggested (green tint). Accept replaces textarea; Dismiss closes panel.
- [x] **[AI-4] Pipeline Failure Diagnosis** — "Explain this error" button in the Run Detail Logs tab, shown per failed step. Sends `step_type + error + logs` to Ollama via `POST /api/ai/query` (`task: diagnose`). Returns 2-4 sentence plain-English cause + fix. Diagnosis panel is per-step, dismissible, shows "via Ollama" label.
- [x] **[AI-5] Data Profiler** — "Summarise" button in the TopBar (visible after preview runs). One-time opt-in banner per session. Calls `POST /api/ai/data-profile`; returns a 3-5 sentence narrative (structure, value ranges, nulls, outliers, key suspicion). Profile card dismissible, clears on query re-run, consent persists for session.
- [x] **[AI-6] Run History Anomaly Alerts** — Statistical outlier detection on `rows_affected` and `duration_ms` per step across the last 30 runs. When a step result is >2σ outside normal range, shows a warning badge in Run Detail. Ollama optionally generates a one-sentence narrative. Statistical layer + Ollama narrative both shipped.

### Storage Steps (shipped 2026-05-24/25)

- [x] **SFTP transfer step** — `sftp_transfer` step type; download (single file or directory with glob pattern) and upload; password or private-key auth (RSA/ECDSA/Ed25519/DSS); `create_remote_dirs`, `overwrite`, `pattern` options; migration 0014 adds `sftp_transfer` to `ck_step_type`; `pip install 'flowforge-io[sftp]'`
- [x] **OneDrive / SharePoint upload step** — `onedrive_upload` step type (Graph API, MSAL); chunked upload for files > 4 MB; `make_shareable=True` returns anonymous view URL. Smart attachment in `email` step prefers OneDrive when `onedrive_folder_id` is set on the email config. Migration 0012 adds the column.

### Platform (shipped 2026-05-24)

- [x] **AI analyze step** — `flowforge/steps/ai_analyze.py`; Ollama + Claude providers; `{{ ai_summary }}` injected to top-level context; `{{ steps.<name>.ai_summary }}` in step context; `max_rows` cap; migration 0013 adds `ai_analyze` to `ck_step_type`

---

## Session — 2026-05-24 (Score 8.5+ Track, Tests complete) 🟢 *(COMPLETE)*

### Score 8.5+ Track — Tests

- [x] **[SCORE-6] Report generation end-to-end test** — `tests/test_report_e2e.py`: CSV + Excel full-chain tests against real test DB (SQL → ReportStep → file on disk), zero-rows edge case, output_path validation. *Tests +0.5.*
- [x] **[SCORE-11] Bulk load step tests** — Already complete: `tests/test_bulk_load_step.py` (27 tests) + `tests/test_bulk_load_configs.py` (14 tests). Covers normal load, skip/fail on no files, footer stripping, replace mode, column mapping, archive, config resolution, runner context propagation. *Tests +0.5.*

---

## Session — 2026-05-24 (Score 8.5+ Track) 🟢 *(COMPLETE)*

### New Issues — Found in 2026-05-23 Review (all resolved)

- [x] **[NEW-1] Email preview modal** — API endpoint `GET /email-configs/{id}/preview` + preview button in `EmailEdit.tsx`. Documented in CLAUDE.md; never built. P0.
- [x] **[NEW-2] SMTP send timeout** — `smtplib.SMTP(host, port, timeout=30)` missing in `smtp.py`; slow servers block pipeline threads indefinitely. P1.
- [x] **[NEW-3] Audit log completeness** — `flowforge/audit.py` logs login and pipeline events but NOT config changes (connections, providers), email sends, or report exports. P1.
- [x] **[NEW-4] JWT token revocation** — stolen token valid 24h; add `jti` claim + server-side blocklist + `/auth/logout` endpoint. P1.
- [x] **[NEW-5] Table-name injection guard** — `db_query.py` and `bulk_load.py` interpolate `output_table` into raw SQL; validate against safe identifier regex `^[a-zA-Z_][a-zA-Z0-9_.]*$`. P1.
- [x] **[NEW-6] DB factory vs check constraint mismatch** — constraint allows `mysql`, `mssql`, `snowflake` but factory raises at runtime; either remove from constraint or implement. P2.
- [x] **[NEW-7] Index on `ff_pipeline_variables(pipeline_id)`** — full table scan on every pipeline run. P2.
- [x] **[NEW-8] Frontend E2E tests (Playwright)** — no coverage of the full login → create → run → history journey. P2.
- [x] **[NEW-9] Production deployment guide** — `wsgi.py` exists but no Gunicorn + Nginx setup documented. P2.
- [x] **[NEW-10] Webhook / API trigger** — `POST /pipelines/{id}/trigger?token=...` for external system integration. P2.

### Score 8.5+ Track — Frontend

- [x] **[SCORE-1] Loading skeletons** — added `<Sk />` shimmer component (`Skeleton.tsx`); shape-matched loading states on `Dashboard.tsx`, `RunHistory.tsx`, `PipelineEdit.tsx`, `Connections.tsx`, `BulkLoads.tsx`. *Frontend +1.0*
- [x] **[SCORE-2] React Hook Form + Zod migration** — migrated `EmailEdit.tsx` and `ReportEdit.tsx` to `useForm<Schema>()` + `zodResolver`; cross-field validation with `.refine()` on recipients; `Controller` for chip-input arrays; `isSubmitting` replaces `saving` state. *Frontend +0.5, Code Quality +0.5*
- [x] **[SCORE-3] CSS token variables** — added 7 new tokens to `index.css` (`--text-3`, `--failure-text`, `--success-text`, `--running-text`, `--accent-text`, `--bg-code`, `--surface-hover`); bulk-replaced all design-token hex strings across 23 TSX files; preserved raw hex in `DB_COLORS` (template-literal alpha-suffix) and `PROJECT_COLORS` (DB-stored, equality-compared). *Frontend +0.5*
- [x] **[SCORE-10] React error boundaries** — enhanced `RouteErrorBoundary` with `componentDidCatch` logging, `label` prop, collapsible stack-trace detail, "Reload page" + "Try again" buttons; global boundary in `main.tsx`; step-editor boundary in `PipelineEdit.tsx` around `<DndContext>`. *Frontend +0.5, Architecture +0.25*

### Score 8.5+ Track — DevOps

- [x] **[SCORE-4] Log rotation for `audit.log`** — replaced `FileHandler` with `RotatingFileHandler(10 MB, 5 backups, utf-8)`; `LOG_LEVEL` env var controls verbosity in `audit.py`, `cli.py`, and `create_app()`; documented in `.env.example`. *DevOps +0.5*
- [x] **[SCORE-5] Fix `alembic.ini` hardcoded database URL** — `sqlalchemy.url` was already absent from baseline; added explanatory comment block to `alembic.ini`; removed silent `flowforge:flowforge` fallback from `env.py` `_db_url()` — now raises `RuntimeError` with actionable message if `FLOWFORGE_DB_URL` is unset. *DevOps +0.5*

### Score 8.5+ Track — Architecture

- [x] **[SCORE-7] Graceful shutdown — drain in-flight pipeline runs** — new `flowforge/engine/shutdown.py`: active-run registry (`register_run`/`unregister_run`), `_drain(timeout)` polling loop, `_cancel_stuck_runs()` DB UPDATE, `install_handler(app)` SIGTERM handler + `atexit` hook, `graceful_exit(app)` for Ctrl+C path. Integrated into `runner.py` (try/finally), `cli.py` `web` and `schedule` commands. `TimeoutStopSec=90` added to both systemd units in `deployment.md`. `FLOWFORGE_SHUTDOWN_TIMEOUT=60` in `.env.example`. *Architecture +0.5*

### Score 8.5+ Track — Database

- [x] **[SCORE-8] Deleted-pipeline run history visibility** — `ff_pipeline_runs.pipeline_id` FK was already `ON DELETE SET NULL` in baseline (no migration needed); `PipelineRun.pipeline_id` typed as `string | null` in `types.ts`; "Deleted pipelines" filter option added to `RunHistory.tsx` (client-side `__deleted__` sentinel, suppressed from API query); `(deleted)` badge shown inline when `pipeline_id === null`. *Database +0.5*

### Pipeline Features (shipped 2026-05-23)

- [x] **Pipeline variables** — Variables card in Pipeline Builder; key/value/secret pairs; `{{ var_key }}` and `{{ vars.var_key }}` in all step configs; secrets encrypted at rest and masked in UI.
- [x] **Bulk file loader step (`bulk_load`)** — Directory scanning, `file_prefix`/`file_prefix_exclude`, PostgreSQL `COPY FROM STDIN`, chunked Python fallback, footer row stripping, archive-after-load, `on_no_files` behaviour, Bulk Loads UI page.

---

## Session — 2026-05-23 (v1.0.0) 🟢 *(COMPLETE)*

### Multi-Project Support

**Goal:** Organize all FlowForge resources (pipelines, reports, email configs, recipient groups) into named projects — so teams can manage Finance, HR, Marketing Ops, etc. in one FlowForge instance without everything living in a flat list.

**Design decisions:**
- `db_connections` and `email_providers` stay **global** — infrastructure configured once, shared across projects
- A **"Default"** project is seeded on migration — all existing rows assigned to it, zero data loss
- Project switcher lives in the topbar beside the breadcrumb (moved from sidebar 2026-05-23)
- "All Projects" admin view for cross-project run history

#### Phase 1 — Database & Backend
- [x] `flowforge/db/models.py` — add `Project` model: `id`, `name`, `description`, `color`, `created_at`
- [x] `flowforge/db/models.py` — add `project_id` FK (nullable → non-null after backfill) to `Pipeline`, `ReportConfig`, `EmailConfig`, `RecipientGroup`
- [x] `flowforge/db/migrations/` — Alembic migration `0006_projects.py`: create `projects` table, add `project_id` columns, seed "Default" project, backfill all existing rows
- [x] `flowforge/api/routes/projects.py` — CRUD endpoints: `GET /projects`, `POST /projects`, `PATCH /projects/:id`, `DELETE /projects/:id`
- [x] All existing list/get routes — filter by `project_id` query param (e.g. `GET /pipelines?project_id=...`)
- [x] `flowforge/api/routes/runs.py` — "All Projects" run history: `GET /runs` with optional `project_id` filter

#### Phase 2 — Frontend: Project Switcher & Projects Page
- [x] `frontend/src/components/shared/ProjectSwitcher.tsx` — dropdown: current project name, list of all projects, "All Projects" link, "+ New Project" action; compact prop for topbar use
- [x] `frontend/src/lib/store.ts` (Zustand) — add `activeProjectId` global state; persisted to `localStorage`
- [x] `frontend/src/pages/Projects.tsx` — projects list as cards: name, color tag, pipeline count, last run status; create/edit/delete actions
- [x] `frontend/src/lib/api.ts` — pass `project_id` on all scoped API calls (pipelines, reports, email, recipients)

#### Phase 3 — Frontend: Scoped Pages & All Projects View
- [x] `frontend/src/pages/Dashboard.tsx` — scope pipeline cards to active project; show project name in header
- [x] `frontend/src/pages/PipelineEdit.tsx` — set `project_id` on create
- [x] `frontend/src/pages/ReportEdit.tsx` — scope to active project on create
- [x] `frontend/src/pages/EmailEdit.tsx` — scope to active project on create; recipient groups filtered by project
- [x] `frontend/src/pages/Recipients.tsx` — scope to active project on list and create
- [x] `frontend/src/pages/RunHistory.tsx` — scope to active project by default; pipeline filter list scoped to active project

#### Phase 4 — Tests & Migration Safety
- [x] `tests/test_projects.py` — CRUD for projects; confirm resources are correctly scoped per project
- [x] `tests/test_projects.py` — confirm pipelines/groups created without `project_id` are assigned to Default project
- [x] `tests/test_projects.py` — confirm `GET /pipelines?project_id=X` returns only X's pipelines, not cross-project leakage
- [x] Manual migration test: N/A — DB is clean (no pre-existing data to backfill)

---

### Query Results in Email (`db_query` → `email` data display)

**Goal:** When a `db_query` step runs (e.g. a post-load audit query returning success/fail counts), subsequent `email` steps can display those results inside the email body — without the user writing raw Jinja2.

**How it works end-to-end:**
1. User ticks **"Capture rows for email"** on the `db_query` step config and sets a row limit (default 100).
2. The step runner stores the result rows in `context['steps']['step_name']['rows']` (list-of-dicts) and pre-renders a styled `context['steps']['step_name']['table_html']` string.
3. In the email body editor, a new **"Insert step data"** button lists all `db_query` steps in the pipeline that have capture enabled. User picks one and a display format → the correct Jinja2 snippet is inserted into the body.
4. Email renders: `{{ steps.load_check.table_html }}` expands to an HTML table inside the sent email.

**Display format presets:**
| Preset | Variable inserted | Output |
|---|---|---|
| HTML table | `{{ steps.NAME.table_html }}` | Styled `<table>` with all columns |
| Key-value list | `{{ steps.NAME.kv_html }}` | `<dl>` — first row as label:value pairs (good for single-row summaries) |
| Counts only | `{{ steps.NAME.rows_affected }}` | Plain number — same as existing `rows_affected` |
| Custom Jinja2 | `{% for row in steps.NAME.rows %}{{ row.status }}: {{ row.count }}<br>{% endfor %}` | User writes own markup with column-name access |

**No migration required** — `capture_rows` and `row_limit` are stored in `pipeline_steps.config` JSONB; `table_html`/`kv_html` live only in the in-memory pipeline context.

#### Phase 1 — Backend Core
- [x] `flowforge/steps/base.py` — add `rows: list[dict]`, `table_html: str`, `kv_html: str` fields to `StepResult`
- [x] `flowforge/steps/db_query.py` — read `capture_rows: bool` (default `False`) and `row_limit: int` (default 100) from step config
- [x] `flowforge/steps/db_query.py` — implement `table_html` renderer: inline-styled `<table>` (no external CSS, email-client safe), HTML-escaped
- [x] `flowforge/steps/db_query.py` — implement `kv_html` renderer: `<dl>` from first row only (single-row summary queries), HTML-escaped
- [x] `flowforge/steps/db_query.py` — when `capture_rows=True`, use `execute_query_with_columns`, zip into list-of-dicts, store rows + rendered HTML in StepResult
- [x] `flowforge/engine/runner.py` — add `'rows'`, `'table_html'`, `'kv_html'` to `context['steps'][step.name]` (same pattern as `files_found` etc.)

#### Phase 2 — Frontend: Step Config
- [x] `frontend/src/components/pipeline/StepEditor.tsx` — add **"Capture rows for email"** toggle (`capture_rows`) to the `db_query` form
- [x] `frontend/src/components/pipeline/StepEditor.tsx` — show **"Row limit"** number input (1–1000, default 100) when toggle is on
- [x] `frontend/src/components/pipeline/StepEditor.tsx` — add hint text showing the exact `{{ steps.NAME.table_html }}` snippet for the step name

#### Phase 3 — Frontend: Email Designer
- [x] `frontend/src/components/pipeline/StepEditor.tsx` — email step shows **"Query data"** section listing upstream `db_query` steps with `capture_rows=true`, with copyable snippets for `table_html`, `kv_html`, and custom loop
- [x] `frontend/src/pages/EmailEdit.tsx` — added `{{ steps.step_name.table_html }}`, `{{ steps.step_name.kv_html }}`, and `{% for row in steps.step_name.rows %}` to the Available Variables reference card

#### Phase 4 — Help Content & Tests
- [x] `frontend/src/lib/helpContent.ts` — added `capture_rows` / `row_limit` hints to `db_query` step tips
- [x] `frontend/src/lib/helpContent.ts` — added embed-query-data hint to `email` step tips
- [x] `tests/test_db_query_capture.py` — `capture=True`: rows stored, HTML rendered, `row_limit` respected; `capture=False`: rows empty, no HTML rendered; HTML renderer unit tests incl. XSS escaping
- [x] `tests/test_runner.py` — assert `rows`, `table_html`, `kv_html` keys are in `context['steps']` for both capturing and non-capturing steps

---

## Session — 2026-05-22 (v0.1.4) 🟢 *(COMPLETE)*

### Bug Fixes
- [x] **Email provider `test()` missing** — `AttributeError` on every provider test. Added `test()` to base class and all three providers: Gmail (token refresh), SMTP (connect + login), M365 (MSAL token). (`flowforge/email_providers/base.py`, `gmail.py`, `smtp.py`, `microsoft365.py`)
- [x] **Gmail test scope error** — `getProfile` requires `gmail.readonly`, exceeding the `gmail.send` scope. Replaced with a token refresh call. (`flowforge/email_providers/gmail.py`)
- [x] **Test error message silently discarded** — Connections UI showed only "FAILED" with no detail. Error now captured and displayed under the Failed badge; also logged to browser console. (`frontend/src/pages/Connections.tsx`)
- [x] **Quick-attach invalid Jinja2 for step names with spaces** — Generated `{{ steps.my step.output_path }}` (invalid dot notation). Now uses `{{ steps['my step'].output_path }}` bracket notation for names with spaces. (`frontend/src/components/pipeline/StepEditor.tsx`)
- [x] **Documentation links showed no content** — Settings page links pointed to `/docs/*.md` which nothing served. Added Flask `/api/docs/<filename>` route; links updated to `/api/docs/` and open in new tab. (`flowforge/api/app.py`, `frontend/src/pages/Settings.tsx`)
- [x] **`data load` button hidden in pipeline builder** — 6 step-type buttons overflowed off the right edge. Fixed with `flexWrap: wrap`. (`frontend/src/pages/PipelineEdit.tsx`)

### Verified End-to-End
- [x] **Gmail email send verified** — Report → email pipeline ran successfully; email received with CSV attachment via Gmail OAuth2.

---

## Phase 4 — Polish & Release Prep 🔵 *(COMPLETE — 2026-05-22)*

- [x] **README screenshots** — Dashboard ✓, Run Detail ✓, Pipeline Builder ✓, Email Setup ✓, Scheduler Disabled ✓ *(all 9 in `docs/screenshots/`)*

---

## Phase 2 — Tests & Verification 🧪 *(COMPLETE — 2026-05-22)*

### End-to-End Pipeline Test
- [x] Create DB connection → Test → verify "Connected" *(screenshot: connection-test-success.png — Connected · 20ms)*
- [x] Create report config with simple `SELECT` → Preview → verify rows appear *(screenshot: report-preview-rows.png — 9 rows)*
- [x] Create pipeline with one `report` step → Run Now → check Run History *(screenshot: pipeline-run-now-success.png — 20 runs, 0 failed)*
- [x] Add `email` step after report → run → verify email received *(Gmail OAuth2 verified end-to-end)*
- [x] Verify `{{ current_month }}` resolves in output filename *(screenshot: run-detail-steps.png)*
- [x] Verify `StepResult.output_path` flows from report step *(screenshot: run-detail-steps.png)*
- [x] Verify `rows_affected` written to `ff_step_runs` *(screenshot: run-detail-steps.png)*

### Scheduler Smoke Test
- [x] Create pipeline with scheduled run → start scheduler → verify auto-run in history *(screenshot: scheduler-auto-run-history.png — 19 scheduler-triggered runs)*
- [x] Disable pipeline → verify no more runs triggered *(screenshot: scheduler-pipeline-disabled.png)*

---

## Session — 2026-05-22 🟢 *(COMPLETE)*

### Infrastructure
- [x] **Oracle 23c Free in Docker** — Added `gvenzl/oracle-free:23-slim` service to `docker-compose.yml` with `APP_USER: oracle` / `APP_USER_PASSWORD loaded from `.env`.`. Docker project renamed to `flowforge-oracle`. Data persisted in `oracle_data` volume. (`docker-compose.yml`)
- [x] **Oracle driver upgrade: `cx_Oracle` → `python-oracledb`** — Replaced deprecated driver with `python-oracledb` (thin mode — pure Python, no Oracle Instant Client required). Updated `pyproject.toml`, `requirements.txt`, and `flowforge/connections/oracle.py`. (`flowforge/connections/oracle.py`)
- [x] **`credentials.local.md`** — Local dev credentials file for PostgreSQL and Oracle (gitignored, never committed). (`credentials.local.md`, `.gitignore`)

### Features Added
- [x] **DataLoader step (`data_load`)** — New pipeline step type for bulk-loading data into any configured DB connection (Oracle or PostgreSQL).
  - Source types: `file` (CSV / Excel, supports `{{ steps.prev.output_path }}`) and `query` (SQL on any source connection — cross-DB ETL)
  - Target modes: `replace` (TRUNCATE + bulk INSERT) and `append`
  - PostgreSQL target uses `psycopg2.extras.execute_batch` for true bulk performance
  - Oracle target uses positional bind vars (`:1, :2, ...`) via `oracledb.executemany`
  - Chunked inserts with configurable `chunk_size` (default 1000)
  - Optional `column_map` to rename source → target columns
  - (`flowforge/steps/data_load.py`, `flowforge/connections/base.py`, `flowforge/connections/postgres.py`, `flowforge/connections/oracle.py`, `flowforge/engine/loader.py`, `flowforge/api/routes/steps.py`)
- [x] **DataLoader frontend form** — `DataLoadForm` component in `StepEditor.tsx`:
  - Source type toggle (File / SQL Query)
  - File source: quick-attach buttons from preceding report steps, file_path input, format picker, optional sheet name
  - Query source: source connection picker + SQL textarea
  - Target section: connection picker, table input (Jinja2 vars), mode selector
  - Advanced panel (collapsible): chunk size + column map JSON editor
  - Amber `Load` badge (`.tbadge-load`) added to design system
  - (`frontend/src/components/pipeline/StepEditor.tsx`, `frontend/src/pages/PipelineEdit.tsx`, `frontend/src/lib/types.ts`, `frontend/src/lib/helpContent.ts`, `frontend/src/index.css`)

### Bug Fixes
- [x] **TypeScript TS6133 errors in test files** — Removed unused `React`, `beforeEach`, and `vi` imports from `Dashboard.test.tsx`, `Pipelines.test.tsx`, and `TopBarSearch.test.tsx`. `npx tsc --noEmit` now exits clean. (`frontend/src/__tests__/`)

### Scripts
- [x] **`scripts/test_oracle.py`** — Oracle connection + DataLoader smoke test: waits for container readiness, prints Oracle version banner, exercises `execute_many` + `make_placeholders` via `OracleConnection`, verifies replace mode.

---

## Session — 2026-05-21 / 2026-05-22 🟢 *(COMPLETE)*

### Bug Fixes
- [x] **Scheduler stale job bug** — `_load_pipeline_jobs()` only added jobs, never removed them. Clearing or disabling a pipeline schedule in the UI had no effect; the old job persisted in the PostgreSQL jobstore across restarts. Fixed by replacing with `_sync_pipeline_jobs()` which diffs existing vs active job IDs and calls `remove_job()` for stale entries. Added a `_pipeline_sync` interval job (every 60s) so schedule changes apply automatically without restarting. (`flowforge/engine/scheduler.py`)
- [x] **Scheduler thread-context bug** — APScheduler worker threads had no Flask app context; `current_app` raised `RuntimeError`. Fixed by storing `app` at module level and pushing context per job run. (`flowforge/engine/scheduler.py`, `flowforge/cli.py`)
- [x] **PowerShell `$PID` reserved variable** — `.\flowforge.ps1 stop` crashed with "Cannot overwrite variable PID because it is read-only or constant". Renamed local variable to `$procId`. (`flowforge.ps1`)

### Features Added
- [x] **JSON report format** — New output format in Report Designer: generates a JSON array of objects (one per row). Alembic migration `0004_json_report_format.py` applied. (`flowforge/reports/json_report.py`, `flowforge/steps/report.py`, `flowforge/api/routes/reports.py`, `flowforge/db/models.py`)
- [x] **Dashboard next run time** — Pipeline cards show when the next scheduled run fires, computed server-side via APScheduler `CronTrigger.from_crontab()`. (`flowforge/api/routes/pipelines.py`, `frontend/src/pages/Dashboard.tsx`)
- [x] **Startup scripts auto-start scheduler** — `flowforge.ps1` and `flowforge.sh` now start API + scheduler + UI together. `[sched]` log prefix. Stop action kills all three. (`flowforge.ps1`, `flowforge.sh`)
- [x] **Scheduler diagnostic script** — `check_scheduler.py` — 7-step end-to-end diagnostic (env → DB → pipelines → thread context → direct fire → run history → job registration).
- [x] **Quick-attach report steps in email config** — When an email step has preceding report steps in the same pipeline, they appear as one-click buttons showing step name + output filename. Clicking inserts `{{ steps.<name>.output_path }}` automatically; already-added steps show green checkmark. (`frontend/src/components/pipeline/StepEditor.tsx`)
- [x] **Email body template size increase** — `rows={14}` → `rows={28}`, `minHeight: 420px`. (`frontend/src/pages/EmailEdit.tsx`)

### UI Improvements
- [x] **Report Designer format auto-extension** — Selecting a format now automatically updates the output filename extension.
- [x] **Pipelines list schedule column** — Shows human-readable cron description + raw expression; "Manual only" for unscheduled.
- [x] **Pipelines list status column** — Green "Active" badge for enabled pipelines.
- [x] **CronBuilder hourly label** — Fixed confusing "at minute N" → "at :N each hour".

### Documentation
- [x] `docs/running-the-server.md` — scheduler as third process, updated mode descriptions, stop behaviour, troubleshooting rows
- [x] `docs/getting-started.md` — startup script as recommended path, JSON format mention, Scheduler Diagnostics section
- [x] `docs/step-types.md` — JSON added to report format options
- [x] `RUNBOOK.md` — all-in-one startup section, scheduler troubleshooting table (section 4a)
- [x] `CHANGELOG.md` — v0.1.1 and v0.1.2 entries

### Manual Testing (Phase 2)
- [x] DB connection test — Connected · 20ms (`docs/screenshots/connection-test-success.png`)
- [x] Report preview rows — 9 rows (`docs/screenshots/report-preview-rows.png`)
- [x] Pipeline Run Now → success in Run History (`docs/screenshots/pipeline-run-now-success.png`)
- [x] Run detail step timeline + output path + rows_affected (`docs/screenshots/run-detail-steps.png`)
- [x] Scheduler auto-trigger — 19 runs with `triggered_by=scheduler` (`docs/screenshots/scheduler-auto-run-history.png`)
- [x] Dashboard README screenshot (`docs/screenshots/dashboard.png`)

---

## Phase 9 — Frontend Quality 🟢 *(COMPLETE — 2026-05-20)*
*Addresses FE findings. Target score: Frontend 5.5 → 7.0*

- [x] **[FE-1] Add form validation** — `fieldErrors` state added to PipelineEdit, ReportEdit, EmailEdit; inline errors shown under Name, Subject, Query, Recipients, Timeout fields; errors clear on field edit. Zod/react-hook-form already installed.
- [x] **[FE-2] Add React error boundaries** — `RouteErrorBoundary` class component created; wraps `<Outlet />` in `Layout.tsx`; shows friendly card with "Try again" button on render errors.
- [x] **[FE-3] Fix `any` types in TopBar search** — `any[]` replaced with `Pipeline[]`, `ReportConfig[]`, `EmailConfig[]` from `lib/types.ts`.
- [x] **[FE-4] Show search hint when cache is empty** — when all caches empty and query has text, shows "Visit Pipelines and Reports pages first to populate search"; shows "No results" only when caches are populated but nothing matches. Test updated (14/14 passing).
- [x] **[FE-5] Migrate hardcoded hex colors to CSS tokens** — replaced `#F97316` → `var(--accent)`, `#1A1D27` → `var(--surface)`, `#21252F` → `var(--surface-2)`, `#2D3143` → `var(--border)`, `#F1F5F9` → `var(--text)`, `#64748B` → `var(--text-muted)`, `#475569` → `var(--text-dim)`, `#CBD5E1` → `var(--text-2)`, `#0F1117` → `var(--bg)`, `#22C55E` → `var(--success)`, `#FB923C` → `var(--accent-h)` across TopBar, Layout, PipelineEdit, ReportEdit, EmailEdit, RunHistory, Connections.
- [x] **[FE-6] Add pagination** — backend `GET /runs` now accepts `offset` param; `getRuns()` in api.ts updated; RunHistory defaults to 50 rows, "Load more" button adds 50 each click, limit resets when filters change, `keepPreviousData` prevents flicker.
- [x] **[FE-7] Fix TopBar blur handler** — replaced `setTimeout(..., 150)` with `containerRef` wrapping the search area; `onBlur` uses `relatedTarget.contains()` so dropdown stays open when tabbing to results; result divs have `tabIndex={-1}`.

---

## Phase 8 — Test Coverage *(COMPLETE — 2026-05-20)*
*Addresses TEST findings. Target score: Tests 6.0 → 7.5*

- **[TEST-2] Fix false-green test** — added `assert result.success is False` to `test_on_error_continue_pipeline_still_fails` in `test_runner.py`.
- **[TEST-3a] Test smart attachment logic** — already fully covered by `test_smart_attachments.py` (direct, Drive upload, missing file). No new tests needed.
- **[TEST-3b] Test Jinja2 rendering errors** — `tests/test_jinja_errors.py` added: `render()` raises `TemplateSyntaxError` on `{{ unclosed`; runner catches it and produces `StepResult(success=False)`; on_error=continue continues past the bad step.
- **[TEST-3c] Test cron validation endpoint** — `tests/test_cron_endpoint.py` added: 12 tests covering valid expressions, n parameter, results ordering, ISO-8601 format, missing expr, invalid expr, out-of-range field, and auth guard.
- **[TEST-3d] Test pipeline variable secret masking** — already fully covered by `test_pipeline_variables.py` (`test_secret_var_masked_in_api_response`, `test_secret_var_not_leaked_by_update`). No new tests needed.
- **[TEST-3e] Test encryption/decryption round-trip** — two tests added to `test_connections.py`: API masks password as `***`; raw DB column does not contain plaintext; `decrypt_config()` recovers original value. Also fixed stale `test_create_connection_bad_type` (was testing `mysql` which is now valid — changed to `sqlite`). Updated `connections.py` route to accept the 5 valid types.
- **[TEST-4] Add frontend tests** — Vitest + @testing-library/react installed; `vitest.config.ts` added; 13 tests in 3 files: `Dashboard.test.tsx` (5 tests), `Pipelines.test.tsx` (3 tests), `TopBarSearch.test.tsx` (5 tests — seeded React Query cache, Escape to clear, report search). All 13 pass.

---

## Phase 7 — Code Quality *(COMPLETE — 2026-05-20)*
*Addresses CODE + DB findings. Target score: Code Quality 6.0 → 7.5, Database 6.5 → 8.0*

- **[CODE-1] Fix silent exception swallowing in `runner.py` DB helpers** — `except Exception: return None` replaced with `except SQLAlchemyError as e: logger.error(...)` in all three helpers; `SQLAlchemyError` imported at module level.
- **[CODE-2] Replace class-name string manipulation for `step_type`** — `step_type: str = ''` added to `BaseStep`; each concrete step sets its own value; `_write_step_run` uses `step.step_type` with the string-hack as fallback.
- **[CODE-3] Protect built-in context variables from `output_variables` overwrite** — before `context.update(...)`, collision check against `_CONTEXT_META_KEYS`; conflicting keys logged and skipped; safe keys propagated normally.
- **[CODE-4] Fix `_utcnow()` timezone stripping** — `_utcnow()` returns `datetime.now(timezone.utc)` (no `.replace(tzinfo=None)`); all model `DateTime` columns changed to `DateTime(timezone=True)`; all call sites updated; migration `0002_timezone_timestamps.py` converts columns to TIMESTAMPTZ.
- **[DB-1] Fix step reordering constraint** — `PUT /pipeline-steps/<id>` uses two-phase swap: occupant moved to order 999999 → target step moved → occupant moved to original slot; no unique constraint violation.
- **[DB-2] Add performance indexes** — migration `0003_indexes_and_constraints.py` adds `ix_pipeline_runs_pipeline_started` on `(pipeline_id, started_at DESC)` and `ix_step_runs_pipeline_run` on `(pipeline_run_id)`.
- **[DB-3] Widen `DbConnection` check constraint** — `mysql`, `mssql`, `snowflake` added to constraint in both `models.py` and migration `0003`; old constraint dropped and recreated.

---

## Phase 6 — Reliability & Production Readiness *(COMPLETE — 2026-05-20)*
*Addresses ARCH + OPS findings. Target score: Architecture 6.5 → 8.0, DevOps 6.0 → 7.5*

- **[ARCH-1a] Add concurrency limit to pipeline execution** — `FLOWFORGE_MAX_CONCURRENT_RUNS` env var (default 5); `threading.Semaphore` in `trigger_run`; excess runs rejected with HTTP 429; semaphore released in `finally` block.
- **[ARCH-1b] Enforce `timeout_minutes` in `runner.py`** — background thread uses `concurrent.futures.ThreadPoolExecutor`; `.result(timeout=...)` raises `TimeoutError`; run marked `failed` with `"Pipeline timed out"`.
- **[ARCH-1c] Sweep stuck `running` runs on startup** — `_sweep_stuck_runs()` called from `create_app()`; marks all `status='running'` rows as `failed` with `"Run interrupted by server restart"`; skips silently if table missing.
- **[ARCH-2] Add `scheduler` service to `docker-compose.yml`** — second service runs `flowforge schedule`; shares image + `output_files` volume; depends on `app: service_healthy`.
- **[ARCH-3] Fix stuck-run race condition in `trigger_run`** — `load_pipeline()` wrapped in `try/except`; on failure run record is set to `failed` and semaphore is released before returning 500.
- **[OPS-2] Add `healthcheck` to `app` service in `docker-compose.yml`** — `GET /api/health`; `interval: 15s`, `timeout: 5s`, `retries: 3`, `start_period: 30s`.
- **[OPS-3] Move `_seed_admin` out of `create_app()`** — `flowforge db seed` CLI command added; documented in getting-started.md; `_seed_admin` removed from app factory, replaced with `_sweep_stuck_runs`.

---

## Phase 5 — Security Fixes *(COMPLETE — 2026-05-20)*
*Addresses SEC findings from CODEBASE_REVIEW.md. Target score: Security 5.5 → 8.0*

- **[SEC-1] Remove hardcoded credentials from `tests/conftest.py`** — removed hardcoded password default; added `.env.test.example`; `sys.exit(1)` with clear message if `FLOWFORGE_DB_URL` not set; CI workflow already sets it.
- **[SEC-2] Split encryption key and JWT secret** — `FLOWFORGE_JWT_SECRET` introduced for JWT signing; `FLOWFORGE_SECRET_KEY` reserved for AES-256 only. Falls back with a `warnings.warn` if unset. Updated `app.py`, `auth.py`, `conftest.py`, `.env.example`, CI workflow.
- **[SEC-3] Fix rate limiter for proxied deployments** — added `werkzeug.middleware.proxy_fix.ProxyFix` controlled by `FLOWFORGE_TRUSTED_PROXIES` env var (default 0). When set ≥1, `get_remote_address` correctly resolves real client IP from `X-Forwarded-For`. Documented in `.env.example`.
- **[SEC-6] Require `FLOWFORGE_CORS_ORIGIN` in production** — logs a loud `WARNING` at startup if `FLASK_ENV=production` and var is unset. `http://localhost:5173` is now dev/test fallback only. Added `FLOWFORGE_CORS_ORIGIN` to `.env.example`.
- **[SEC-7] Add basic audit logging** — `flowforge/audit.py` writes to `logs/audit.log`. Login success/failure logged from `routes/auth.py` (with IP). Pipeline STARTED/SUCCESS/FAILED logged from `runner.py`.

---

## Completed: Phase 4 Docs (May 2026)

- **`docs/step-types.md`** — Full config spec for all 5 step types (`db_procedure`, `db_query`, `report`, `email`, `drive_upload`) with YAML examples, field tables, output variable docs, and complete variable reference table including all date-range vars.
- **`docs/email-providers.md`** — SMTP setup (with presets for Outlook, Yahoo, SendGrid, Gmail app password), Microsoft 365 step-by-step Azure AD app registration + admin consent + token refresh notes, provider comparison table.
- **`CONTRIBUTING.md`** — Dev setup (venv, DB, env, frontend), running tests (real-DB rationale), project structure, how to add a new step type, PR checklist.
- **`.github/ISSUE_TEMPLATE/bug_report.md`** and **`feature_request.md`** — GitHub issue templates with environment fields, reproduction steps, log paste sections, and affected-area checkboxes.
- **`CHANGELOG.md`** — Fully rewritten v0.1.0 entry covering all shipped features (engine, steps, connections, reports, email providers, variable system, scheduler, frontend, security, DevOps, CLI, docs); `[Unreleased]` stub added; GitHub URL corrected to `jagdeepvirdi/flowforge`.

---

## Completed: Phase 1 Bug Fix (May 2026)

- **Report columns col0/col1/col2** — Added `execute_query_with_columns()` to `BaseConnection`, `PostgreSQLConnection`, and `OracleConnection` returning `(rows, column_names)` from `cursor.description`. `ReportStep` now uses it; explicit `report_cfg['columns']` still overrides when set. (commit `df2f63e`)

---

## Completed: Phase 4 Code Items (May 2026)

- **Visual cron builder** — `PipelineEdit.tsx` — frequency picker (none/minutely/hourly/daily/weekly/monthly/custom) with contextual controls, live cron expression preview, next-5-runs via `GET /api/pipelines/cron-next`. `FieldTooltip` clipping fixed: flips downward when within 220px of viewport top. (commit `aeffc2f`)
- **TopBar refresh button** — `RefreshCw` icon in `TopBar.tsx` calls targeted or global `queryClient.invalidateQueries()`. (commit `aeffc2f`)
- **Help discovery indicator** — Orange pulse dot (`.ff-help-dot`) on `?` button; cleared to `localStorage ff_help_seen` on first open. `@keyframes ff-accent-pulse` added to `index.css`. (commit `aeffc2f`)
- **Run history: log resolved variable values** — `runner.py` appends a "Variables resolved:" block to every `ff_step_runs.logs` entry. Secret vars masked as `***`. `loader.py` now returns `secret_keys: set[str]` as 3rd value; all call-sites updated. (commit `aeffc2f`)
- **Validate cron expressions** — `_validate_cron()` in `pipelines.py` uses APScheduler's `CronTrigger.from_crontab()`; called on pipeline create and update. (commit `aeffc2f`)

---

## Completed: Phase 2 Features (May 2026)

- **Built-in smart date-range variables** — Added `{{ week_start }}`, `{{ week_end }}`, `{{ month_start }}`, `{{ month_end }}`, `{{ quarter_start }}`, `{{ quarter_end }}` to `flowforge/engine/context.py`. ISO week Mon–Sun; quarter Q1=Jan–Mar etc. Tooltip in `helpContent.ts` updated with all new vars and examples. (commit `938459e`)
- **db_query scalar output variable** — Optional `output_variable` field on `db_query` step config captures first column of first row into top-level pipeline context (e.g. `{{ subscription_count }}`). `StepResult.output_variables` dict added; runner propagates it. `StepEditor.tsx` shows the field with inline usage hint. (commit `938459e`)

---

## Completed: Phase 1 Fixes + Phase 2 Tests + Phase 3 Help System (May 2026)

### Phase 1 — Core Stability
- **Database Migrations (Alembic)** — Replaced `db.create_all()` with Alembic; baseline migration in `flowforge/db/migrations/`.
- **M365 Token Refresh** — Token re-acquired via MSAL before each `send()` call in `flowforge/email_providers/microsoft365.py`.
- **CLI Parity: `flowforge import`** — YAML → pipeline + steps via DB (mirrors `flowforge export` in reverse).

### Phase 2 — Tests & Settings OAuth
- **`test_pipeline_variables.py`** — Secret var encrypted on write, decrypted at runtime, `{{ vars.key }}` available in context, plaintext non-secret var unaffected.
- **Settings OAuth Wiring** — "Set up Gmail" button wired to `/api/setup/gmail`; "Set up Drive" button wired; current OAuth status (connected / not connected) shown per provider.

### Phase 3 — In-App Help System (fully complete)

#### HelpDrawer component
- `frontend/src/components/shared/HelpDrawer.tsx` — right-side sliding panel (400px), `?` button in TopBar
- Context-sensitive content based on current route
- Keyboard shortcut: `?` key opens/closes
- Zustand store `useHelp` — `{ open, topic, openHelp(topic?), closeHelp() }`
- Close on Escape + overlay click; smooth slide-in animation

#### Page intro cards
Collapsible "What is this?" card at top of each page (dismissed via `localStorage` flag `ff_help_dismissed_<page>`):
- **Dashboard** — "Your pipeline control center. See last run status, trigger runs manually, monitor active jobs."
- **Pipelines** — "A pipeline is an ordered list of steps. Steps run in sequence: query a DB, generate a report, send an email."
- **Reports** — "Report configs define a SQL query + output format (Excel/PDF/CSV). A report step runs this query and writes the file."
- **Emails** — "Email configs define the subject, body, and recipients. They reference an Email Provider (Gmail/M365/SMTP)."
- **Connections** — "DB Connections store credentials for your databases. Credentials are encrypted at rest."
- **Recipients** — "Recipient groups are named lists of email addresses. Assign a group to an email config instead of typing addresses every time."
- **Run History** — "Every pipeline execution is recorded here. Click a run to see step-by-step timing, logs, and errors."
- **Settings** — "Connect FlowForge to Gmail or Microsoft 365 via OAuth2. Configure system-wide defaults."

#### Field-level tooltips
`(?)` icon → small popover with explanation + example:
- **Cron schedule field** — 5-part format, examples (`0 8 * * 1-5` = weekdays 8am), link to crontab.guru
- **`{{ variable }}` syntax fields** — list all vars: `current_date`, `current_month`, `current_year`, `yesterday`, `run_id`, `pipeline_name`, `steps.step_name.output_path`
- **DB Connection host/port/database** — PostgreSQL vs Oracle example values
- **Drive Folder ID** — "The ID is the last part of the Drive folder URL: `.../folders/THIS_PART`"
- **Attachment max MB** — explain smart attachment threshold behavior
- **Email body template** — note Jinja2 support
- **on_error field** — `stop` vs `continue` behavior
- **Oracle connection string** — both formats: `host:port/service` and TNS alias

#### Empty state guidance
- **Pipelines** — "No pipelines yet…" + Create Pipeline button
- **Connections** — "No connections yet…" + Add Connection button
- **Emails** — "No email configs yet… You'll also need an Email Provider set up first." + links to both
- **Reports** — "No report configs yet…"
- **Run History** — "No runs yet. Trigger a pipeline from the Pipelines page."

#### Concept glossary (HelpDrawer "Glossary" tab)
- Defines: Pipeline, Step, Step Type, Report Config, Email Config, Email Provider, Recipient Group, Smart Attachments, Run, Step Run, Pipeline Variable, on_error
- Each definition: 2-sentence plain English + "Where to find it" link

#### Step editor contextual help
- **db_procedure** — Oracle `package.procedure` syntax note, params support `{{ variables }}`
- **db_query** — `replace` vs `append` mode explanation
- **report** — output path available as `{{ steps.this_step_name.output_path }}`
- **email** — use `{{ steps.report_step.output_path }}` in attachments field
- **drive_upload** — link available as `{{ steps.this_step_name.drive_url }}`

---

## Completed: Score-Driven Roadmap Items (May 2026)

### 🔴 Deployment & DevOps
- **Docker Orchestration** — `docker-compose.yml` bundling Flask, React (Nginx), and PostgreSQL. (commit `66220d0`)
- **GitHub Actions CI** — `.github/workflows/test.yml` running pytest on every push/PR. (commit `57f5222`)

### 🟡 Security & Stability
- **Security Hardening** — `flask-limiter` on `/api/auth/login` (10/min per IP). (commit `57f5222`)
- **Output TTL Cleanup** — `flowforge cleanup` CLI command + daily scheduler job to prune `./output/`. (commit `ecfe8de`)
- **Context Sync** — `{{ run_id }}` in Jinja2 context now matches the actual `ff_pipeline_runs.id`. (commit `66220d0`)

### 🔵 Technical Debt & Polish
- **SDK Extras** — `google-api-python-client`, `google-auth`, `google-auth-oauthlib`, `msal` moved to optional extras (`[gmail]`, `[drive]`, `[microsoft365]`). (commit `167fd9e`)
- **Python 3.12 Compliance** — `utcnow()` replaced with `datetime.now(timezone.utc)` across all models. (commit `66220d0`)
- **GitHub repo URLs** — Placeholder `YOUR_GITHUB_USERNAME` replaced with `jagdeepvirdi/flowforge`. (commit `b975bf1`)
- **OneDrive backlog entry** — Implementation notes added to v2 backlog. (commit `291a13a`)

---

## Completed: All 8 GitHub Release Blockers (commit `c749de7`)

1. Legacy `code/` directory removed from git tracking
2. CLI setup commands print actionable instructions
3. `xlsxwriter` removed, `requests` added, `cx_Oracle` corrected in deps
4. Async pipeline execution — `POST /run` returns 202 + `run_id` immediately
5. DB credentials + email provider configs encrypted (AES-256-GCM)
6. Secret pipeline variables masked in UI and encrypted at rest
7. JWT auth hardened (expired/bad-secret/malformed all → 401)
8. Admin user seeded from env vars on startup

---

## Completed: Pre-Phase — Scrub & Refactor Sessions

- **Session Zero** — Full structured code review saved to `docs/code-review.md`
- **Session 1** — Dead code removed, duplicate logic consolidated, debug prints cleaned
- **Session 2** — All company/telecom/internal references scrubbed
- **Session 3** — Refactored into FlowForge package layout (`engine/`, `steps/`, `connections/`, `email_providers/`, `reports/`, `storage/`)
- **Session 4** — GitHub release files created: README, .gitignore, pyproject.toml, .env.example, LICENSE, CHANGELOG.md, getting-started.md

---

## Completed: Phase 1 — Database Schema & API Foundation

- Full PostgreSQL schema: `email_providers`, `db_connections`, `pipelines`, `pipeline_steps`, `pipeline_variables`, `report_configs`, `email_configs`, `recipient_groups`, `pipeline_runs`, `step_runs` (11 tables)
- SQLAlchemy models for all tables
- `flowforge/crypto.py` — AES-256-GCM encrypt/decrypt, key from `FLOWFORGE_SECRET_KEY`
- Flask app factory, JWT auth middleware, CORS, health check, JSON error handler
- All REST routes: pipelines, steps, reports, emails, recipients, connections, providers, runs (full CRUD + test endpoints)

---

## Completed: Phase 2 — Core Engine

- `flowforge/engine/context.py` — Jinja2 variable resolution: `current_month`, `current_date`, `current_year`, `yesterday`, `run_id`, `pipeline_name`, `failed_step`, `env.VAR`, `steps.x.output_path`, `steps.x.drive_url`, `{{ timestamp }}`
- `flowforge/engine/runner.py` — step ordering, `on_error: stop/continue`, context passing, `pipeline_run` + `step_run` DB records, async daemon thread execution
- `flowforge/engine/scheduler.py` — APScheduler with PostgreSQL job store, hot reload, misfire grace

---

## Completed: Phase 3 — Step Implementations

- `flowforge/steps/base.py` — `BaseStep` ABC + `StepResult` dataclass
- `flowforge/steps/db_procedure.py` — PostgreSQL + Oracle stored procedures/packages
- `flowforge/steps/db_query.py` — SQL query → output table (replace/append/truncate_insert)
- `flowforge/steps/report.py` — dispatches to Excel/PDF/CSV generators, output path in context
- `flowforge/steps/email_step.py` — smart attachment logic, provider dispatch
- `flowforge/steps/drive_upload.py` — Drive upload, shareable link in context

---

## Completed: Phase 4 — Email Providers

- `flowforge/email_providers/base.py` — `EmailProvider` ABC
- `flowforge/email_providers/gmail.py` — OAuth2 via `google-auth` + Gmail API
- `flowforge/email_providers/microsoft365.py` — MSAL client credentials + Graph API (token refresh still has 1h bug — see remaining tasks)
- `flowforge/email_providers/smtp.py` — `smtplib`, covers STARTTLS/SSL, Outlook/Yahoo/corporate

---

## Completed: Phase 5 — Database Connections

- `flowforge/connections/base.py` — `BaseConnection` ABC
- `flowforge/connections/postgres.py` — `psycopg2` ThreadedConnectionPool, parameterized queries, bulk insert
- `flowforge/connections/oracle.py` — `cx_Oracle`, package.procedure syntax, LOB/DATE/TIMESTAMP handling, arraysize
- Connection factory: `get_connection(id)` → decrypts config, instantiates correct class

---

## Completed: Phase 6 — Report Generators

- `flowforge/reports/excel_report.py` — optional template, headers, auto-width columns, bold headers
- `flowforge/reports/pdf_report.py` — Jinja2 HTML → weasyprint (optional dep)
- `flowforge/reports/csv_report.py` — UTF-8 BOM option, configurable delimiter

---

## Completed: Phase 7 — Scheduler & CLI (partial)

- `flowforge schedule` — APScheduler daemon with PostgreSQL job store
- `flowforge run`, `flowforge list`, `flowforge validate`, `flowforge connections test`
- `flowforge setup gmail`, `flowforge setup microsoft365`, `flowforge setup drive`
- `flowforge web` — start Flask + React frontend
- `flowforge export <pipeline>` — export pipeline as YAML
- `flowforge cleanup` — prune output files older than N days
- `server_start.ps1` / `server_start.sh` scripts

---

## Completed: Phase 8 — Frontend (scaffolded and wired)

- React + Vite + TypeScript scaffold, design tokens applied to `tailwind.config.ts`
- React Query + React Router + JWT auth (login, token storage, API interceptor)
- **Dashboard** — pipeline cards, status badges, live polling, global stats
- **Pipeline Builder** — list, edit, step forms (db_procedure, db_query, report, email, drive_upload), drag-to-reorder, cron builder, on_error toggle
- **Report Designer** — SQL editor (CodeMirror 6), format selector, output filename, Preview (first 20 rows)
- **Email Designer** — provider picker, recipients, CC/BCC, subject, body editor, smart attachment settings, Preview modal
- **Recipient Groups** — create/edit groups, address chip input
- **Connections Manager** — DB connections + email providers tabbed, test button, credential masking
- **Run History** — table with filters, run detail with step timeline + expandable logs
- **Settings** — OAuth setup buttons, defaults, YAML export/import
- Report step output file download

---

## Completed: Test Suite (168 tests passing)

| File | Coverage |
|---|---|
| `test_crypto.py` | encrypt/decrypt, unique nonces, bad key |
| `test_auth.py` | login, JWT, protected routes |
| `test_connections.py` | DB connection CRUD + live test + raw test |
| `test_pipelines.py` | pipeline CRUD + step CRUD |
| `test_reports.py` | report config CRUD + preview + semicolon fix |
| `test_recipients.py` | recipient group CRUD |
| `test_runs.py` | run history filters + disabled pipeline guard |
| `test_email_configs.py` | email config CRUD |
| `test_email_providers.py` | mocked SMTP send (SSL, TLS, CC/BCC, attachments, failure) |
| `test_context.py` | Jinja2 variable resolution (all vars) |
| `test_runner.py` | step ordering, on_error stop/continue, context passing |
| `test_steps_db.py` | db_query + db_procedure with mocked connections |
| `test_report_generators.py` | Excel headers/data/bold; CSV header row, delimiter |
| `test_smart_attachments.py` | under/over limit, Drive upload + link, missing file |
| `test_jwt_expiry.py` | expired/bad-secret/malformed/empty/no-header → 401 |

Manual test scripts in `tests/manual/`: `check_api.py`, `check_email.py`, `check_runner.py`, `check_scheduler.py`
