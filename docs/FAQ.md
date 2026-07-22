# FlowForge — FAQ

Answers to questions that come up while using or reviewing the app but aren't spelled out
in one place elsewhere. Not exhaustive — see [`docs/INDEX.md`](INDEX.md) for the full doc set,
and treat the source files linked below as the ground truth if this ever drifts.

Also linked from the in-app **Help** drawer (the book icon in the top bar) — a small **FAQ ↗**
link next to the drawer's close button opens this file raw via `GET /api/docs/FAQ.md`
(`frontend/src/components/shared/HelpDrawer.tsx`).

---

## Pipelines

### Where is "Pipeline Builder"? I don't see it in the nav.

It's labelled **Pipelines** in the sidebar (`frontend/src/components/shared/Layout.tsx`) — "Pipeline
Builder" is the name used in design docs (`CLAUDE.md`) and the CHANGELOG, not the on-screen label.
Click **Pipelines** → open or create a pipeline → that's the editor page (`PipelineEdit.tsx`),
reachable at `/pipelines/:id/edit` or `/pipelines/new`.

### Where can I see the visual pipeline canvas?

In the pipeline editor (`/pipelines/:id/edit`), above the step list there's a list/grid icon toggle.
Switching to the grid icon shows the canvas view — steps as nodes laid out left-to-right in the
order they'll actually execute, with `parallel_group` steps grouped into one column. You can drag
to reorder, drag a node into/out of a group column, click a node to edit it in a side panel, and
add/duplicate/delete from the canvas. Screenshot: [`docs/screenshots/pipeline-canvas.png`](screenshots/pipeline-canvas.png).

Shipped 2026-07-09 (TASKS.md Phase 14, Option A). You can also drag from one node's handle to
another to draw a real dependency edge between two steps — shipped 2026-07-22 (Phase 14.2, Option
B; see the next question for what that changes about execution). The edge persists immediately (no
Save needed) and renders in the accent color, distinct from the neutral synthetic layout edges. Once
a pipeline has at least one real edge, the canvas shows only real edges — the synthetic wave-layout
edges disappear for that pipeline.

Code: `frontend/src/components/pipeline/canvas/`, `frontend/src/lib/pipelineWaves.ts`,
`frontend/src/lib/pipelineReorder.ts`, `frontend/src/lib/stepDeps.ts`.

### What changes when a pipeline has real step dependencies (DAG mode)?

Drawing at least one edge switches that pipeline's execution from the default sequential/
parallel-wave engine (`_build_execution_waves`) to a topological DAG engine
(`flowforge/engine/dag.py::run_dag`) — steps dispatch as soon as their upstream dependencies
complete, rather than in synchronized batches. Two behaviors differ from wave mode:

- **`on_error: stop` is branch-scoped.** In wave mode, a `stop` failure halts every later step in
  the pipeline. In DAG mode, it only skips that step's *transitive descendants* — an independent
  branch with no path from the failed step keeps running to completion. Skipped steps still get a
  real `step_runs` row with `status: skipped`, so they're visible in Run History, not silently
  missing.
- **`{{ steps.X.* }}` is ancestors-only.** In wave mode every completed step is visible to every
  later one. In DAG mode a step only sees output from steps it's actually downstream of — a sibling
  branch's output renders as blank (Jinja's default `Undefined`) rather than being available.

A pipeline with zero drawn edges is completely unaffected — it keeps running through the exact
existing wave engine, byte-for-byte. There's no migration step and no way to "half-opt-in"; the
`StepDependency.exists_for_pipeline()` check on the pipeline's edges is the only switch.

Code: `flowforge/engine/runner.py` (the dual-path gate in `run_pipeline`), `flowforge/engine/dag.py`.
Tests: `tests/test_dag_engine.py`, `tests/test_runner_dag_gate.py`, `tests/test_dag_integration.py`.

### What happens if a step fails inside a parallel group?

The other steps in that same group are **not** cancelled — `_run_parallel_wave()` dispatches every
step in the group to a `ThreadPoolExecutor` and calls `concurrent.futures.wait(futures)`, which
blocks until *all* of them finish, regardless of whether a sibling already failed. Isolation is at
the wave boundary, not instant: a failing step can't stop steps already running alongside it, only
the wave that runs *after* it.

