# TASKS.md — FlowForge

*Completed tasks are in [TASKS_ARCHIVE.md](TASKS_ARCHIVE.md).*
*Full codebase review with scores in [CODEBASE_REVIEW.md](CODEBASE_REVIEW.md).*

---

## GitHub Release Score: 9.5 / 10 (updated 2026-05-23)
## Codebase Review Score: 6.0 / 10 (reviewed 2026-05-20 — see CODEBASE_REVIEW.md)

| Dimension | Score |
|---|---|
| Code quality | 7/10 — Clean architecture, good separation of concerns |
| Feature completeness | 10/10 — bulk_load, pipeline variables, delta vars, create_if_missing all shipped |
| Security | 9/10 — Encryption, rate limiting, Alembic migrations all done |
| Documentation | 9/10 — CHANGELOG, step-types, getting-started, manual-testing-guide all updated |
| Deployment UX | 7/10 — Docker Compose + CI added |
| GitHub readiness | 10/10 — All manual tests passed, email verified end-to-end |

---

## Remaining Work — Query Results in Email (`db_query` → `email` data display)

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

---

### Phase 1 — Backend Core
*Foundation. Nothing else works without this.*

- [x] `flowforge/steps/base.py` — add `rows: list[dict]`, `table_html: str`, `kv_html: str` fields to `StepResult`
- [x] `flowforge/steps/db_query.py` — read `capture_rows: bool` (default `False`) and `row_limit: int` (default 100) from step config
- [x] `flowforge/steps/db_query.py` — implement `table_html` renderer: inline-styled `<table>` (no external CSS, email-client safe), HTML-escaped
- [x] `flowforge/steps/db_query.py` — implement `kv_html` renderer: `<dl>` from first row only (single-row summary queries), HTML-escaped
- [x] `flowforge/steps/db_query.py` — when `capture_rows=True`, use `execute_query_with_columns`, zip into list-of-dicts, store rows + rendered HTML in StepResult
- [x] `flowforge/engine/runner.py` — add `'rows'`, `'table_html'`, `'kv_html'` to `context['steps'][step.name]` (same pattern as `files_found` etc.)

---

### Phase 2 — Frontend: Step Config
*Lets users opt in to row capture on a per-step basis.*

- [x] `frontend/src/components/pipeline/StepEditor.tsx` — add **"Capture rows for email"** toggle (`capture_rows`) to the `db_query` form
- [x] `frontend/src/components/pipeline/StepEditor.tsx` — show **"Row limit"** number input (1–1000, default 100) when toggle is on
- [x] `frontend/src/components/pipeline/StepEditor.tsx` — add hint text showing the exact `{{ steps.NAME.table_html }}` snippet for the step name

---

### Phase 3 — Frontend: Email Designer
*The payoff — lets users insert captured data into email bodies.*

- [x] `frontend/src/components/pipeline/StepEditor.tsx` — email step shows **"Query data"** section listing upstream `db_query` steps with `capture_rows=true`, with copyable snippets for `table_html`, `kv_html`, and custom loop
- [x] `frontend/src/pages/EmailEdit.tsx` — added `{{ steps.step_name.table_html }}`, `{{ steps.step_name.kv_html }}`, and `{% for row in steps.step_name.rows %}` to the Available Variables reference card

---

### Phase 4 — Help Content & Tests
*Correctness verification and discoverability.*

- [x] `frontend/src/lib/helpContent.ts` — added `capture_rows` / `row_limit` hints to `db_query` step tips
- [x] `frontend/src/lib/helpContent.ts` — added embed-query-data hint to `email` step tips
- [x] `tests/test_db_query_capture.py` — `capture=True`: rows stored, HTML rendered, `row_limit` respected; `capture=False`: rows empty, no HTML rendered; HTML renderer unit tests incl. XSS escaping
- [x] `tests/test_runner.py` — assert `rows`, `table_html`, `kv_html` keys are in `context['steps']` for both capturing and non-capturing steps

---

## Multi-Project Support

**Goal:** Organize all FlowForge resources (pipelines, reports, email configs, recipient groups) into named projects — so teams can manage Finance, HR, Marketing Ops, etc. in one FlowForge instance without everything living in a flat list.

**Design decisions:**
- `db_connections` and `email_providers` stay **global** — infrastructure configured once, shared across projects
- A **"Default"** project is seeded on migration — all existing rows assigned to it, zero data loss
- Project switcher lives at the top of the sidebar (Vercel/Linear style)
- "All Projects" admin view for cross-project run history

**Data model — new `project_id` FK on:**
`pipelines`, `report_configs`, `email_configs`, `recipient_groups`

---

### Phase 1 — Database & Backend
*Migration is the critical path. Everything else builds on it.*

