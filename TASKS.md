# TASKS.md — FlowForge

*Completed tasks are in [TASKS_ARCHIVE.md](TASKS_ARCHIVE.md).*
*Full codebase review with scores in [CODEBASE_REVIEW.md](CODEBASE_REVIEW.md).*

---

## GitHub Release Score: 8.6 / 10 (updated 2026-05-22)
## Codebase Review Score: 6.0 / 10 (reviewed 2026-05-20 — see CODEBASE_REVIEW.md)

| Dimension | Score |
|---|---|
| Code quality | 7/10 — Clean architecture, good separation of concerns |
| Feature completeness | 9/10 — Scheduler sync, JSON format, quick-attach, all phase 9 items done |
| Security | 9/10 — Encryption, rate limiting, Alembic migrations all done |
| Documentation | 7/10 — All docs updated, scheduler runbook added, screenshots in progress |
| Deployment UX | 7/10 — Docker Compose + CI added |
| GitHub readiness | 9/10 — Startup scripts solid, scheduler reliable, UX improvements shipped |

---

## Remaining Work

---

## Phase 2 — Tests & Verification 🧪
*Automated test coverage + manual pre-launch smoke tests.*

### Manual Verification Checklist (do before launch)

#### End-to-End Pipeline Test
- [x] Create DB connection → Test → verify "Connected" *(screenshot: connection-test-success.png — Connected · 20ms)*
- [x] Create report config with simple `SELECT` → Preview → verify rows appear *(screenshot: report-preview-rows.png — 9 rows)*
- [x] Create pipeline with one `report` step → Run Now → check Run History *(screenshot: pipeline-run-now-success.png — 20 runs, 0 failed)*
- [ ] Add `email` step after report → run → verify email received
- [x] Verify `{{ current_month }}` resolves in output filename *(screenshot: run-detail-steps.png — RunBook_Report_2026-05_...csv visible)*
- [x] Verify `StepResult.output_path` flows from report step *(screenshot: run-detail-steps.png — output file and Download button visible)*
- [x] Verify `rows_affected` written to `ff_step_runs` *(screenshot: run-detail-steps.png — "Rows affected: 9" visible)*

#### Scheduler Smoke Test
- [x] Create pipeline with scheduled run → start scheduler → verify auto-run in history *(screenshot: scheduler-auto-run-history.png — 19 scheduler-triggered runs)*
- [ ] Disable pipeline → verify no more runs triggered

---

## Phase 4 — Polish & Release Prep 🔵
*Docs, GitHub presence, and final UX touches.*

- [ ] **README screenshots** — ~~Dashboard~~ ✓, ~~Run Detail~~ ✓, **Pipeline Builder still needed**. Highest-impact item for GitHub stars.

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
- [ ] **Pipeline run parameter UI** — A "Parameters" section on the pipeline edit page where you define named params and their computation rules (e.g., `week_start = start of current ISO week`, `week_end = end of current ISO week`). More flexible than built-in date vars; allows per-pipeline customization. Params become available as `{{ params.week_start }}` in all step configs. Pairs with the built-in smart date vars (ship those first).
- [ ] **Bulk file loader step (`bulk_load`)** — Advanced successor to `data_load`. Replaces the Oracle SQL\*Loader shell script at `github.com/jagdeepvirdi/DayToDayOfficeOperations`. Adds: directory scanning (`file_prefix`, `file_prefix_exclude`), Oracle SQL\*Loader direct-path via subprocess (fastest), PostgreSQL `COPY FROM STDIN`, footer row stripping, `.bad` file surfacing in logs, archive-after-load, `files_found`/`records_loaded`/`records_failed` output variables. Full spec below.

  **Step config (stored in `pipeline_steps.config` JSONB):**
  ```json
  {
    "connection_id": "uuid",
    "source_directory": "/data/incoming/",
    "file_prefix": "SUBS_",
    "file_prefix_exclude": null,
    "file_type": "csv",
    "delimiter": ",",
    "header_rows": 1,
    "footer_rows": 0,
    "target_table": "STAGING.SUBSCRIPTIONS",
    "load_mode": "append",
    "column_mapping": [],
    "use_sqlloader": true,
    "archive_directory": "/data/archive/{{ current_date }}/",
    "on_no_files": "skip"
  }
  ```

  **Execution — three internal paths:**
  1. **Oracle + `use_sqlloader: true`** — FlowForge generates a `.ctl` control file dynamically from the step config (delimiter, column mapping, date formats). Calls `sqlldr user/pass@dsn control=<tmp>.ctl log=<tmp>.log bad=<tmp>.bad` as a subprocess. Parses the `.log` file for "rows loaded" / "rows not loaded" counts. Surfaces `.bad` file content (rejected rows) in `step_runs.logs`. Fastest path — Oracle direct-path load, bypasses redo logging.
  2. **PostgreSQL** — Uses psycopg2 `cursor.copy_expert("COPY table FROM STDIN CSV HEADER", file)`. Equivalent speed to SQL\*Loader for Postgres. Parse `copy_expert` counts for loaded/rejected rows.
  3. **Python fallback** (any DB, or `use_sqlloader: false`)— Reads file in chunks of 10,000 rows, strips `header_rows` + `footer_rows`, inserts via `executemany()`. Slower but requires no external tooling.

  **Control file auto-generation (Oracle path):**
  FlowForge writes the `.ctl` to a temp directory — the user never touches it. Derives from: delimiter, `column_mapping`, any date-format hints on columns. After load: archive source files to `archive_directory`, delete temp `.ctl`/`.log`/`.bad`.

  **Step output variables (available in subsequent steps via `{{ steps.<name>.x }}`):**
  | Variable | Example |
  |---|---|
  | `files_found` | 3 |
  | `files_loaded` | 3 |
  | `files_failed` | 0 |
  | `records_loaded` | 147,832 |
  | `records_failed` | 14 |
  | `duration_sec` | 8.3 |

  Use these directly in an `email` step body to send a load confirmation — no new feature needed, standard pipeline step.

  **Run History tracking:**
  - `step_runs.rows_affected` = `records_loaded`
  - `step_runs.logs` = full load summary + first 50 rejected rows from `.bad` file

  **Code changes required:**
  - `flowforge/steps/bulk_load.py` — new step class
  - `flowforge/steps/base.py` — add `files_found`, `files_loaded`, `files_failed`, `records_loaded`, `records_failed`, `duration_sec` fields to `StepResult`
  - `flowforge/engine/context.py` — propagate new `StepResult` fields into pipeline context (same pattern as `output_path` and `drive_url`)
  - `frontend/src/components/pipeline/StepEditor.tsx` — add `bulk_load` step config panel
  - `frontend/src/lib/helpContent.ts` — add `bulk_load` to step hints
  - Alembic migration — add `bulk_load` to step type enum if constrained

  **Implementation order:** Python fallback first (works immediately, no Oracle client needed for dev/test) → PostgreSQL COPY → Oracle SQL\*Loader.

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
