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

Shipped 2026-07-09 (TASKS.md Phase 14, Option A). It does **not** support drawing arbitrary
dependency edges between steps (that's Option B, unbuilt — see [Roadmap](../ROADMAP.md)); the
canvas visualizes the existing sequential + parallel-group execution model, it doesn't add a new one.

Code: `frontend/src/components/pipeline/canvas/`, `frontend/src/lib/pipelineWaves.ts`,
`frontend/src/lib/pipelineReorder.ts`.

---

## Triggers

### What is "Webhook / API Trigger"?

A card in the pipeline editor (shown only once the pipeline already exists) that lets you trigger
a pipeline run from outside FlowForge via a plain HTTP `POST`, instead of waiting for its cron
schedule:

```
POST /api/pipelines/{pipeline-id}/trigger?token=<token>
```

Generate a token, copy the URL (shown once, not recoverable), and call it from CI, a cron job, or
a monitoring alert. Tokens are scoped to one pipeline, stored as bcrypt hashes, individually
revocable, don't expire by default, and every trigger is written to the audit log.

Code: `frontend/src/components/pipeline/WebhookCard.tsx`, `flowforge/api/routes/pipelines.py`,
`flowforge/db/migrations/versions/0010_webhook_tokens.py`. Docs: `docs/getting-started.md`
("API / Webhook Triggers"), `docs/security.md` ("Webhook / API Trigger Tokens").

---

## Pipeline Dependencies

### What is "Upstream Dependencies"?

A card in the pipeline editor (`DependenciesCard.tsx`) that lets a pipeline auto-launch after
one or more *other* pipelines succeed, instead of (or in addition to) running on its own cron
schedule. Backed by the `ff_pipeline_dependencies` table (`upstream_id` / `downstream_id`).

After any pipeline run finishes successfully, `runner.py`'s `_trigger_downstream_pipelines()`
checks each of its downstreams: if *all* of that downstream's upstreams have had a successful run
since the downstream last started, it auto-launches with `triggered_by="dependency"`. A pipeline
with no upstream deps behaves exactly as before — schedule or manual trigger only.

### Can I add or remove dependencies from the UI?

Yes. In the **Upstream Dependencies** card: pick a pipeline from the dropdown to add it (only
pipelines not already listed, and not the pipeline itself, are offered); click the trash icon to
remove one. Changes are staged in local state and only persisted when you click **Save** on the
pipeline — `PipelineEdit.tsx` diffs the before/after list and calls the add/remove API endpoints
for whatever changed. Unsaved changes are discarded like any other pipeline edit if you navigate
away. The card only appears once the pipeline already exists (needs a real pipeline ID).

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