- [x] `flowforge/db/models.py` — add `Project` model: `id`, `name`, `description`, `color`, `created_at`
- [x] `flowforge/db/models.py` — add `project_id` FK (nullable → non-null after backfill) to `Pipeline`, `ReportConfig`, `EmailConfig`, `RecipientGroup`
- [x] `flowforge/db/migrations/` — Alembic migration: create `projects` table, add `project_id` columns, seed "Default" project, backfill all existing rows
- [x] `flowforge/api/routes/projects.py` — CRUD endpoints: `GET /projects`, `POST /projects`, `PATCH /projects/:id`, `DELETE /projects/:id`
- [x] All existing list/get routes — filter by `project_id` query param (e.g. `GET /pipelines?project_id=...`)
- [x] `flowforge/api/routes/runs.py` — "All Projects" run history: `GET /runs` with optional `project_id` filter

---

### Phase 2 — Frontend: Project Switcher & Projects Page
*The core navigation change.*

- [x] `frontend/src/components/shared/ProjectSwitcher.tsx` — dropdown at top of sidebar: current project name, list of all projects, "All Projects" link, "+ New Project" action
- [x] `frontend/src/lib/store.ts` (Zustand) — add `activeProjectId` global state; persisted to `localStorage`
- [x] `frontend/src/pages/Projects.tsx` — projects list as cards: name, color tag, pipeline count, last run status; create/edit/delete actions
- [x] `frontend/src/lib/api.ts` — pass `project_id` on all scoped API calls (pipelines, reports, email, recipients)

---

### Phase 3 — Frontend: Scoped Pages & All Projects View
*Filter all existing pages by active project; add the admin overview.*

- [x] `frontend/src/pages/Dashboard.tsx` — scope pipeline cards to active project; show project name in header
- [x] `frontend/src/pages/PipelineEdit.tsx` — set `project_id` on create
- [x] `frontend/src/pages/ReportEdit.tsx` — scope to active project on create
- [x] `frontend/src/pages/EmailEdit.tsx` — scope to active project on create; recipient groups filtered by project
- [x] `frontend/src/pages/Recipients.tsx` — scope to active project on list and create
- [x] `frontend/src/pages/RunHistory.tsx` — scope to active project by default; pipeline filter list scoped to active project

---

### Phase 4 — Tests & Migration Safety
*Verify the migration is safe and scoping is airtight.*

- [x] `tests/test_projects.py` — CRUD for projects; confirm resources are correctly scoped per project
- [x] `tests/test_projects.py` — confirm pipelines/groups created without `project_id` are assigned to Default project
- [x] `tests/test_projects.py` — confirm `GET /pipelines?project_id=X` returns only X's pipelines, not cross-project leakage
- [ ] Manual migration test: run on a populated DB, verify all rows backfilled, Default project present

---

## Backlog (Post v1)

### More Email Providers
- [ ] SendGrid API
- [ ] AWS SES
- [ ] Mailgun

### More Storage
- [ ] SFTP upload step
- [ ] AWS S3 upload step
- [ ] Azure Blob upload step
- [ ] **OneDrive / SharePoint upload step** — Graph API + MSAL (already installed via `[microsoft365]`). New `onedrive_upload` step type, extend smart attachment with `storage_provider` field (`google_drive` | `onedrive`). Deferred to post-core-stability. *User confirmed active need.*

### More DB Support
- [ ] MySQL / MariaDB
- [ ] MSSQL / SQL Server
- [ ] Generic ODBC

### Pipeline Features
- [ ] Pipeline dependencies (run B after A)
- [ ] Parallel step execution
- [ ] Step retry with exponential backoff
- [ ] Pipeline YAML import/export from UI
- [x] **Pipeline variables** — Variables card in Pipeline Builder; key/value/secret pairs; `{{ var_key }}` and `{{ vars.var_key }}` in all step configs; secrets encrypted at rest and masked in UI. *(Shipped 2026-05-23)*
- [x] **Bulk file loader step (`bulk_load`)** — Directory scanning, `file_prefix`/`file_prefix_exclude`, PostgreSQL `COPY FROM STDIN`, chunked Python fallback, footer row stripping, archive-after-load, `on_no_files` behaviour, Bulk Loads UI page. *(Shipped 2026-05-23)*

### Platform
- [ ] Multi-user auth with roles (v2)
- [ ] Plugin system for community step types
- [ ] Slack/Teams notifications (v2)
- [ ] AI analyze step — `flowforge/steps/ai_analyze.py`, Ollama/Claude routing, `{{ ai_summary }}` variable (v2)

---

## Known Risks & Mitigations

| Risk | Mitigation |
|---|---|
| ~~cx_Oracle requires Oracle Instant Client~~ | ✅ Resolved — migrated to `python-oracledb` (thin mode, pure Python, no Instant Client needed) |
| M365 requires Azure AD app registration | Step-by-step guide in docs/email-providers.md; flowforge setup microsoft365 wizard |
| Gmail OAuth2 token expiry | Refresh token handling; re-auth wizard in settings |
| Drive folder ID opaque to users | Folder picker in frontend fetches Drive tree via API |
| Smart attachment: Drive upload fails after report generated | Fallback: attach directly if Drive upload fails, log warning |
| Large report query times out in Preview | Preview uses `LIMIT 20` wrapper around user query |
| Oracle LOB columns break row serialization | OracleConnection reads LOB values explicitly before cursor close |