Once every step in the group has finished, results are evaluated in order: each failure marks the
pipeline as failed (`_pipeline_has_failed`) and, if that step's `on_error` is `stop` (the default),
sets `should_stop = True` — which halts the pipeline before the next wave starts. If `on_error` is
`continue`, the failure is recorded (first error/step wins for the run's headline error) but the
pipeline proceeds to the next wave anyway. Per-step retries (`retry_count`/`retry_delay`) still
apply inside the group exactly as they would for a sequential step.

Code: `flowforge/engine/runner.py` (`_run_parallel_wave`, `_build_execution_waves`).

---

## Triggers

Schedule, Upstream Dependencies, and Webhook / API Trigger — the three ways a pipeline can start —
are consolidated into one **Triggers** card in the pipeline editor (shown only once the pipeline
already exists), with a Schedule / Dependencies / Webhook tab switcher. `DependenciesCard.tsx` and
`WebhookCard.tsx` still hold their original logic; `TriggersCard.tsx` renders them inline (via a
`bare` prop) as the tab content instead of duplicating it.

### What is "Webhook / API Trigger"?

The Webhook tab of the Triggers card. It lets you trigger a pipeline run from outside FlowForge
via a plain HTTP `POST`, instead of waiting for its cron schedule:

```
POST /api/pipelines/{pipeline-id}/trigger?token=<token>
```

Generate a token, copy the URL (shown once, not recoverable), and call it from CI, a cron job, or
a monitoring alert. Tokens are scoped to one pipeline, stored as bcrypt hashes, individually
revocable, don't expire by default, and every trigger is written to the audit log.

Code: `frontend/src/components/pipeline/TriggersCard.tsx`, `frontend/src/components/pipeline/WebhookCard.tsx`,
`flowforge/api/routes/pipelines.py`, `flowforge/db/migrations/versions/0010_webhook_tokens.py`.
Docs: `docs/getting-started.md` ("API / Webhook Triggers"), `docs/security.md` ("Webhook / API Trigger Tokens").

---

## Pipeline Dependencies

*Not to be confused with the step-level dependencies drawn on the canvas (see "Where can I see the
visual pipeline canvas?" above) — these are two separate mechanisms. This section is about whole
**pipelines** triggering other **pipelines**; the canvas edges are about **steps** within one
pipeline changing that one pipeline's execution order.*

### What is "Upstream Dependencies"?

The Dependencies tab of the Triggers card (`DependenciesCard.tsx`, rendered inline by
`TriggersCard.tsx`) that lets a pipeline auto-launch after one or more *other* pipelines succeed,
instead of (or in addition to) running on its own cron schedule. Backed by the
`ff_pipeline_dependencies` table (`upstream_id` / `downstream_id`).

After any pipeline run finishes successfully, `runner.py`'s `_trigger_downstream_pipelines()`
checks each of its downstreams: if *all* of that downstream's upstreams have had a successful run
since the downstream last started, it auto-launches with `triggered_by="dependency"`. A pipeline
with no upstream deps behaves exactly as before — schedule or manual trigger only.

### Can I add or remove dependencies from the UI?

Yes. In the Triggers card's **Dependencies** tab: pick a pipeline from the dropdown to add it (only
pipelines not already listed, and not the pipeline itself, are offered); click the trash icon to
remove one. Changes are staged in local state and only persisted when you click **Save** on the
pipeline — `PipelineEdit.tsx` diffs the before/after list and calls the add/remove API endpoints
for whatever changed. Unsaved changes are discarded like any other pipeline edit if you navigate
away. The Triggers card only appears once the pipeline already exists (needs a real pipeline ID).

### What happens if a dependency would create a cycle?

The add is rejected server-side, not blocked in the dropdown. On Save, `POST
/api/pipelines/{id}/dependencies` runs a BFS (`_has_path()` in
`flowforge/api/routes/pipelines.py`) forward from the pipeline being edited through the dependency
graph — if it can reach the proposed upstream pipeline, adding the edge would close a loop, and
the API returns `409 Conflict` with `"Adding this dependency would create a circular dependency"`.
That surfaces as the pipeline's generic save-error message.

Caveat: saving isn't atomic across multiple new dependencies in one edit — if you add several and
one of them 409s, earlier ones in the same save may already have been created before the failing
call throws. Re-open the pipeline to see what actually stuck. Duplicate additions are separately
rejected with `409` + `"Dependency already exists"`, though the dropdown already filters out
pipelines that are already listed, so that path is rarely hit from normal use.

Code: `flowforge/api/routes/pipelines.py` (`_has_path`, `add_dependency`),
`frontend/src/pages/PipelineEdit.tsx` (save-sync logic).
