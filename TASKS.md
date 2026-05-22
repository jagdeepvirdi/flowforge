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

## Remaining Work

---

### Query Results in Email (`db_query` → `email` data display)

**Goal:** When a `db_query` step runs (e.g. a post-load audit query returning success/fail counts), subsequent `email` steps can display those results inside the email body — without the user writing raw Jinja2.

**How it works end-to-end:**
1. User ticks **"Capture rows for email"** on the `db_query` step config and sets a row limit (default 100).
2. The step runner stores the result rows in `context['steps']['step_name']['rows']` (list-of-dicts) and pre-renders a styled `context['steps']['step_name']['table_html']` string.
3. In the email body editor, a new **"Insert step data"** button lists all `db_query` steps in the pipeline that have capture enabled. User picks one and a display format → the correct Jinja2 snippet is inserted into the body.
4. Email renders: `{{ steps.load_check.table_html }}` expands to an HTML table inside the sent email.

**Display format presets (the "limited options"):**
| Preset | Variable inserted | Output |
|---|---|---|
| HTML table | `{{ steps.NAME.table_html }}` | Styled `<table>` with all columns |
| Key-value list | `{{ steps.NAME.kv_html }}` | `<dl>` — first row as label:value pairs (good for single-row summaries) |
| Counts only | `{{ steps.NAME.rows_affected }}` | Plain number — same as existing `rows_affected` |
| Custom Jinja2 | `{% for row in steps.NAME.rows %}{{ row.status }}: {{ row.count }}<br>{% endfor %}` | User writes own markup with column-name access |

---

**Backend changes:**

- [ ] `flowforge/steps/base.py` — add `rows: list[dict]` to `StepResult` (default `[]`)
- [ ] `flowforge/steps/db_query.py`
  - Read `capture_rows: bool` (default `False`) and `row_limit: int` (default 100) from step config
  - When `capture_rows=True`: fetch results as list-of-dicts; truncate to `row_limit`; store in `step_result.rows`; render `table_html` and `kv_html` into `step_result.output_variables` so they land in context
  - `table_html` renderer: simple inline-styled `<table>` (no external CSS dependency, works in email clients)
  - `kv_html` renderer: `<dl>` from first row only — for single-row summary queries
- [ ] `flowforge/engine/runner.py` — add `'rows': step_result.rows` to the `context['steps'][step.name]` dict (same pattern as `files_found` etc.)

**Frontend changes:**

- [ ] `frontend/src/components/pipeline/StepEditor.tsx` — db_query form section:
  - Add **"Capture rows for email"** toggle (`capture_rows`)
  - When toggled on, show **"Row limit"** number input (1–1000, default 100)
  - Hint text: _"Makes query results available in downstream email steps as `{{ steps.NAME.table_html }}`"_
- [ ] `frontend/src/pages/EmailDesigner.tsx` (or email body CodeMirror toolbar):
  - Add **"Insert step data"** button in the body editor toolbar
  - Opens a small popover: shows all `db_query` steps in the current pipeline that have `capture_rows=true`
  - User picks a step → picks a format preset → the correct snippet is inserted at cursor position
  - If no capturing steps exist, show: _"Enable 'Capture rows for email' on a DB Query step first."_
- [ ] `frontend/src/lib/helpContent.ts` — add `capture_rows` / `row_limit` hints to `db_query` step tips; add email template variable examples (`{{ steps.NAME.table_html }}`, `{% for row in steps.NAME.rows %}`)

**No migration required** — `capture_rows` and `row_limit` are stored in `pipeline_steps.config` JSONB; `table_html`/`kv_html` live only in the in-memory pipeline context.

**Implementation order:**
1. `StepResult.rows` field + `db_query.py` capture logic + `table_html`/`kv_html` renderers
2. Runner context propagation
3. `StepEditor.tsx` capture toggle + row_limit field
4. Email designer "Insert step data" helper
5. Tests: `test_db_query_capture.py` (capture=True stores rows, renders HTML, respects row_limit, capture=False leaves rows empty); update `test_runner.py` to assert `rows` key in context

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
